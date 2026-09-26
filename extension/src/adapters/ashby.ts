// Ashby adapter — handles Ashby-hosted job application forms
// Ashby uses custom components with data-testid attributes

import type { FormField } from '../types';

// ── Detect if page is Ashby ─────────────────────────────────────────────────
export function isAshbyPage(url: string): boolean {
  return /jobs\.ashbyhq\.com|ashbyhq\.com/i.test(url);
}

// ── Extract Ashby fields ────────────────────────────────────────────────────
export function extractAshbyFields(doc: Document): FormField[] {
  const fields: FormField[] = [];

  // Ashby uses standard form elements
  const inputs = doc.querySelectorAll('input, textarea, select');
  inputs.forEach((el) => {
    const type = (el as HTMLInputElement).type || 'text';
    if (['file', 'hidden', 'submit', 'button', 'image'].includes(type)) return;

    const id = el.id || el.getAttribute('name') || '';
    const label = el.getAttribute('aria-label') ||
                  el.getAttribute('placeholder') ||
                  (id ? doc.querySelector(`label[for="${CSS.escape(id)}"]`)?.textContent?.trim() : '') ||
                  '';

    if (!label && !id) return;

    const name = el.getAttribute('name') || id;
    const selector = id ? `#${CSS.escape(id)}` : `[name="${CSS.escape(name)}"]`;

    fields.push({
      id: `ashby_${name}`,
      elementType: el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'SELECT' ? 'select' : 'input',
      inputType: type,
      label: label.replace(/\*/g, '').trim() || name,
      name,
      selector,
      required: (el as HTMLInputElement).required || (el as HTMLInputElement).getAttribute('aria-required') === 'true',
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    });
  });

  // Also check data-testid
  const testIdInputs = doc.querySelectorAll('[data-testid]');
  testIdInputs.forEach((el) => {
    const testId = el.getAttribute('data-testid') || '';
    if (!testId) return;

    const type = (el as HTMLInputElement).type || 'text';
    if (['file', 'hidden', 'submit', 'button', 'image'].includes(type)) return;

    const name = el.getAttribute('name') || testId;
    if (fields.some(f => f.name === name)) return;

    const label = el.getAttribute('aria-label') ||
                  el.getAttribute('placeholder') ||
                  testId.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    fields.push({
      id: `ashby_${testId}`,
      elementType: 'input',
      inputType: type,
      label,
      name,
      selector: `[data-testid="${CSS.escape(testId)}"]`,
      required: (el as HTMLInputElement).required,
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    });
  });

  return fields;
}

// ── Fill Ashby field ────────────────────────────────────────────────────────
export function fillAshbyField(fieldId: string, value: string): boolean {
  const rawId = fieldId.startsWith('ashby_') ? fieldId.slice(6) : fieldId;

  let el = document.getElementById(rawId) as HTMLInputElement;
  if (!el) el = document.querySelector(`[name="${CSS.escape(rawId)}"]`) as HTMLInputElement;
  if (!el) el = document.querySelector(`[data-testid="${CSS.escape(rawId)}"]`) as HTMLInputElement;
  if (!el) return false;

  if (el.readOnly || el.disabled) return false;

  el.focus();
  el.dispatchEvent(new FocusEvent('focus', { bubbles: true }));
  el.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));

  const nativeSetter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(el), 'value'
  )?.set;

  if (nativeSetter) {
    nativeSetter.call(el, value);
  } else {
    el.value = value;
  }

  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new InputEvent('input', {
    bubbles: true, cancelable: true, inputType: 'insertText', data: value, composed: true,
  }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));

  return el.value === value;
}

// ── Map profile to Ashby fields ─────────────────────────────────────────────
export function mapProfileToAshby(profile: any): Record<string, string> {
  const m: Record<string, string> = {};
  if (profile.personal?.firstName) m['firstName'] = profile.personal.firstName;
  if (profile.personal?.lastName) m['lastName'] = profile.personal.lastName;
  if (profile.personal?.email) m['email'] = profile.personal.email;
  if (profile.personal?.phone) m['phone'] = profile.personal.phone;
  if (profile.personal?.address?.city) m['location'] = profile.personal.address.city;
  if (profile.professional?.currentCompany) m['company'] = profile.professional.currentCompany;
  if (profile.professional?.currentTitle) m['title'] = profile.professional.currentTitle;
  if (profile.professional?.linkedin) m['linkedin'] = profile.professional.linkedin;
  return m;
}

// ── Extract job info ────────────────────────────────────────────────────────
export function extractAshbyJobInfo(doc: Document): { jobTitle: string; company: string } {
  const h1 = doc.querySelector('h1, h2, [class*="job-title"]');
  const jobTitle = h1?.textContent?.trim() || '';

  const companyEl = doc.querySelector('[class*="company"], [class*="organization"]');
  const company = companyEl?.textContent?.trim() || '';

  return { jobTitle, company };
}
