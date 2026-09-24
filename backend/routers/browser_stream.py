"""WebSocket endpoint for guided step-by-step job application fill."""
import asyncio
import base64
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.security import decode_access_token

logger = logging.getLogger('browser_stream')
router = APIRouter(prefix='/api', tags=['browser-stream'])


async def _extract_fields(page) -> list:
    """Extract visible form fields with labels, types, current values."""
    try:
        return await page.evaluate('''() => {
            const fields = [];
            const els = document.querySelectorAll(
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="file"]), textarea, select'
            );
            let idx = 0;
            for (const el of els) {
                if (el.offsetParent === null || el.disabled) continue;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;

                let label = '';
                if (el.id) {
                    const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                    if (lbl) label = lbl.textContent.trim();
                }
                if (!label) {
                    const parent = el.closest('label');
                    if (parent) label = parent.textContent.trim();
                }
                if (!label) {
                    const container = el.closest('[class*="field"], [class*="form"], [data-automation-id]');
                    if (container) {
                        const lbl = container.querySelector('label, [class*="label"], [class*="Label"]');
                        if (lbl) label = lbl.textContent.trim();
                    }
                }
                if (!label && el.name) label = el.name.replace(/[-_]/g, ' ');
                if (!label && el.placeholder) label = el.placeholder;
                if (!label && el.getAttribute('aria-label')) label = el.getAttribute('aria-label');

                let ft = 'text';
                if (el.tagName === 'SELECT') ft = 'select';
                else if (el.type === 'radio') ft = 'radio';
                else if (el.type === 'checkbox') ft = 'checkbox';
                else if (el.type === 'file') ft = 'file';
                else if (el.type === 'email') ft = 'email';
                else if (el.type === 'tel') ft = 'phone';
                else if (el.type === 'number') ft = 'number';
                else if (el.tagName === 'TEXTAREA') ft = 'textarea';

                let options = [];
                if (el.tagName === 'SELECT') {
                    options = Array.from(el.options).map(o => ({ value: o.value, label: o.textContent.trim() })).filter(o => o.value);
                }
                if (ft === 'radio' && el.name) {
                    const group = document.querySelectorAll(`input[name="${CSS.escape(el.name)}"]`);
                    options = Array.from(group).map(r => ({
                        value: r.value,
                        label: (r.closest('label') || r.parentElement)?.textContent?.trim() || r.value,
                    }));
                }

                const fieldName = el.name || el.id || el.getAttribute('data-automation-id') || '';
                fields.push({
                    index: idx++,
                    label: label || 'Unknown field',
                    type: ft,
                    name: fieldName,
                    value: el.value || '',
                    checked: el.type === 'checkbox' ? el.checked : undefined,
                    options: options,
                    required: el.required || el.getAttribute('aria-required') === 'true',
                    selector: fieldName
                        ? (el.id ? '#' + CSS.escape(el.id) : `${el.tagName.toLowerCase()}[name="${CSS.escape(fieldName)}"]`)
                        : '',
                });
            }
            return fields;
        }''') or []
    except Exception as e:
        logger.error('Extract fields failed: %s', e)
        return []


async def _fill_field(page, field: dict, value: str) -> bool:
    """Fill a single field by selector or index."""
    try:
        selector = field.get('selector', '')
        ft = field.get('type', 'text')

        if selector:
            el = await page.query_selector(selector)
            if not el:
                return False

            if ft == 'select':
                tag = await el.evaluate('e => e.tagName')
                if tag == 'SELECT':
                    await page.evaluate('''(args) => {
                        const el = document.querySelector(args.sel);
                        if (!el) return;
                        for (const opt of el.options) {
                            if (opt.value === args.val || opt.textContent.trim().toLowerCase() === args.val.toLowerCase()) {
                                el.value = opt.value;
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                break;
                            }
                        }
                    }''', {'sel': selector, 'val': value})
                    return True
                # Custom dropdown - click to open, find option
                await el.click()
                await page.wait_for_timeout(500)
                found = await page.evaluate('''(val) => {
                    const opts = document.querySelectorAll('[role="option"], [class*="option"], li');
                    for (const o of opts) {
                        if (o.textContent.trim().toLowerCase().includes(val.toLowerCase())) {
                            o.click();
                            return true;
                        }
                    }
                    return false;
                }''', value)
                if found:
                    await page.wait_for_timeout(300)
                    return True
                # Try typing into combobox
                inp = await el.query_selector('input')
                if inp:
                    await inp.fill('')
                    await inp.type(value, delay=30)
                    await page.wait_for_timeout(500)
                    await page.evaluate('''() => {
                        const o = document.querySelector('[role="option"]');
                        if (o) o.click();
                    }''')
                    return True
                return False

            if ft == 'radio':
                name = field.get('name', '')
                if name:
                    await page.evaluate('''(args) => {
                        const radios = document.querySelectorAll(`input[name="${args.name}"]`);
                        for (const r of radios) {
                            const lbl = (r.closest('label') || r.parentElement)?.textContent?.trim() || '';
                            if (r.value === args.val || lbl.toLowerCase() === args.val.toLowerCase()) {
                                r.checked = true;
                                r.dispatchEvent(new Event('change', { bubbles: true }));
                                r.dispatchEvent(new Event('click', { bubbles: true }));
                                return;
                            }
                        }
                    }''', {'name': name, 'val': value})
                    return True
                return False

            if ft == 'checkbox':
                should = value.lower() in ('true', 'yes', '1', 'on')
                is_checked = await el.is_checked()
                if should != is_checked:
                    await el.click()
                return True

            # Text/email/tel/number/textarea
            await el.click()
            await el.fill('')
            await el.type(value, delay=20)
            return True

        return False
    except Exception as e:
        logger.error('Fill field failed: %s', e)
        return False


async def _find_and_click_next(page) -> bool:
    """Find and click the Next/Continue/Submit button on the current step."""
    try:
        return await page.evaluate('''() => {
            const btns = document.querySelectorAll('button, a, [role="button"], input[type="submit"]');
            const nextPatterns = ['next', 'continue', 'proceed', 'save & next', 'save and next'];
            const submitPatterns = ['submit', 'apply', 'send', 'finish', 'complete'];

            // Try Next/Continue first
            for (const btn of btns) {
                if (btn.offsetParent === null || btn.disabled) continue;
                const text = btn.textContent.trim().toLowerCase();
                for (const p of nextPatterns) {
                    if (text.includes(p)) {
                        btn.click();
                        return 'next';
                    }
                }
            }
            // Try Submit
            for (const btn of btns) {
                if (btn.offsetParent === null || btn.disabled) continue;
                const text = btn.textContent.trim().toLowerCase();
                for (const p of submitPatterns) {
                    if (text.includes(p)) {
                        btn.click();
                        return 'submit';
                    }
                }
            }
            // Try primary/cta buttons
            for (const btn of btns) {
                if (btn.offsetParent === null || btn.disabled) continue;
                if (btn.classList.contains('primary') || btn.classList.contains('cta') ||
                    btn.getAttribute('data-automation-id')?.includes('submit') ||
                    btn.getAttribute('data-automation-id')?.includes('next')) {
                    btn.click();
                    return 'next';
                }
            }
            return '';
        }''')
    except Exception as e:
        logger.error('Click next failed: %s', e)
        return ''


async def _take_screenshot_b64(page) -> str:
    """Take screenshot and return base64."""
    try:
        screenshot_bytes = await page.screenshot(full_page=False)
        return base64.b64encode(screenshot_bytes).decode('utf-8')
    except Exception:
        return ''


@router.websocket('/ws/browser-stream')
async def browser_stream_ws(websocket: WebSocket):
    """Guided step-by-step job application fill.

    Protocol:
    -> { "action": "open", "url": "..." }
    -> { "action": "fill-and-next", "fields": [{ index/name/selector, value }] }
    -> { "action": "fill-and-submit", "fields": [...] }
    -> { "action": "screenshot" }
    -> { "action": "close" }

    <- { "type": "screenshot", "data": "base64..." }
    <- { "type": "step", "step": 1, "fields": [...], "has_next": true/false, "page_title": "..." }
    <- { "type": "filled", "success": true/false, "next_action": "next"/"submit"/"" }
    <- { "type": "error", "message": "..." }
    """
    await websocket.accept()

    token = websocket.query_params.get('token', '')
    user_id = decode_access_token(token) if token else None

    if not user_id:
        try:
            await websocket.send_json({'type': 'error', 'message': 'Please log in again'})
        except Exception:
            pass
        await websocket.close(code=4001)
        return

    from backend.browser.worker import get_browser_manager
    from backend.services.job_profile_service import JobProfileService
    from backend.database import SessionLocal

    browser_mgr = get_browser_manager()
    page = None
    context = None
    step_num = 0

    db = SessionLocal()
    try:
        profile_svc = JobProfileService(db)
        profile = profile_svc.get_or_create(user_id)
        profile_dict = profile.to_dict() if profile else {}
    finally:
        db.close()

    try:
        # Send profile to frontend
        await websocket.send_json({'type': 'profile', 'data': profile_dict})

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=300)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break

            action = msg.get('action', '')

            if action == 'open':
                url = msg.get('url', '')
                if not url:
                    await websocket.send_json({'type': 'error', 'message': 'No URL'})
                    continue

                # Close previous
                if page and not page.is_closed():
                    try: await page.close()
                    except: pass
                if context:
                    try: await context.close()
                    except: pass

                try:
                    ctx_cm = browser_mgr.ephemeral_context()
                    context = await ctx_cm.__aenter__()
                    page = await context.new_page()
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(3000)

                    step_num = 1

                    # Take screenshot + extract fields
                    screenshot = await _take_screenshot_b64(page)
                    fields = await _extract_fields(page)
                    title = await page.title()

                    # Detect if there's a Next button
                    has_next = await page.evaluate('''() => {
                        const btns = document.querySelectorAll('button, a, [role="button"]');
                        for (const b of btns) {
                            if (b.offsetParent === null) continue;
                            const t = b.textContent.trim().toLowerCase();
                            if (t.includes('next') || t.includes('continue') || t.includes('proceed')) return true;
                        }
                        return false;
                    }''')

                    await websocket.send_json({
                        'type': 'screenshot', 'data': screenshot,
                    })
                    await websocket.send_json({
                        'type': 'step',
                        'step': step_num,
                        'fields': fields,
                        'has_next': has_next,
                        'page_title': title,
                    })

                except Exception as e:
                    await websocket.send_json({'type': 'error', 'message': f'Failed: {str(e)}'})

            elif action == 'fill-and-next':
                fields_to_fill = msg.get('fields', [])
                if not page or page.is_closed():
                    await websocket.send_json({'type': 'error', 'message': 'No page open'})
                    continue

                # Fill each field
                filled_count = 0
                for f in fields_to_fill:
                    val = f.get('value', '')
                    if not val:
                        continue
                    success = await _fill_field(page, f, val)
                    if success:
                        filled_count += 1

                # Click Next
                next_result = await _find_and_click_next(page)
                if next_result:
                    await page.wait_for_timeout(3000)

                # Take new screenshot + extract new fields
                screenshot = await _take_screenshot_b64(page)
                fields = await _extract_fields(page)
                title = await page.title()
                step_num += 1

                has_next = await page.evaluate('''() => {
                    const btns = document.querySelectorAll('button, a, [role="button"]');
                    for (const b of btns) {
                        if (b.offsetParent === null) continue;
                        const t = b.textContent.trim().toLowerCase();
                        if (t.includes('next') || t.includes('continue') || t.includes('proceed')) return true;
                    }
                    return false;
                }''')

                await websocket.send_json({'type': 'screenshot', 'data': screenshot})
                await websocket.send_json({
                    'type': 'step',
                    'step': step_num,
                    'fields': fields,
                    'has_next': has_next,
                    'filled_count': filled_count,
                    'next_action': next_result,
                    'page_title': title,
                })

            elif action == 'fill-and-submit':
                fields_to_fill = msg.get('fields', [])
                if not page or page.is_closed():
                    await websocket.send_json({'type': 'error', 'message': 'No page open'})
                    continue

                filled_count = 0
                for f in fields_to_fill:
                    val = f.get('value', '')
                    if not val:
                        continue
                    success = await _fill_field(page, f, val)
                    if success:
                        filled_count += 1

                # Click Submit
                next_result = await _find_and_click_next(page)
                await page.wait_for_timeout(3000)

                screenshot = await _take_screenshot_b64(page)
                fields = await _extract_fields(page)
                title = await page.title()

                await websocket.send_json({'type': 'screenshot', 'data': screenshot})
                await websocket.send_json({
                    'type': 'step',
                    'step': step_num,
                    'fields': fields,
                    'has_next': False,
                    'filled_count': filled_count,
                    'next_action': next_result or 'submitted',
                    'page_title': title,
                })

            elif action == 'screenshot':
                if page and not page.is_closed():
                    screenshot = await _take_screenshot_b64(page)
                    await websocket.send_json({'type': 'screenshot', 'data': screenshot})

            elif action == 'close':
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error('Browser stream error: %s', e)
    finally:
        if page and not page.is_closed():
            try: await page.close()
            except: pass
        if context:
            try: await context.__aexit__(None, None, None)
            except: pass
