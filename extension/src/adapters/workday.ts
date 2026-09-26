// Workday adapter — handles Workday-hosted job application forms
// Workday uses custom web components with data-automation-id attributes

import type { FormField } from '../types';

// ── Detect if page is Workday ───────────────────────────────────────────────
export function isWorkdayPage(url: string): boolean {
  return /myworkday\.com|workday\.com|wday\.com/i.test(url);
}

// ── Workday field selectors ─────────────────────────────────────────────────
// Workday uses data-automation-id for nearly everything
const WORKDAY_TEXT_AUTOMATION_IDS: Record<string, string> = {
  'firstLegalName\$input': 'First Name',
  'lastName\$input': 'Last Name',
  'email\$input': 'Email',
  'phone\$input': 'Phone',
  'addressLine1\$input': 'Street Address',
  'city\$input': 'City',
  'state\$input': 'State/Province',
  'postalCode\$input': 'Postal Code',
  'country\$input': 'Country',
  'companyName\$input': 'Current Company',
  'title\$input': 'Job Title',
  'linkedin\$input': 'LinkedIn URL',
  'website\$input': 'Website/Portfolio',
  'educationSchool\$input': 'School',
  'educationDegree\$input': 'Degree',
  'educationMajor\$input': 'Major/Field',
  'educationEndDate\$input': 'Graduation Date',
  'currentSalary\$input': 'Current Salary',
  'desiredSalary\$input': 'Desired Salary',
};

// ── Extract Workday fields ──────────────────────────────────────────────────
export function extractWorkdayFields(doc: Document): FormField[] {
  const fields: FormField[] = [];

  // Find all data-automation-id inputs
  const allInputs = doc.querySelectorAll('input[data-automation-id], textarea[data-automation-id], select[data-automation-id]');
  allInputs.forEach((el) => {
    const automationId = el.getAttribute('data-automation-id') || '';
    if (!automationId) return;

    // Skip file uploads, hidden, submit
    const type = (el as HTMLInputElement).type || 'text';
    if (['file', 'hidden', 'submit', 'button'].includes(type)) return;

    // Get label from aria-label, placeholder, or automation ID
    const label = (el as HTMLInputElement).getAttribute('aria-label') ||
                  (el as HTMLInputElement).placeholder ||
                  WORKDAY_TEXT_AUTOMATION_IDS[automationId] ||
                  automationId.replace(/[\\\$]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    fields.push({
      id: `wd_${automationId}`,
      elementType: el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'SELECT' ? 'select' : 'input',
      inputType: type,
      label,
      name: automationId,
      selector: `[data-automation-id="${CSS.escape(automationId)}"]`,
      required: (el as HTMLInputElement).required || (el as HTMLInputElement).getAttribute('aria-required') === 'true',
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    });
  });

  // Also look for standard labeled inputs
  const labels = doc.querySelectorAll('label');
  labels.forEach((labelEl) => {
    const forId = labelEl.getAttribute('for');
    if (!forId) return;

    const el = doc.getElementById(forId) as HTMLInputElement;
    if (!el) return;

    const type = el.type || 'text';
    if (['file', 'hidden', 'submit', 'button'].includes(type)) return;

    // Skip if already captured
    if (fields.some(f => f.name === forId)) return;

    const labelText = labelEl.textContent?.trim().replace('*', '').trim() || forId;

    fields.push({
      id: `wd_${forId}`,
      elementType: el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'SELECT' ? 'select' : 'input',
      inputType: type,
      label: labelText,
      name: forId,
      selector: `#${CSS.escape(forId)}`,
      required: el.required || el.getAttribute('aria-required') === 'true',
      currentValue: el.value || '',
      index: fields.length,
    });
  });

  return fields;
}

// ── Fill Workday field ──────────────────────────────────────────────────────
export function fillWorkdayField(fieldId: string, value: string): boolean {
  const rawId = fieldId.startsWith('wd_') ? fieldId.slice(3) : fieldId;

  // Try data-automation-id first
  let el = document.querySelector(`[data-automation-id="${rawId}"]`) as HTMLInputElement;
  if (!el) {
    // Try by ID
    el = document.getElementById(rawId) as HTMLInputElement;
  }
  if (!el) return false;

  return fillWorkdayInput(el, value);
}

function fillWorkdayInput(el: HTMLInputElement, value: string): boolean {
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

// ── Map profile to Workday fields ───────────────────────────────────────────
export function mapProfileToWorkday(profile: any): Record<string, string> {
  const m: Record<string, string> = {};
  if (profile.personal?.firstName) m['firstLegalName\\$input'] = profile.personal.firstName;
  if (profile.personal?.lastName) m['lastName\\$input'] = profile.personal.lastName;
  if (profile.personal?.email) m['email\\$input'] = profile.personal.email;
  if (profile.personal?.phone) m['phone\\$input'] = profile.personal.phone;
  if (profile.personal?.address?.street) m['addressLine1\\$input'] = profile.personal.address.street;
  if (profile.personal?.address?.city) m['city\\$input'] = profile.personal.address.city;
  if (profile.personal?.address?.state) m['state\\$input'] = profile.personal.address.state;
  if (profile.personal?.address?.country) m['country\\$input'] = profile.personal.address.country;
  if (profile.personal?.address?.postalCode) m['postalCode\\$input'] = profile.personal.address.postalCode;
  if (profile.professional?.currentCompany) m['companyName\\$input'] = profile.professional.currentCompany;
  if (profile.professional?.currentTitle) m['title\\$input'] = profile.professional.currentTitle;
  if (profile.professional?.linkedin) m['linkedin\\$input'] = profile.professional.linkedin;
  if (profile.professional?.github) m['website\\$input'] = profile.professional.github;
  return m;
}

// ── Extract job info ────────────────────────────────────────────────────────
export function extractWorkdayJobInfo(doc: Document): { jobTitle: string; company: string } {
  const h1 = doc.querySelector('h1, [data-automation-id="jobPostingHeader"]');
  const jobTitle = h1?.textContent?.trim() || '';

  // Company from URL or page
  const companyEl = doc.querySelector('[data-automation-id="companyName"]');
  const company = companyEl?.textContent?.trim() || '';

  return { jobTitle, company };
}
