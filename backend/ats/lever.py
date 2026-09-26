"""Lever ATS adapter for job application autofill."""
import logging
from typing import List, Dict, Any

from .base import ATSAdapter

logger = logging.getLogger('ats.lever')


class LeverAdapter(ATSAdapter):
    """Handles Lever job application forms."""

    name = 'lever'
    supported_domains = ['lever.co']

    SELECTORS = {
        'form': 'form.postings-applications, form[class*="application"], .application-form',
        'submit': 'button[data-qa="btn-submit"], button[type="submit"], .postings-btn-submit',
        'next': 'button[data-qa="btn-next"], .postings-btn-next',
        'field_container': '.application-field, [class*="application-field"], .field',
        'label': 'label, .application-label, [class*="label"]',
        'text_input': 'input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input:not([type]):not([hidden]):not([submit]):not([button]):not([checkbox]):not([radio]):not([file])',
        'textarea': 'textarea',
        'select': 'select',
        'radio': 'input[type="radio"]',
        'checkbox': 'input[type="checkbox"]',
        'file_input': 'input[type="file"]',
        'resume_upload': 'input[type="file"][name*="resume"], .file-attachment input[type="file"]',
        'cover_letter': '[class*="cover-letter"], [data-qa*="cover"]',
        'custom_question': '[class*="custom-question"], [class*="screening"]',
        'error': '.application-field-error, [class*="error"], [role="alert"]',
        'captcha': '[class*="captcha"], [class*="recaptcha"], iframe[src*="recaptcha"]',
    }

    async def can_handle(self, url: str, page) -> bool:
        if 'lever.co' in url.lower():
            return True
        try:
            content = await page.content()
            if 'lever' in content.lower() and ('apply' in content.lower() or 'application' in content.lower()):
                return True
        except Exception:
            pass
        return False

    async def extract_fields(self, page) -> List[Dict[str, Any]]:
        fields = []
        try:
            await page.wait_for_selector(self.SELECTORS['form'], timeout=10000)
        except Exception:
            logger.warning('No Lever form found, trying extraction anyway')

        try:
            raw_fields = await page.evaluate('''() => {
                const fields = [];
                const seen = new Set();

                function getLabel(el) {
                    if (el.id) {
                        const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                        if (lbl) return lbl.textContent.trim();
                    }
                    const parentLabel = el.closest('label');
                    if (parentLabel) return parentLabel.textContent.trim();
                    const container = el.closest('.application-field, .field, [class*="field"]');
                    if (container) {
                        const lbl = container.querySelector('label, .label, [class*="label"]');
                        if (lbl) return lbl.textContent.trim();
                    }
                    return el.getAttribute('aria-label') || el.placeholder || el.name || '';
                }

                function isRequired(el) {
                    if (el.required || el.getAttribute('aria-required') === 'true') return true;
                    const container = el.closest('.application-field, .field');
                    if (container) return container.querySelector('.required, [class*="required"]') !== null;
                    return false;
                }

                function getSection(el) {
                    const section = el.closest('fieldset, [class*="section"], [class*="group"]');
                    if (section) {
                        const h = section.querySelector('legend, h2, h3, [class*="heading"], [class*="title"]');
                        if (h) return h.textContent.trim();
                    }
                    return '';
                }

                const inputSelectors = [
                    'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
                    'textarea', 'select',
                ];

                for (const sel of inputSelectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        if (el.offsetParent === null && el.type !== 'file') continue;
                        if (el.disabled) continue;

                        const key = el.id || el.name || '';
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
                        else if (el.getAttribute('data-qa')) selector = `[data-qa="${CSS.escape(el.getAttribute('data-qa'))}"]`;

                        let fieldType = 'text';
                        if (el.tagName === 'SELECT') fieldType = 'select';
                        else if (el.type === 'radio') fieldType = 'radio';
                        else if (el.type === 'checkbox') fieldType = 'checkbox';
                        else if (el.type === 'file') fieldType = 'file';
                        else if (el.type === 'email') fieldType = 'email';
                        else if (el.type === 'tel') fieldType = 'phone';
                        else if (el.type === 'number') fieldType = 'number';
                        else if (el.tagName === 'TEXTAREA') fieldType = 'textarea';

                        fields.push({
                            field_label: getLabel(el),
                            field_name: el.name || '',
                            field_id: el.id || '',
                            field_type: fieldType,
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
                return fields;
            }''')

            fields = raw_fields or []
        except Exception as e:
            logger.error('Lever field extraction failed: %s', e)

        return fields

    async def fill_field(self, page, field: Dict[str, Any], value: str) -> bool:
        selector = field.get('field_selector', '')
        if not selector:
            return False

        try:
            element = await page.query_selector(selector)
            if not element:
                return False

            field_type = field.get('field_type', 'text')

            if field_type == 'select':
                options = field.get('options', [])
                target = value
                for opt in options:
                    if value.lower() in (opt.get('label', '').lower(), opt.get('value', '').lower()):
                        target = opt.get('value', value)
                        break
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
                }''', {'selector': selector, 'value': target})
                return True

            elif field_type == 'radio':
                name = field.get('field_name', '')
                if not name:
                    return False
                await page.evaluate('''(args) => {
                    const radios = document.querySelectorAll(`input[name="${args.name}"]`);
                    for (const r of radios) {
                        if (r.value === args.value || r.closest('label')?.textContent?.trim().toLowerCase() === args.value.toLowerCase()) {
                            r.checked = true;
                            r.dispatchEvent(new Event('change', { bubbles: true }));
                            break;
                        }
                    }
                }''', {'name': name, 'value': value})
                return True

            elif field_type == 'checkbox':
                should_check = value.lower() in ('true', 'yes', '1')
                is_checked = await element.is_checked()
                if should_check != is_checked:
                    await element.click()
                return True

            else:
                await element.click()
                await element.fill('')
                await element.type(value, delay=20)
                actual = await element.input_value()
                return actual.strip() == value.strip()

        except Exception as e:
            logger.error('Lever fill_field failed: %s', e)
            return False

    async def upload_resume(self, page, file_path: str) -> bool:
        try:
            file_input = await page.query_selector(self.SELECTORS['resume_upload'])
            if not file_input:
                file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                return False
            await file_input.set_input_files(file_path)
            return True
        except Exception as e:
            logger.error('Lever resume upload failed: %s', e)
            return False

    async def validate(self, page) -> Dict[str, Any]:
        errors = []
        try:
            error_els = await page.query_selector_all(self.SELECTORS['error'])
            for el in error_els:
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


lever_adapter = LeverAdapter()
