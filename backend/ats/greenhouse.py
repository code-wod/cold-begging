"""Greenhouse ATS adapter for job application autofill."""
import logging
import re
from typing import List, Dict, Any, Optional

from .base import ATSAdapter

logger = logging.getLogger('ats.greenhouse')


class GreenhouseAdapter(ATSAdapter):
    """Handles Greenhouse job application forms."""

    name = 'greenhouse'
    supported_domains = ['greenhouse.io']

    # Greenhouse-specific CSS selectors
    SELECTORS = {
        'form': 'form, [class*="application"], [id*="application"]',
        'submit': 'button[type="submit"], input[type="submit"], [class*="submit"]',
        'next': 'button[class*="next"], [class*="next-step"]',
        'file_input': 'input[type="file"]',
        'field_container': '.field, [class*="field"], [class*="form-group"], [class*="question"]',
        'label': 'label, [class*="label"], [class*="question-text"], .field-label',
        'required_marker': '.required, [aria-required="true"], [required]',
        'text_input': 'input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input:not([type]):not([hidden]):not([submit]):not([button]):not([checkbox]):not([radio]):not([file])',
        'textarea': 'textarea',
        'select': 'select',
        'radio': 'input[type="radio"]',
        'checkbox': 'input[type="checkbox"]',
        'custom_dropdown': '[class*="select"], [class*="dropdown"], [role="listbox"], [role="combobox"]',
        'autocomplete': '[class*="autocomplete"], [class*="typeahead"]',
        'cover_letter': '[class*="cover-letter"], [data-field="cover_letter"]',
        'resume_upload': 'input[type="file"][name*="resume"], input[type="file"][name*="resume_or_cv"]',
        'divider': '[class*="divider"], [class*="section-header"], [class*="heading"]',
        'error': '[class*="error"], [class*="invalid"], [role="alert"]',
        'captcha': '[class*="captcha"], [class*="recaptcha"], iframe[src*="recaptcha"]',
        'login_required': '[class*="login"], [class*="sign-in"], [class*="auth"]',
    }

    async def can_handle(self, url: str, page) -> bool:
        """Check if this is a Greenhouse application page."""
        url_lower = url.lower()
        if 'greenhouse.io' in url_lower:
            return True

        # Check page content for Greenhouse markers
        try:
            content = await page.content()
            content_lower = content.lower()
            if 'greenhouse' in content_lower and ('apply' in content_lower or 'application' in content_lower):
                return True
            if 'gh-form' in content_lower or 'greenhouse' in content_lower:
                return True
        except Exception:
            pass

        return False

    async def extract_fields(self, page) -> List[Dict[str, Any]]:
        """Extract all form fields from a Greenhouse application page."""
        fields = []

        try:
            # Wait for form to load
            await page.wait_for_selector(self.SELECTORS['form'], timeout=10000)
        except Exception:
            logger.warning('No form found on Greenhouse page, trying to extract anyway')

        try:
            raw_fields = await page.evaluate('''(selectors) => {
                const fields = [];
                const seen = new Set();

                // Helper to get label for an element
                function getLabel(el) {
                    // Try label[for]
                    if (el.id) {
                        const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                        if (label) return label.textContent.trim();
                    }
                    // Try closest label
                    const parentLabel = el.closest('label');
                    if (parentLabel) return parentLabel.textContent.trim();
                    // Try previous sibling
                    const prev = el.previousElementSibling;
                    if (prev && (prev.tagName === 'LABEL' || prev.classList.contains('label') || prev.classList.contains('field-label'))) {
                        return prev.textContent.trim();
                    }
                    // Try parent's label
                    const parent = el.closest('.field, .form-group, [class*="field"]');
                    if (parent) {
                        const lbl = parent.querySelector('label, .label, [class*="label"], [class*="question"]');
                        if (lbl) return lbl.textContent.trim();
                    }
                    // Try aria-label
                    return el.getAttribute('aria-label') || el.placeholder || el.name || '';
                }

                // Helper to check if field is required
                function isRequired(el) {
                    if (el.required || el.getAttribute('aria-required') === 'true') return true;
                    const parent = el.closest('.field, .form-group, [class*="field"]');
                    if (parent) {
                        return parent.querySelector('.required, [class*="required"]') !== null;
                    }
                    return false;
                }

                // Helper to get section
                function getSection(el) {
                    const section = el.closest('[class*="section"], fieldset, [class*="group"]');
                    if (section) {
                        const heading = section.querySelector('h2, h3, h4, [class*="heading"], [class*="title"], legend');
                        if (heading) return heading.textContent.trim();
                    }
                    return '';
                }

                // Extract all form inputs
                const inputSelectors = [
                    'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
                    'textarea',
                    'select',
                    '[role="combobox"]',
                    '[role="listbox"]',
                ];

                for (const sel of inputSelectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        if (el.offsetParent === null && el.type !== 'file') continue;
                        if (el.disabled) continue;

                        const key = el.id || el.name || el.getAttribute('data-field') || '';
                        if (key && seen.has(key)) continue;
                        if (key) seen.add(key);

                        const label = getLabel(el);
                        const section = getSection(el);
                        const required = isRequired(el);

                        // Get options for select/radio
                        let options = [];
                        if (el.tagName === 'SELECT') {
                            options = Array.from(el.options).map(o => ({
                                value: o.value,
                                label: o.textContent.trim(),
                            })).filter(o => o.value && o.label && o.value !== '');
                        } else if (el.type === 'radio') {
                            const name = el.name;
                            if (name) {
                                const radios = document.querySelectorAll(`input[name="${CSS.escape(name)}"]`);
                                options = Array.from(radios).map(r => ({
                                    value: r.value,
                                    label: r.closest('label')?.textContent?.trim() || r.value,
                                }));
                            }
                        }

                        // Build CSS selector
                        let selector = '';
                        if (el.id) {
                            selector = `#${CSS.escape(el.id)}`;
                        } else if (el.name) {
                            selector = `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
                        } else if (el.getAttribute('data-field')) {
                            selector = `[data-field="${CSS.escape(el.getAttribute('data-field'))}"]`;
                        } else if (el.getAttribute('aria-label')) {
                            selector = `[aria-label="${CSS.escape(el.getAttribute('aria-label'))}"]`;
                        }

                        // Determine type
                        let fieldType = 'text';
                        if (el.tagName === 'SELECT' || el.getAttribute('role') === 'combobox') fieldType = 'select';
                        else if (el.type === 'radio') fieldType = 'radio';
                        else if (el.type === 'checkbox') fieldType = 'checkbox';
                        else if (el.type === 'file') fieldType = 'file';
                        else if (el.type === 'email') fieldType = 'email';
                        else if (el.type === 'tel') fieldType = 'phone';
                        else if (el.type === 'number') fieldType = 'number';
                        else if (el.type === 'date') fieldType = 'date';
                        else if (el.type === 'url') fieldType = 'url';
                        else if (el.tagName === 'TEXTAREA') fieldType = 'textarea';

                        // Check for cover letter / custom file fields
                        const name = (el.name || '').toLowerCase();
                        const labelLower = label.toLowerCase();
                        const isCoverLetter = name.includes('cover') || labelLower.includes('cover letter');
                        const isResume = name.includes('resume') || name.includes('cv') || labelLower.includes('resume') || labelLower.includes('cv');

                        fields.push({
                            field_label: label,
                            field_name: el.name || '',
                            field_id: el.id || '',
                            field_type: fieldType,
                            field_selector: selector,
                            placeholder: el.placeholder || '',
                            aria_label: el.getAttribute('aria-label') || '',
                            section: section,
                            options: options,
                            required: required,
                            is_cover_letter: isCoverLetter,
                            is_resume: isResume,
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
            }''', self.SELECTORS)

            fields = raw_fields or []

        except Exception as e:
            logger.error('Greenhouse field extraction failed: %s', e)

        return fields

    async def fill_field(self, page, field: Dict[str, Any], value: str) -> bool:
        """Fill a single field on a Greenhouse form."""
        selector = field.get('field_selector', '')
        field_type = field.get('field_type', 'text')

        if not selector:
            logger.warning('No selector for field: %s', field.get('field_label'))
            return False

        try:
            element = await page.query_selector(selector)
            if not element:
                logger.warning('Element not found: %s', selector)
                return False

            if field_type == 'select':
                return await self._fill_select(page, element, value, field)
            elif field_type == 'radio':
                return await self._fill_radio(page, element, value, field)
            elif field_type == 'checkbox':
                return await self._fill_checkbox(page, element, value)
            elif field_type == 'textarea':
                return await self._fill_textarea(page, element, value)
            elif field_type == 'file':
                return False  # Files handled separately
            else:
                return await self._fill_text(page, element, value)

        except Exception as e:
            logger.error('Failed to fill field %s: %s', field.get('field_label'), e)
            return False

    async def _fill_text(self, page, element, value: str) -> bool:
        """Fill a text input field."""
        try:
            await element.click()
            await element.fill('')
            await element.type(value, delay=20)
            # Verify
            actual = await element.input_value()
            return actual.strip() == value.strip()
        except Exception as e:
            logger.error('Text fill failed: %s', e)
            return False

    async def _fill_textarea(self, page, element, value: str) -> bool:
        """Fill a textarea field."""
        try:
            await element.click()
            await element.fill(value)
            actual = await element.input_value()
            return actual.strip() == value.strip()
        except Exception as e:
            logger.error('Textarea fill failed: %s', e)
            return False

    async def _fill_select(self, page, element, value: str, field: Dict) -> bool:
        """Fill a select dropdown."""
        try:
            options = field.get('options', [])
            # Try to find matching option
            target_value = value
            for opt in options:
                if value.lower() in (opt.get('label', '').lower(), opt.get('value', '').lower()):
                    target_value = opt.get('value', value)
                    break

            # Use Playwright's select_option
            await page.evaluate('''(args) => {
                const { selector, value } = args;
                const el = document.querySelector(selector);
                if (!el || el.tagName !== 'SELECT') return;
                for (const opt of el.options) {
                    if (opt.value === value || opt.textContent.trim().toLowerCase() === value.toLowerCase()) {
                        el.value = opt.value;
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        break;
                    }
                }
            }''', {'selector': field['field_selector'], 'value': target_value})

            return True
        except Exception as e:
            logger.error('Select fill failed: %s', e)
            return False

    async def _fill_radio(self, page, element, value: str, field: Dict) -> bool:
        """Fill a radio button group."""
        try:
            options = field.get('options', [])
            name = field.get('field_name', '')
            if not name:
                return False

            # Find matching option
            target_value = value.lower()
            for opt in options:
                if target_value in (opt.get('label', '').lower(), opt.get('value', '').lower()):
                    # Click the matching radio
                    await page.evaluate('''(args) => {
                        const { name, value } = args;
                        const radios = document.querySelectorAll(`input[name="${name}"]`);
                        for (const r of radios) {
                            if (r.value === value || r.closest('label')?.textContent?.trim().toLowerCase() === value.toLowerCase()) {
                                r.checked = true;
                                r.dispatchEvent(new Event('change', { bubbles: true }));
                                r.dispatchEvent(new Event('click', { bubbles: true }));
                                break;
                            }
                        }
                    }''', {'name': name, 'value': opt.get('value', '')})
                    return True

            return False
        except Exception as e:
            logger.error('Radio fill failed: %s', e)
            return False

    async def _fill_checkbox(self, page, element, value: str) -> bool:
        """Fill a checkbox."""
        try:
            should_check = value.lower() in ('true', 'yes', '1', 'checked')
            is_checked = await element.is_checked()
            if should_check != is_checked:
                await element.click()
            return True
        except Exception as e:
            logger.error('Checkbox fill failed: %s', e)
            return False

    async def upload_resume(self, page, file_path: str) -> bool:
        """Upload a resume file to the Greenhouse form."""
        try:
            # Find file input for resume
            file_input = await page.query_selector(self.SELECTORS['resume_upload'])
            if not file_input:
                # Try broader search
                file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                logger.warning('No file input found for resume upload')
                return False

            await file_input.set_input_files(file_path)
            return True
        except Exception as e:
            logger.error('Resume upload failed: %s', e)
            return False

    async def upload_cover_letter(self, page, file_path: str) -> bool:
        """Upload a cover letter file."""
        try:
            cover_input = await page.query_selector(self.SELECTORS['cover_letter'] + ' input[type="file"]')
            if not cover_input:
                # Try to find any file input that's not the resume
                all_inputs = await page.query_selector_all('input[type="file"]')
                for inp in all_inputs:
                    name = await inp.get_attribute('name') or ''
                    if 'cover' in name.lower():
                        cover_input = inp
                        break
            if not cover_input:
                logger.warning('No file input found for cover letter')
                return False

            await cover_input.set_input_files(file_path)
            return True
        except Exception as e:
            logger.error('Cover letter upload failed: %s', e)
            return False

    async def validate(self, page) -> Dict[str, Any]:
        """Validate the form - check for errors and required fields."""
        errors = []
        try:
            # Check for visible error messages
            error_elements = await page.query_selector_all(self.SELECTORS['error'])
            for el in error_elements:
                text = await el.text_content()
                if text and text.strip():
                    errors.append(text.strip())

            # Check for required fields that are empty
            required_empty = await page.evaluate('''() => {
                const empty = [];
                const required = document.querySelectorAll('[aria-required="true"], .required, [required]');
                for (const el of required) {
                    if (el.offsetParent === null) continue;
                    const tag = el.tagName.toLowerCase();
                    const type = el.type || '';
                    if (tag === 'input' && (type === 'text' || type === 'email' || type === 'tel' || type === 'number')) {
                        if (!el.value.trim()) {
                            const label = el.closest('.field')?.querySelector('label')?.textContent?.trim() || el.name || 'Unknown';
                            empty.push(label);
                        }
                    } else if (tag === 'select') {
                        if (!el.value) {
                            const label = el.closest('.field')?.querySelector('label')?.textContent?.trim() || el.name || 'Unknown';
                            empty.push(label);
                        }
                    } else if (tag === 'textarea') {
                        if (!el.value.trim()) {
                            const label = el.closest('.field')?.querySelector('label')?.textContent?.trim() || el.name || 'Unknown';
                            empty.push(label);
                        }
                    }
                }
                return empty;
            }''')

            for field_name in (required_empty or []):
                errors.append(f'Required field empty: {field_name}')

        except Exception as e:
            logger.error('Validation check failed: %s', e)

        return {
            'valid': len(errors) == 0,
            'errors': errors,
        }

    async def submit(self, page) -> Dict[str, Any]:
        """Click the submit button on the Greenhouse form."""
        try:
            submit_btn = await page.query_selector(self.SELECTORS['submit'])
            if not submit_btn:
                # Try next button (multi-step form)
                submit_btn = await page.query_selector(self.SELECTORS['next'])
            if not submit_btn:
                return {'success': False, 'message': 'Submit button not found'}

            await submit_btn.click()

            # Wait for response
            await page.wait_for_timeout(3000)

            # Check for errors after submit
            has_error = await page.evaluate('''() => {
                const errors = document.querySelectorAll('.error, [class*="error"], [role="alert"]');
                return errors.length > 0;
            }''')

            if has_error:
                return {'success': False, 'message': 'Form has errors after submit attempt'}

            return {'success': True, 'message': 'Form submitted successfully'}

        except Exception as e:
            logger.error('Submit failed: %s', e)
            return {'success': False, 'message': str(e)}

    async def handle_multi_step(self, page, max_steps: int = 20) -> Dict[str, Any]:
        """Handle multi-step Greenhouse forms by clicking Next until submit is available."""
        steps_completed = 0

        for _ in range(max_steps):
            # Check if we're on the final step (submit button visible)
            submit = await page.query_selector(self.SELECTORS['submit'])
            if submit:
                break

            # Click next
            next_btn = await page.query_selector(self.SELECTORS['next'])
            if not next_btn:
                break

            try:
                await next_btn.click()
                await page.wait_for_timeout(2000)
                steps_completed += 1
            except Exception:
                break

        return {'steps_completed': steps_completed}


# Register adapter
greenhouse_adapter = GreenhouseAdapter()
