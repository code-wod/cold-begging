// Lever adapter — handles Lever-hosted job application forms
// Lever uses simple form fields with name attributes and data-qa selectors

import type { FormField } from '../types';

// ── Detect if page is Lever ─────────────────────────────────────────────────
export function isLeverPage(url: string): boolean {
  return /jobs\.lever\.co|lever\.co/i.test(url);
}

// ── Lever field mappings ────────────────────────────────────────────────────
const LEVER_FIELDS: Record<string, string> = {
  'name': 'Full Name',
  'email': 'Email',
  'phone': 'Phone',
  'org': 'Current Company',
  'urls[LinkedIn]': 'LinkedIn URL',
  'urls[GitHub]': 'GitHub URL',
  'urls[Portfolio]': 'Portfolio URL',
  'urls[Other]': 'Other URL',
  'comments': 'Cover Letter / Comments',
  'resume': 'Resume',
  'location': 'Location',
};

// ── Extract Lever fields ────────────────────────────────────────────────────
export function extractLeverFields(doc: Document): FormField[] {
  const fields: FormField[] = [];

  // Lever uses standard form elements with name attributes
  const inputs = doc.querySelectorAll('input, textarea, select');
  inputs.forEach((el) => {
    const name = el.getAttribute('name') || '';
    if (!name) return;

    const type = (el as HTMLInputElement).type || 'text';
    if (['file', 'hidden', 'submit', 'button', 'image'].includes(type)) return;

    const label = LEVER_FIELDS[name] ||
                  el.getAttribute('aria-label') ||
                  el.getAttribute('placeholder') ||
                  doc.querySelector(`label[for="${CSS.escape(name)}"]`)?.textContent?.trim() ||
                  name;

    fields.push({
      id: `lever_${name}`,
      elementType: el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'SELECT' ? 'select' : 'input',
      inputType: type,
      label: label.replace(/\*/g, '').trim(),
      name,
      selector: `[name="${CSS.escape(name)}"]`,
      required: (el as HTMLInputElement).required || (el as HTMLInputElement).getAttribute('aria-required') === 'true',
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    });
  });

  // Also check for data-qa fields
  const qaInputs = doc.querySelectorAll('[data-qa]');
  qaInputs.forEach((el) => {
    const qa = el.getAttribute('data-qa') || '';
    if (!qa) return;

    const type = (el as HTMLInputElement).type || 'text';
    if (['file', 'hidden', 'submit', 'button', 'image'].includes(type)) return;

    const name = el.getAttribute('name') || qa;
    if (fields.some(f => f.name === name)) return;

    const label = el.getAttribute('aria-label') ||
                  el.getAttribute('placeholder') ||
                  qa.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    fields.push({
      id: `lever_${qa}`,
      elementType: 'input',
      inputType: type,
      label,
      name,
      selector: `[data-qa="${CSS.escape(qa)}"]`,
      required: (el as HTMLInputElement).required,
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    });
  });

  return fields;
}

// ── Fill Lever field ────────────────────────────────────────────────────────
export function fillLeverField(fieldId: string, value: string): boolean {
  const rawId = fieldId.startsWith('lever_') ? fieldId.slice(6) : fieldId;

  let el = document.querySelector(`[name="${CSS.escape(rawId)}"]`) as HTMLInputElement;
  if (!el) el = document.querySelector(`[data-qa="${CSS.escape(rawId)}"]`) as HTMLInputElement;
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

// ── Map profile to Lever fields ─────────────────────────────────────────────
export function mapProfileToLever(profile: any): Record<string, string> {
  const m: Record<string, string> = {};
  if (profile.personal?.firstName && profile.personal?.lastName) {
    m['name'] = `${profile.personal.firstName} ${profile.personal.lastName}`;
  }
  if (profile.personal?.email) m['email'] = profile.personal.email;
  if (profile.personal?.phone) m['phone'] = profile.personal.phone;
  if (profile.professional?.currentCompany) m['org'] = profile.professional.currentCompany;
  if (profile.professional?.linkedin) m['urls[LinkedIn]'] = profile.professional.linkedin;
  if (profile.professional?.github) m['urls[GitHub]'] = profile.professional.github;
  if (profile.professional?.portfolio) m['urls[Portfolio]'] = profile.professional.portfolio;
  if (profile.personal?.address?.city) m['location'] = profile.personal.address.city;
  return m;
}

// ── Extract job info ────────────────────────────────────────────────────────
export function extractLeverJobInfo(doc: Document): { jobTitle: string; company: string } {
  const h1 = doc.querySelector('.posting-headline h2, h2');
  const jobTitle = h1?.textContent?.trim() || '';

  const companyEl = doc.querySelector('.posting-headline h1, .company-name');
  const company = companyEl?.textContent?.trim() || '';

  return { jobTitle, company };
}
