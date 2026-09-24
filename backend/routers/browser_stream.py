"""WebSocket endpoint for live browser streaming with field interaction."""
import asyncio
import base64
import json
import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.security import decode_access_token

logger = logging.getLogger('browser_stream')
router = APIRouter(tags=['browser-stream'])

# Active browser sessions per user
_active_sessions: Dict[int, Dict[str, Any]] = {}


async def _extract_fields_from_page(page) -> list:
    """Extract form fields with their bounding boxes for click detection."""
    try:
        return await page.evaluate('''() => {
            const fields = [];
            const els = document.querySelectorAll(
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'
            );
            for (const el of els) {
                if (el.offsetParent === null) continue;
                if (el.disabled) continue;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;

                let label = '';
                if (el.id) {
                    const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                    if (lbl) label = lbl.textContent.trim();
                }
                if (!label && el.name) label = el.name;
                if (!label && el.placeholder) label = el.placeholder;
                if (!label && el.getAttribute('aria-label')) label = el.getAttribute('aria-label');
                if (!label) {
                    const parent = el.closest('label');
                    if (parent) label = parent.textContent.trim();
                }

                let options = [];
                if (el.tagName === 'SELECT') {
                    options = Array.from(el.options).map(o => ({ value: o.value, label: o.textContent.trim() }));
                }

                let ft = 'text';
                if (el.tagName === 'SELECT') ft = 'select';
                else if (el.type === 'radio') ft = 'radio';
                else if (el.type === 'checkbox') ft = 'checkbox';
                else if (el.type === 'file') ft = 'file';
                else if (el.type === 'email') ft = 'email';
                else if (el.type === 'tel') ft = 'phone';
                else if (el.type === 'number') ft = 'number';
                else if (el.tagName === 'TEXTAREA') ft = 'textarea';

                fields.push({
                    index: fields.length,
                    label: label || `Field ${fields.length + 1}`,
                    type: ft,
                    name: el.name || '',
                    id: el.id || '',
                    placeholder: el.placeholder || '',
                    required: el.required || el.getAttribute('aria-required') === 'true',
                    value: el.value || '',
                    options: options,
                    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                });
            }
            return fields;
        }''')
    except Exception as e:
        logger.error('Field extraction failed: %s', e)
        return []


async def _fill_field_by_index(page, index: int, value: str) -> bool:
    """Fill a field by its index."""
    try:
        return await page.evaluate('''(args) => {
            const els = document.querySelectorAll(
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'
            );
            const visible = [];
            for (const el of els) {
                if (el.offsetParent === null || el.disabled) continue;
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) visible.push(el);
            }
            const el = visible[args.index];
            if (!el) return false;

            if (el.tagName === 'SELECT') {
                for (const opt of el.options) {
                    if (opt.value === args.value || opt.textContent.trim().toLowerCase() === args.value.toLowerCase()) {
                        el.value = opt.value;
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                return false;
            }
            if (el.type === 'radio') {
                const name = el.name;
                const radios = document.querySelectorAll(`input[name="${CSS.escape(name)}"]`);
                for (const r of radios) {
                    if (r.value === args.value || r.closest('label')?.textContent?.trim().toLowerCase() === args.value.toLowerCase()) {
                        r.checked = true;
                        r.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                return false;
            }
            if (el.type === 'checkbox') {
                const should = args.value.toLowerCase() === 'true' || args.value.toLowerCase() === 'yes';
                if (el.checked !== should) el.click();
                return true;
            }

            el.focus();
            el.value = '';
            el.value = args.value;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return el.value === args.value;
        }''', {'index': index, 'value': value})
    except Exception as e:
        logger.error('Fill field failed: %s', e)
        return False


@router.websocket('/ws/browser-stream')
async def browser_stream_ws(websocket: WebSocket):
    """WebSocket for live browser streaming with field interaction.

    Protocol:
    -> { "action": "open", "url": "..." }
    -> { "action": "click", "x": 100, "y": 200 }  (click on page)
    -> { "action": "fill", "index": 0, "value": "John" }  (fill a field)
    -> { "action": "scroll", "delta": -300 }  (scroll the page)
    -> { "action": "fields" }  (re-extract fields)
    <- { "type": "screenshot", "data": "base64..." }
    <- { "type": "fields", "fields": [...] }
    <- { "type": "filled", "index": 0, "success": true }
    <- { "type": "error", "message": "..." }
    """
    await websocket.accept()

    # Authenticate
    token = websocket.query_params.get('token', '')
    user_id = None
    try:
        payload = decode_access_token(token)
        user_id = payload
    except Exception:
        pass

    if not user_id:
        await websocket.send_json({'type': 'error', 'message': 'Authentication required'})
        await websocket.close()
        return

    from backend.browser.worker import get_browser_manager
    from backend.services.job_profile_service import JobProfileService
    from backend.database import SessionLocal

    browser_mgr = get_browser_manager()
    page = None
    context = None
    running = True
    screenshot_task = None

    db = SessionLocal()
    try:
        profile_svc = JobProfileService(db)
        profile = profile_svc.get_or_create(user_id)
        profile_dict = profile.to_dict() if profile else {}
    finally:
        db.close()

    async def send_screenshot():
        """Take and send screenshots periodically."""
        nonlocal running
        while running and page:
            try:
                await asyncio.sleep(1.0)
                if page.is_closed():
                    break
                screenshot_bytes = await page.screenshot(full_page=False)
                b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                await websocket.send_json({'type': 'screenshot', 'data': b64})
            except Exception:
                break

    try:
        while running:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=30)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break

            action = msg.get('action', '')

            if action == 'open':
                url = msg.get('url', '')
                if not url:
                    await websocket.send_json({'type': 'error', 'message': 'No URL provided'})
                    continue

                # Close previous page
                if page and not page.is_closed():
                    try:
                        await page.close()
                    except Exception:
                        pass

                try:
                    ctx = await browser_mgr.ephemeral_context()
                    context = ctx
                    page = await context.new_page()
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(3000)

                    # Send initial screenshot
                    screenshot_bytes = await page.screenshot(full_page=False)
                    b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    await websocket.send_json({'type': 'screenshot', 'data': b64})

                    # Extract and send fields
                    fields = await _extract_fields_from_page(page)
                    await websocket.send_json({'type': 'fields', 'fields': fields})

                    # Start periodic screenshots
                    if screenshot_task:
                        screenshot_task.cancel()
                    screenshot_task = asyncio.create_task(send_screenshot())

                except Exception as e:
                    await websocket.send_json({'type': 'error', 'message': f'Failed to open: {str(e)}'})

            elif action == 'fill':
                index = msg.get('index')
                value = msg.get('value', '')
                if page and not page.is_closed() and index is not None:
                    success = await _fill_field_by_index(page, index, value)
                    await websocket.send_json({'type': 'filled', 'index': index, 'success': success})
                    # Send updated screenshot
                    try:
                        screenshot_bytes = await page.screenshot(full_page=False)
                        b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        await websocket.send_json({'type': 'screenshot', 'data': b64})
                    except Exception:
                        pass

            elif action == 'click':
                x = msg.get('x', 0)
                y = msg.get('y', 0)
                if page and not page.is_closed():
                    try:
                        await page.mouse.click(x, y)
                        await page.wait_for_timeout(500)
                        # Re-extract fields after click (dropdown might have opened)
                        fields = await _extract_fields_from_page(page)
                        await websocket.send_json({'type': 'fields', 'fields': fields})
                        screenshot_bytes = await page.screenshot(full_page=False)
                        b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        await websocket.send_json({'type': 'screenshot', 'data': b64})
                    except Exception as e:
                        await websocket.send_json({'type': 'error', 'message': str(e)})

            elif action == 'scroll':
                delta = msg.get('delta', 0)
                if page and not page.is_closed():
                    try:
                        await page.mouse.wheel(0, delta)
                        await page.wait_for_timeout(300)
                        screenshot_bytes = await page.screenshot(full_page=False)
                        b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        await websocket.send_json({'type': 'screenshot', 'data': b64})
                    except Exception:
                        pass

            elif action == 'fields':
                if page and not page.is_closed():
                    fields = await _extract_fields_from_page(page)
                    await websocket.send_json({'type': 'fields', 'fields': fields})

            elif action == 'close':
                running = False
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error('Browser stream error: %s', e)
    finally:
        running = False
        if screenshot_task:
            screenshot_task.cancel()
        if page and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass
        if context:
            try:
                await context.close()
            except Exception:
                pass
