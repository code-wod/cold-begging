"""Workday ATS adapter for job application autofill."""
import logging
import re
from typing import List, Dict, Any

from .base import ATSAdapter

logger = logging.getLogger('ats.workday')


class WorkdayAdapter(ATSAdapter):
    """Handles Workday job application forms.

    Workday uses heavily dynamic JavaScript-rendered forms with
    custom dropdowns, multi-step flows, and React-based UI.
    """

    name = 'workday'
    supported_domains = ['myworkdayjobs.com', 'workday.com', 'wd5.myworkdayjobs.com']

    SELECTORS = {
        'form': '[class*="application"], [data-automation-id*="application"], form',
        'submit': '[data-automation-id="submit-button"], button[type="submit"], [class*="submit"]',
        'next': '[data-automation-id="next-button"], [class*="next"]',
        'field_container': '[class*="field-group"], [class*="form-field"], [data-automation-id*="field"]',
        'label': 'label, [class*="label"], [data-automation-id*="label"]',
        'text_input': 'input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input:not([type]):not([hidden]):not([submit]):not([button]):not([checkbox]):not([radio]):not([file])',
        'textarea': 'textarea',
        'select': 'select',
        'radio': 'input[type="radio"]',
        'checkbox': 'input[type="checkbox"]',
        'file_input': 'input[type="file"]',
        'resume_upload': '[data-automation-id*="resume"] input[type="file"], input[type="file"][name*="resume"]',
        'custom_dropdown': '[class*="select"], [role="listbox"], [role="combobox"], [data-automation-id*="select"]',
        'autocomplete': '[class*="autocomplete"], [role="combobox"]',
        'error': '[class*="error"], [data-automation-id*="error"], [role="alert"]',
        'section_heading': 'h2, h3, [class*="section-header"], [data-automation-id*="section"]',
        'progress': '[class*="progress"], [class*="step"]',
        'captcha': '[class*="captcha"], [class*="recaptcha"], iframe[src*="recaptcha"]',
    }

    async def can_handle(self, url: str, page) -> bool:
        url_lower = url.lower()
        if any(d in url_lower for d in ['myworkdayjobs.com', 'workday.com', 'wd5.myworkdayjobs']):
            return True
        try:
            content = await page.content()
            cl = content.lower()
            if 'workday' in cl and ('apply' in cl or 'application' in cl):
                return True
            if 'data-automation-id' in cl:
                return True
        except Exception:
            pass
        return False

    async def extract_fields(self, page) -> List[Dict[str, Any]]:
        """Extract fields from Workday's dynamic forms.

        Workday uses React components with data-automation-id attributes.
        Custom dropdowns are rendered as divs, not native selects.
        """
        fields = []
        try:
            await page.wait_for_selector(self.SELECTORS['form'], timeout=15000)
        except Exception:
            logger.warning('No Workday form found')

        try:
            raw_fields = await page.evaluate('''() => {
                const fields = [];
                const seen = new Set();

                function getLabel(el) {
                    // Workday uses label elements with for attribute
                    if (el.id) {
                        const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                        if (lbl) return lbl.textContent.trim();
                    }
                    // Check data-automation-id for label
                    const autoId = el.getAttribute('data-automation-id') || '';
                    if (autoId) {
                        // Convert automation id to readable label
                        return autoId.replace(/[-_]/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                    }
                    // Check aria-label
                    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
                    // Check placeholder
                    if (el.placeholder) return el.placeholder;
                    // Check name
                    if (el.name) return el.name.replace(/[-_]/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                    // Check parent label
                    const parentLabel = el.closest('label');
                    if (parentLabel) return parentLabel.textContent.trim();
                    // Check sibling label
                    const container = el.closest('[class*="field-group"], [class*="form-field"]');
                    if (container) {
                        const lbl = container.querySelector('label, [class*="label"]');
                        if (lbl) return lbl.textContent.trim();
                    }
                    return '';
                }

                function isRequired(el) {
                    if (el.required || el.getAttribute('aria-required') === 'true') return true;
                    const container = el.closest('[class*="field-group"], [class*="form-field"]');
                    if (container) {
                        return container.querySelector('[class*="required"], [aria-required="true"]') !== null;
                    }
                    return false;
                }

                function getSection(el) {
                    // Walk up to find section heading
                    let current = el;
                    while (current && current !== document.body) {
                        current = current.previousElementSibling || current.parentElement;
                        if (current && (current.tagName === 'H2' || current.tagName === 'H3' ||
                            current.classList.contains('section-header') ||
                            current.getAttribute('data-automation-id')?.includes('section'))) {
                            return current.textContent.trim();
                        }
                    }
                    return '';
                }

                // Standard inputs
                const inputSels = [
                    'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
                    'textarea', 'select',
                ];

                for (const sel of inputSels) {
                    for (const el of document.querySelectorAll(sel)) {
                        if (el.offsetParent === null && el.type !== 'file') continue;
                        if (el.disabled) continue;

                        const key = el.id || el.name || el.getAttribute('data-automation-id') || '';
                        if (key && seen.has(key)) continue;
                        if (key) seen.add(key);

                        let options = [];
                        if (el.tagName === 'SELECT') {
                            options = Array.from(el.options).map(o => ({
                                value: o.value, label: o.textContent.trim(),
                            })).filter(o => o.value && o.label);
                        } else if (el.type === 'radio') {
                            const name = el.name;
                            if (name) {
                                options = Array.from(document.querySelectorAll(`input[name="${CSS.escape(name)}"]`)).map(r => ({
                                    value: r.value,
                                    label: r.closest('label')?.textContent?.trim() || r.value,
                                }));
                            }
                        }

                        let selector = '';
                        if (el.id) selector = `#${CSS.escape(el.id)}`;
                        else if (el.name) selector = `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
                        else if (el.getAttribute('data-automation-id')) selector = `[data-automation-id="${CSS.escape(el.getAttribute('data-automation-id'))}"]`;

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
                            field_label: getLabel(el),
                            field_name: el.name || '',
                            field_id: el.id || '',
                            field_type: ft,
                            field_selector: selector,
                            placeholder: el.placeholder || '',
                            aria_label: el.getAttribute('aria-label') || '',
                            section: getSection(el),
                            options: options,
                            required: isRequired(el),
                            is_cover_letter: (el.name || '').toLowerCase().includes('cover'),
                            is_resume: (el.name || '').toLowerCase().includes('resume'),
                            order: fields.length,
                            status: 'pending',
                            confidence: 0.0,
                            mapped_value: '',
                            profile_field: '',
                            mapping_reasoning: '',
                            requires_review: true,
                        });
                    }
                }

                // Workday custom dropdowns (div-based, role="listbox" or role="combobox")
                const customDropdowns = document.querySelectorAll('[role="listbox"], [role="combobox"], [class*="select-input"]');
                for (const el of customDropdowns) {
                    if (el.offsetParent === null) continue;
                    const autoId = el.getAttribute('data-automation-id') || el.id || '';
                    if (autoId && seen.has(autoId)) continue;
                    if (autoId) seen.add(autoId);

                    const label = getLabel(el);
                    let selector = '';
                    if (autoId) selector = `[data-automation-id="${CSS.escape(autoId)}"]`;
                    else if (el.id) selector = `#${CSS.escape(el.id)}`;

                    fields.push({
                        field_label: label,
                        field_name: '',
                        field_id: autoId,
                        field_type: 'select',
                        field_selector: selector,
                        placeholder: '',
                        aria_label: el.getAttribute('aria-label') || '',
                        section: getSection(el),
                        options: [],
                        required: false,
                        is_cover_letter: false,
                        is_resume: false,
                        order: fields.length,
                        status: 'pending',
                        confidence: 0.0,
                        mapped_value: '',
                        profile_field: '',
                        mapping_reasoning: '',
                        requires_review: true,
                    });
                }

                return fields;
            }''')

            fields = raw_fields or []
        except Exception as e:
            logger.error('Workday field extraction failed: %s', e)

        return fields

    async def fill_field(self, page, field: Dict[str, Any], value: str) -> bool:
        selector = field.get('field_selector', '')
        if not selector:
            return False

        try:
            element = await page.query_selector(selector)
            if not element:
                return False

            ft = field.get('field_type', 'text')

            if ft == 'select':
                # Try native select first
                tag = await element.evaluate('el => el.tagName')
                if tag == 'SELECT':
                    await page.evaluate('''(args) => {
                        const el = document.querySelector(args.selector);
                        if (!el) return;
                        for (const opt of el.options) {
                            if (opt.value === args.value || opt.textContent.trim().toLowerCase() === args.value.toLowerCase()) {
                                el.value = opt.value;
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                break;
                            }
                        }
                    }''', {'selector': selector, 'value': value})
                    return True

                # Workday custom dropdown: click to open, then select option
                await element.click()
                await page.wait_for_timeout(500)

                # Look for the option in the opened dropdown
                option_found = await page.evaluate('''(value) => {
                    const options = document.querySelectorAll('[role="option"], [class*="option"], [data-automation-id*="option"]');
                    for (const opt of options) {
                        const text = opt.textContent.trim();
                        if (text.toLowerCase() === value.toLowerCase() || text.includes(value)) {
                            opt.click();
                            return true;
                        }
                    }
                    return false;
                }''', value)

                if option_found:
                    await page.wait_for_timeout(300)
                    return True

                # Fallback: type into the input if it's a combobox
                input_el = await element.query_selector('input')
                if input_el:
                    await input_el.fill('')
                    await input_el.type(value, delay=30)
                    await page.wait_for_timeout(500)
                    # Try to select first option
                    await page.evaluate('''() => {
                        const opt = document.querySelector('[role="option"]');
                        if (opt) opt.click();
                    }''')
                    return True

                return False

            elif ft == 'radio':
                name = field.get('field_name', '')
                if not name:
                    # Try clicking the label with matching text
                    await page.evaluate('''(args) => {
                        const labels = document.querySelectorAll('label, [class*="radio"]');
                        for (const lbl of labels) {
                            if (lbl.textContent.trim().toLowerCase() === args.value.toLowerCase()) {
                                lbl.click();
                                break;
                            }
                        }
                    }''', {'value': value})
                    return True

                await page.evaluate('''(args) => {
                    const radios = document.querySelectorAll(`input[name="${args.name}"]`);
                    for (const r of radios) {
                        if (r.value === args.value || r.closest('label')?.textContent?.trim().toLowerCase() === args.value.toLowerCase()) {
                            r.checked = true;
                            r.dispatchEvent(new Event('change', { bubbles: true }));
                            r.dispatchEvent(new Event('click', { bubbles: true }));
                            break;
                        }
                    }
                }''', {'name': name, 'value': value})
                return True

            elif ft == 'checkbox':
                should = value.lower() in ('true', 'yes', '1')
                is_checked = await element.is_checked()
                if should != is_checked:
                    await element.click()
                return True

            else:
                # Standard text/email/tel/number/textarea
                await element.click()
                await element.fill('')
                await element.type(value, delay=20)
                actual = await element.input_value()
                return actual.strip() == value.strip()

        except Exception as e:
            logger.error('Workday fill_field failed: %s', e)
            return False

    async def upload_resume(self, page, file_path: str) -> bool:
        try:
            fi = await page.query_selector(self.SELECTORS['resume_upload'])
            if not fi:
                fi = await page.query_selector('input[type="file"]')
            if not fi:
                return False
            await fi.set_input_files(file_path)
            return True
        except Exception as e:
            logger.error('Workday resume upload failed: %s', e)
            return False

    async def validate(self, page) -> Dict[str, Any]:
        errors = []
        try:
            els = await page.query_selector_all(self.SELECTORS['error'])
            for el in els:
                text = await el.text_content()
                if text and text.strip():
                    errors.append(text.strip())
        except Exception:
            pass
        return {'valid': len(errors) == 0, 'errors': errors}

    async def submit(self, page) -> Dict[str, Any]:
        try:
            btn = await page.query_selector(self.SELECTORS['submit'])
            if not btn:
                btn = await page.query_selector(self.SELECTORS['next'])
            if not btn:
                return {'success': False, 'message': 'Submit button not found'}
            await btn.click()
            await page.wait_for_timeout(3000)
            return {'success': True, 'message': 'Submitted'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    async def handle_multi_step(self, page, max_steps: int = 30) -> Dict[str, Any]:
        """Workday forms are heavily multi-step. Navigate through steps."""
        steps = 0
        for _ in range(max_steps):
            submit = await page.query_selector(self.SELECTORS['submit'])
            if submit:
                break
            next_btn = await page.query_selector(self.SELECTORS['next'])
            if not next_btn:
                break
            try:
                await next_btn.click()
                await page.wait_for_timeout(2000)
                steps += 1
            except Exception:
                break
        return {'steps_completed': steps}


workday_adapter = WorkdayAdapter()
