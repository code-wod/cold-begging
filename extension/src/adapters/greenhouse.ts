// Greenhouse-specific field extraction and filling
// This handles the exact Greenhouse form structure found at greenhouse.io

import type { FormField } from '../types';

// ── Greenhouse field definitions ─────────────────────────────────────────────
// Based on actual Greenhouse form HTML structure
const GREENHOUSE_FIELDS: Record<string, { label: string; type: string; autocomplete?: string }> = {
  'first_name': { label: 'First Name', type: 'text', autocomplete: 'given-name' },
  'last_name': { label: 'Last Name', type: 'text', autocomplete: 'family-name' },
  'email': { label: 'Email', type: 'text', autocomplete: 'email' },
  'phone': { label: 'Phone', type: 'tel' },
  'country': { label: 'Country', type: 'react-select' },
  'candidate-location': { label: 'Location', type: 'react-select' },
  'resume': { label: 'Resume/CV', type: 'file' },
  'cover_letter': { label: 'Cover Letter', type: 'file' },
  'company-name-0': { label: 'Company Name', type: 'text' },
  'title-0': { label: 'Title', type: 'text' },
  'start-date-month-0': { label: 'Start Date Month', type: 'react-select' },
  'start-date-year-0': { label: 'Start Date Year', type: 'text' },
  'end-date-month-0': { label: 'End Date Month', type: 'react-select' },
  'end-date-year-0': { label: 'End Date Year', type: 'text' },
  'current-role-0_1': { label: 'Current Role', type: 'checkbox' },
  'school--0': { label: 'School', type: 'react-select' },
  'degree--0': { label: 'Degree', type: 'react-select' },
  'discipline--0': { label: 'Discipline', type: 'react-select' },
};

// ── Extract Greenhouse fields ────────────────────────────────────────────────
export function extractGreenhouseFields(doc: Document): FormField[] {
  const fields: FormField[] = [];

  for (const [id, def] of Object.entries(GREENHOUSE_FIELDS)) {
    const el = doc.getElementById(id);
    if (!el) continue;

    const field: FormField = {
      id: `gh_${id}`,
      elementType: def.type === 'react-select' ? 'combobox' : def.type === 'file' ? 'input' : 'input',
      inputType: def.type === 'file' ? 'file' : def.type === 'react-select' ? 'text' : (el as HTMLInputElement).type || 'text',
      label: def.label,
      name: id,
      autocomplete: def.autocomplete,
      selector: `#${CSS.escape(id)}`,
      required: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    };

    fields.push(field);
  }

  // Also extract custom question fields (question_XXXXXXX pattern)
  const questionInputs = doc.querySelectorAll('input[id^="question_"], select[id^="question_"]');
  questionInputs.forEach((el) => {
    const id = el.id;
    const labelEl = doc.getElementById(`${id}-label`);
    const label = labelEl?.textContent?.replace('*', '').trim() || '';

    // Skip if already captured
    if (fields.some(f => f.name === id)) return;

    fields.push({
      id: `gh_${id}`,
      elementType: 'input',
      inputType: (el as HTMLInputElement).type || 'text',
      label,
      name: id,
      selector: `#${CSS.escape(id)}`,
      required: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    });
  });

  // Also get React Select comboboxes for questions
  const comboboxes = doc.querySelectorAll('[role="combobox"][id^="question_"]');
  comboboxes.forEach((el) => {
    const id = el.id;
    const labelEl = doc.getElementById(`${id}-label`);
    const label = labelEl?.textContent?.replace('*', '').trim() || '';

    if (fields.some(f => f.name === id)) return;

    fields.push({
      id: `gh_${id}`,
      elementType: 'combobox',
      inputType: 'text',
      label,
      name: id,
      selector: `#${CSS.escape(id)}`,
      required: el.getAttribute('aria-required') === 'true',
      currentValue: '',
      index: fields.length,
    });
  });

  return fields;
}

// ── Fill a Greenhouse field ──────────────────────────────────────────────────
export function fillGreenhouseField(fieldId: string, value: string): boolean {
  // Strip gh_ prefix
  const rawId = fieldId.startsWith('gh_') ? fieldId.slice(3) : fieldId;

  const el = document.getElementById(rawId);
  if (!el) return false;

  const def = GREENHOUSE_FIELDS[rawId];
  if (def?.type === 'react-select') {
    return fillReactSelect(rawId, value);
  }

  if (def?.type === 'checkbox') {
    const checkbox = el as HTMLInputElement;
    const shouldCheck = /^(yes|true|1)$/i.test(value);
    if (checkbox.checked !== shouldCheck) checkbox.click();
    return true;
  }

  if (def?.type === 'file') {
    return false; // File uploads need special handling
  }

  // Standard input
  return fillStandardInput(el as HTMLInputElement, value);
}

// ── Fill a standard input ───────────────────────────────────────────────────
function fillStandardInput(el: HTMLInputElement, value: string): boolean {
  if (el.readOnly || el.disabled) return false;

  el.focus();
  el.click();

  // Use native setter for React
  const nativeSetter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(el), 'value'
  )?.set;

  if (nativeSetter) {
    nativeSetter.call(el, value);
  } else {
    el.value = value;
  }

  // Full event sequence for React
  el.dispatchEvent(new Event('focus', { bubbles: true }));
  el.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new InputEvent('input', { bubbles: true, data: value, inputType: 'insertText', composed: true }));
  el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'a' }));
  el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'a' }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));
  el.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));

  return true;
}

// ── Fill a React Select dropdown ─────────────────────────────────────────────
// React Select requires: focus → type → wait for options → click option
function fillReactSelect(inputId: string, value: string): boolean {
  const input = document.getElementById(inputId) as HTMLInputElement;
  if (!input) return false;

  // Find the control container
  const control = input.closest('.select__control') || input.closest('[class*="control"]');
  if (!control) return false;

  // Focus and click to open
  input.focus();
  input.click();

  // Clear existing value
  const nativeSetter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(input), 'value'
  )?.set;

  if (nativeSetter) {
    nativeSetter.call(input, value);
  } else {
    input.value = value;
  }

  // Dispatch events to trigger React Select filtering
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new InputEvent('input', { bubbles: true, data: value, inputType: 'insertText' }));

  // Wait for options to appear, then click the matching one
  return new Promise<boolean>((resolve) => {
    setTimeout(() => {
      // Look for dropdown menu
      const menuId = `react-select-${inputId}-listbox`;
      let menu = document.getElementById(menuId);

      if (!menu) {
        // Try finding any open menu
        menu = document.querySelector('[class*="MenuList"], [role="listbox"], [class*="menu-list"]');
      }

      if (!menu) {
        // Try looking for options in any dropdown
        const options = document.querySelectorAll('[role="option"], [class*="option"]');
        for (const opt of Array.from(options)) {
          const text = opt.textContent?.trim().toLowerCase() || '';
          if (text.includes(value.toLowerCase()) || value.toLowerCase().includes(text)) {
            (opt as HTMLElement).click();
            resolve(true);
            return;
          }
        }
        resolve(false);
        return;
      }

      // Find matching option in menu
      const options = menu.querySelectorAll('[role="option"], [class*="option"], [id*="option"]');
      for (const opt of Array.from(options)) {
        const text = opt.textContent?.trim().toLowerCase() || '';
        if (text.includes(value.toLowerCase()) || value.toLowerCase().includes(text)) {
          (opt as HTMLElement).click();
          resolve(true);
          return;
        }
      }

      resolve(false);
    }, 300);
  }) as any;
}

// ── Map profile to Greenhouse fields ─────────────────────────────────────────
export function mapProfileToGreenhouse(profile: any): Record<string, string> {
  const mapping: Record<string, string> = {};

  if (profile.personal?.firstName) mapping['first_name'] = profile.personal.firstName;
  if (profile.personal?.lastName) mapping['last_name'] = profile.personal.lastName;
  if (profile.personal?.email) mapping['email'] = profile.personal.email;
  if (profile.personal?.phone) mapping['phone'] = profile.personal.phone;
  if (profile.personal?.address?.country) mapping['country'] = profile.personal.address.country;
  if (profile.personal?.address?.city) mapping['candidate-location'] = profile.personal.address.city;
  if (profile.professional?.currentCompany) mapping['company-name-0'] = profile.professional.currentCompany;
  if (profile.professional?.currentTitle) mapping['title-0'] = profile.professional.currentTitle;
  if (profile.professional?.linkedin) mapping['question_68978657'] = profile.professional.linkedin;

  return mapping;
}

// ── Detect if page is Greenhouse ─────────────────────────────────────────────
export function isGreenhousePage(url: string): boolean {
  return /greenhouse\.io/i.test(url) || /boards\.greenhouse\.io/i.test(url);
}

// ── Extract job title from page ──────────────────────────────────────────────
export function extractJobTitle(doc: Document): string {
  const h1 = doc.querySelector('h1');
  return h1?.textContent?.trim() || '';
}

// ── Extract company from page ────────────────────────────────────────────────
export function extractCompany(doc: Document, url: string): string {
  // Try from URL
  try {
    const params = new URL(url).searchParams;
    const forParam = params.get('for');
    if (forParam) return forParam.charAt(0).toUpperCase() + forParam.slice(1);
  } catch {}

  // Try from page
  const backLink = doc.querySelector('a.link');
  if (backLink) {
    const text = backLink.textContent?.trim() || '';
    if (text.includes('Back to')) return text.replace('Back to', '').trim();
  }

  return '';
}
