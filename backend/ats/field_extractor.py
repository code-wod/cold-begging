"""Generic Playwright-based form field extraction."""
import logging
from typing import List, Dict, Any

logger = logging.getLogger('ats.field_extractor')

# CSS selectors for common form field patterns
FIELD_SELECTORS = [
    # Standard inputs
    'input[type="text"]',
    'input[type="email"]',
    'input[type="tel"]',
    'input[type="number"]',
    'input[type="date"]',
    'input[type="url"]',
    'input[type="password"]',
    'input:not([type])',
    # Textareas
    'textarea',
    # Selects
    'select',
    # File inputs
    'input[type="file"]',
    # Radio buttons
    'input[type="radio"]',
    # Checkboxes
    'input[type="checkbox"]',
    # Custom dropdowns (common in ATS)
    '[role="combobox"]',
    '[role="listbox"]',
    '[data-qa*="input"]',
    '[data-qa*="select"]',
    '[data-qa*="text"]',
]

# Patterns for labels that indicate section headers (not actual fields)
SECTION_PATTERNS = [
    'personal information',
    'contact information',
    'education',
    'work experience',
    'skills',
    'additional information',
    'equal opportunity',
    'eeo',
    'voluntary self-identification',
]


def _classify_field_type(tag_name: str, input_type: str, role: str, options_count: int) -> str:
    """Classify a form field into a normalized type."""
    if tag_name == 'select' or (role in ('combobox', 'listbox')):
        return 'select'
    if input_type == 'radio':
        return 'radio'
    if input_type == 'checkbox':
        return 'checkbox'
    if input_type == 'file':
        return 'file'
    if input_type == 'email':
        return 'email'
    if input_type == 'tel':
        return 'phone'
    if input_type == 'number':
        return 'number'
    if input_type == 'date':
        return 'date'
    if input_type == 'url':
        return 'url'
    if tag_name == 'textarea':
        return 'textarea'
    return 'text'


def _extract_label(field_info: Dict[str, Any], page_text: str = '') -> str:
    """Extract the best label for a field from available info."""
    # Prioritize explicit label
    if field_info.get('label'):
        return field_info['label']
    if field_info.get('aria_label'):
        return field_info['aria_label']
    if field_info.get('placeholder'):
        return field_info['placeholder']
    if field_info.get('name'):
        # Convert snake_case or camelCase to readable
        name = field_info['name']
        return name.replace('_', ' ').replace('-', ' ').title()
    return ''


async def extract_fields(page, ats_platform: str = 'unknown') -> List[Dict[str, Any]]:
    """Extract all form fields from the page using Playwright.

    Returns a list of normalized field dictionaries.
    """
    fields = []

    try:
        # Use page.evaluate to extract field info from the DOM
        raw_fields = await page.evaluate('''() => {
            const fields = [];
            const selectors = [
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
                'textarea',
                'select',
                '[role="combobox"]',
                '[role="listbox"]',
            ];

            const seen = new Set();

            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    // Skip hidden elements
                    if (el.offsetParent === null && el.type !== 'file') continue;
                    if (el.disabled) continue;

                    // Build a unique key to deduplicate
                    const key = el.id || el.name || el.getAttribute('data-qa') || '';
                    if (key && seen.has(key)) continue;
                    if (key) seen.add(key);

                    // Find associated label
                    let label = '';
                    if (el.id) {
                        const labelEl = document.querySelector(`label[for="${el.id}"]`);
                        if (labelEl) label = labelEl.textContent.trim();
                    }
                    if (!label) {
                        const parent = el.closest('label');
                        if (parent) label = parent.textContent.trim();
                    }
                    if (!label) {
                        // Check preceding sibling or parent container
                        const prev = el.previousElementSibling;
                        if (prev && (prev.tagName === 'LABEL' || prev.tagName === 'SPAN')) {
                            label = prev.textContent.trim();
                        }
                    }
                    if (!label) {
                        // Check aria-label
                        label = el.getAttribute('aria-label') || '';
                    }

                    // Get options for select/radio
                    let options = [];
                    if (el.tagName === 'SELECT') {
                        options = Array.from(el.options).map(o => ({
                            value: o.value,
                            label: o.textContent.trim(),
                        })).filter(o => o.value && o.label);
                    } else if (el.type === 'radio') {
                        const name = el.name;
                        if (name) {
                            const radios = document.querySelectorAll(`input[name="${name}"]`);
                            options = Array.from(radios).map(r => ({
                                value: r.value,
                                label: r.closest('label')?.textContent?.trim() || r.value,
                            }));
                        }
                    }

                    // Find section (fieldset or heading group)
                    let section = '';
                    const fieldset = el.closest('fieldset');
                    if (fieldset) {
                        const legend = fieldset.querySelector('legend');
                        if (legend) section = legend.textContent.trim();
                    }
                    if (!section) {
                        const heading = el.closest('[class*="section"], [class*="group"], [data-qa*="section"]');
                        if (heading) {
                            const h = heading.querySelector('h2, h3, h4, [class*="title"]');
                            if (h) section = h.textContent.trim();
                        }
                    }

                    // Build CSS selector
                    let selector = '';
                    if (el.id) {
                        selector = `#${CSS.escape(el.id)}`;
                    } else if (el.name) {
                        selector = `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;
                    } else if (el.getAttribute('data-qa')) {
                        selector = `[data-qa="${CSS.escape(el.getAttribute('data-qa'))}"]`;
                    }

                    fields.push({
                        field_label: label,
                        field_name: el.name || '',
                        field_id: el.id || '',
                        field_type: el.tagName === 'SELECT' ? 'select'
                            : el.type === 'radio' ? 'radio'
                            : el.type === 'checkbox' ? 'checkbox'
                            : el.type === 'file' ? 'file'
                            : el.type === 'email' ? 'email'
                            : el.type === 'tel' ? 'phone'
                            : el.type === 'number' ? 'number'
                            : el.type === 'date' ? 'date'
                            : el.type === 'url' ? 'url'
                            : el.tagName === 'TEXTAREA' ? 'textarea'
                            : 'text',
                        field_selector: selector,
                        placeholder: el.placeholder || '',
                        aria_label: el.getAttribute('aria-label') || '',
                        section: section,
                        options: options,
                    });
                }
            }

            return fields;
        }''')

        for i, f in enumerate(raw_fields or []):
            f['order'] = i
            f['status'] = 'pending'
            f['confidence'] = 0.0
            f['mapped_value'] = ''
            f['profile_field'] = ''
            f['mapping_reasoning'] = ''
            f['requires_review'] = True
            fields.append(f)

    except Exception as e:
        logger.error('Field extraction failed: %s', e)

    return fields
