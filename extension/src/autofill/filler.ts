import type { FormField, FieldSuggestion } from '../types';

// ── Fill a single field by walking DOM directly (no selectors) ──────────────
export function fillField(field: FormField, value: string): boolean {
  const el = resolveElement(field);
  if (!el) {
    console.warn('[Cold-Begging] Could not resolve element for:', field.label || field.name);
    return false;
  }

  try {
    const tag = el.tagName.toLowerCase();
    const inputType = (el as HTMLInputElement).type?.toLowerCase();

    if (tag === 'select') return fillSelect(el as HTMLSelectElement, value);
    if (inputType === 'checkbox') return fillCheckbox(el as HTMLInputElement, value);
    if (inputType === 'radio') return fillRadio(el as HTMLInputElement, value);
    if (tag === 'textarea' || el.getAttribute('contenteditable') === 'true') return fillTextarea(el, value);
    if (tag === 'input') return fillInput(el as HTMLInputElement, value);

    const role = el.getAttribute('role');
    if (role === 'combobox' || role === 'listbox') return fillCombobox(el, value);

    // Fallback: try setting value on any element
    return fillInput(el as HTMLInputElement, value);
  } catch (err) {
    console.error('[Cold-Begging] Fill error:', field.label, err);
    return false;
  }
}

// ── Resolve element using multiple strategies (not just CSS selector) ───────
function resolveElement(field: FormField): Element | null {
  // Strategy 1: Try the stored selector
  if (field.selector) {
    try {
      const el = document.querySelector(field.selector);
      if (el) return el;
    } catch { /* invalid selector */ }
  }

  // Strategy 2: Find by name attribute
  if (field.name) {
    const el = document.querySelector(`[name="${CSS.escape(field.name)}"]`);
    if (el) return el;
  }

  // Strategy 3: Find by label text → for/id association
  if (field.label) {
    const labels = document.querySelectorAll('label');
    for (const label of labels) {
      if (label.textContent?.trim().includes(field.label) || field.label.includes(label.textContent?.trim() || '')) {
        // Check for 'for' attribute
        const forAttr = label.getAttribute('for');
        if (forAttr) {
          const el = document.getElementById(forAttr);
          if (el) return el;
        }
        // Check for nested input
        const nested = label.querySelector('input, select, textarea');
        if (nested) return nested;
        // Check sibling
        const next = label.nextElementSibling;
        if (next && ['INPUT', 'SELECT', 'TEXTAREA'].includes(next.tagName)) return next;
      }
    }
  }

  // Strategy 4: Find by aria-label
  if (field.ariaLabel) {
    const el = document.querySelector(`[aria-label="${CSS.escape(field.ariaLabel)}"]`);
    if (el) return el;
  }

  // Strategy 5: Find by placeholder
  if (field.placeholder) {
    const el = document.querySelector(`[placeholder="${CSS.escape(field.placeholder)}"]`);
    if (el) return el;
  }

  // Strategy 6: Walk all inputs and match by autocomplete attribute
  if (field.autocomplete) {
    const el = document.querySelector(`[autocomplete="${CSS.escape(field.autocomplete)}"]`);
    if (el) return el;
  }

  // Strategy 7: Brute force — find all inputs of the right type near the label text
  if (field.label || field.name) {
    const searchText = (field.label || field.name || '').toLowerCase();
    const allInputs = document.querySelectorAll('input, select, textarea');
    for (const input of allInputs) {
      const inputEl = input as HTMLInputElement;
      // Check nearby text
      const parent = input.closest('div, fieldset, section, tr, li');
      if (parent) {
        const parentText = parent.textContent?.toLowerCase() || '';
        if (parentText.includes(searchText)) {
          // Check type match
          if (field.inputType && inputEl.type && field.inputType === inputEl.type) return input;
          if (!field.inputType || field.inputType === 'text') return input;
        }
      }
    }
  }

  return null;
}

// ── Input filling ───────────────────────────────────────────────────────────
function fillInput(el: HTMLInputElement, value: string): boolean {
  // Skip read-only/disabled
  if (el.readOnly || el.disabled) return false;

  // Focus first
  el.focus();
  el.click();

  // Use native setter for React controlled inputs
  const nativeSetter = getNativeSetter(el, 'value');
  if (nativeSetter) {
    nativeSetter.call(el, value);
  } else {
    el.value = value;
  }

  // Dispatch full event sequence for React/Vue/Angular
  dispatchEvents(el, value);
  return true;
}

// ── Textarea filling ────────────────────────────────────────────────────────
function fillTextarea(el: Element, value: string): boolean {
  if (el.getAttribute('contenteditable') === 'true') {
    el.textContent = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  const textarea = el as HTMLTextAreaElement;
  if (textarea.readOnly || textarea.disabled) return false;

  textarea.focus();
  const nativeSetter = getNativeSetter(textarea, 'value');
  if (nativeSetter) {
    nativeSetter.call(textarea, value);
  } else {
    textarea.value = value;
  }
  dispatchEvents(textarea, value);
  return true;
}

// ── Select filling ──────────────────────────────────────────────────────────
function fillSelect(el: HTMLSelectElement, value: string): boolean {
  if (el.disabled) return false;
  const valueLower = value.toLowerCase();

  // Exact match
  for (const option of Array.from(el.options)) {
    if (option.value === value || option.textContent?.trim() === value) {
      el.value = option.value;
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }
  }

  // Partial match
  for (const option of Array.from(el.options)) {
    const label = option.textContent?.trim().toLowerCase() || '';
    if (label.includes(valueLower) || valueLower.includes(label)) {
      el.value = option.value;
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }
  }

  return false;
}

// ── Checkbox filling ────────────────────────────────────────────────────────
function fillCheckbox(el: HTMLInputElement, value: string): boolean {
  const shouldBeChecked = /^(yes|true|1|checked)$/i.test(value);
  if (el.checked !== shouldBeChecked) {
    el.click();
  }
  return true;
}

// ── Radio filling ───────────────────────────────────────────────────────────
function fillRadio(el: HTMLInputElement, value: string): boolean {
  const label = el.labels?.[0]?.textContent?.trim().toLowerCase() || '';
  const elValue = el.value.toLowerCase();
  const valueLower = value.toLowerCase();

  if (label.includes(valueLower) || valueLower.includes(label) || elValue === valueLower) {
    el.click();
    return true;
  }
  return false;
}

// ── Combobox filling ────────────────────────────────────────────────────────
function fillCombobox(el: Element, value: string): boolean {
  const input = el.querySelector('input') || el;
  (input as HTMLElement).focus();
  (input as HTMLElement).click();

  const nativeSetter = getNativeSetter(input as HTMLInputElement, 'value');
  if (nativeSetter) {
    nativeSetter.call(input, value);
  } else {
    (input as HTMLInputElement).value = value;
  }
  dispatchEvents(input as HTMLInputElement, value);

  // Try to click matching option after a delay
  setTimeout(() => {
    const options = document.querySelectorAll('[role="option"], [class*="option"], [class*="suggestion"], li');
    for (const option of Array.from(options)) {
      const text = option.textContent?.trim().toLowerCase() || '';
      if (text.includes(value.toLowerCase()) || value.toLowerCase().includes(text)) {
        (option as HTMLElement).click();
        break;
      }
    }
  }, 300);

  return true;
}

// ── Fill multiple fields ────────────────────────────────────────────────────
export interface FillResult {
  fieldId: string;
  fieldLabel?: string;
  success: boolean;
}

export function fillFields(fields: FormField[], suggestions: FieldSuggestion[]): FillResult[] {
  const results: FillResult[] = [];

  for (const suggestion of suggestions) {
    if (!suggestion.value) {
      results.push({ fieldId: suggestion.fieldId, success: false });
      continue;
    }

    const field = fields.find(f => f.id === suggestion.fieldId);
    if (!field) {
      results.push({ fieldId: suggestion.fieldId, success: false });
      continue;
    }

    const success = fillField(field, suggestion.value);
    results.push({
      fieldId: suggestion.fieldId,
      success,
      fieldLabel: field.label || field.name,
    });
  }

  return results;
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function getNativeSetter(el: Element, prop: string): ((value: string) => void) | undefined {
  // Walk up prototype chain to find the native setter
  let current: any = el;
  while (current) {
    const descriptor = Object.getOwnPropertyDescriptor(current, prop);
    if (descriptor?.set) return descriptor.set;
    current = Object.getPrototypeOf(current);
  }
  // Last resort: use HTMLInputElement.prototype
  const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, prop);
  return descriptor?.set as ((value: string) => void) | undefined;
}

function dispatchEvents(el: Element, value: string): void {
  // Focus events
  el.dispatchEvent(new Event('focus', { bubbles: true }));
  el.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));

  // Input events — key for React
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new InputEvent('input', { bubbles: true, data: value, inputType: 'insertText', composed: true }));

  // React uses keydown/keyup
  el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'a' }));
  el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'a' }));

  // Change event
  el.dispatchEvent(new Event('change', { bubbles: true }));

  // Blur
  el.dispatchEvent(new Event('blur', { bubbles: true }));
  el.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
}

// ── Navigate to next step ───────────────────────────────────────────────────
export function findAndClickNextStep(): boolean {
  const nextPatterns = [
    /^next$/i, /^continue$/i, /^proceed$/i, /^save.*next$/i,
    /^next step$/i, /^forward$/i, /^submit$/i,
  ];

  const buttons = document.querySelectorAll('button, input[type="submit"], a[role="button"], [role="button"]');
  for (const btn of Array.from(buttons)) {
    const text = (btn.textContent || (btn as HTMLInputElement).value || '').trim();
    if (nextPatterns.some(p => p.test(text))) {
      (btn as HTMLElement).click();
      return true;
    }
  }
  return false;
}
