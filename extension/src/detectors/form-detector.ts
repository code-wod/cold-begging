import type { FormField, FieldType, InputType } from '../types';

let fieldCounter = 0;

function generateFieldId(): string {
  return `field_${++fieldCounter}_${Date.now().toString(36)}`;
}

function getSelector(el: Element): string {
  if (el.id) return `#${CSS.escape(el.id)}`;
  if (el.getAttribute('name')) return `[name="${CSS.escape(el.getAttribute('name')!)}"]`;
  if (el.getAttribute('data-automation-id')) return `[data-automation-id="${CSS.escape(el.getAttribute('data-automation-id')!)}"]`;
  if (el.getAttribute('aria-label')) return `[aria-label="${CSS.escape(el.getAttribute('aria-label')!)}"]`;

  // Build path
  const parts: string[] = [];
  let current: Element | null = el;
  while (current && current !== document.body) {
    let selector = current.tagName.toLowerCase();
    if (current.id) { selector = `#${CSS.escape(current.id)}`; parts.unshift(selector); break; }
    if (current.className && typeof current.className === 'string') {
      const cls = current.className.split(/\s+/).filter(c => c && !c.startsWith('css-')).slice(0, 2).map(c => `.${CSS.escape(c)}`).join('');
      if (cls) selector += cls;
    }
    const parent = current.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(c => c.tagName === current!.tagName);
      if (siblings.length > 1) {
        const idx = siblings.indexOf(current) + 1;
        selector += `:nth-of-type(${idx})`;
      }
    }
    parts.unshift(selector);
    current = current.parentElement;
  }
  return parts.join(' > ');
}

function getLabel(el: Element): string | undefined {
  // Check associated label
  if (el.id) {
    const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (label) return label.textContent?.trim();
  }

  // Check parent label
  const parentLabel = el.closest('label');
  if (parentLabel) {
    const clone = parentLabel.cloneNode(true) as HTMLElement;
    // Remove the input itself from the clone to get just the label text
    const inputs = clone.querySelectorAll('input, select, textarea');
    inputs.forEach(i => i.remove());
    const text = clone.textContent?.trim();
    if (text) return text;
  }

  // Check aria-label
  const ariaLabel = el.getAttribute('aria-label');
  if (ariaLabel) return ariaLabel;

  // Check previous sibling text
  const prev = el.previousElementSibling;
  if (prev) {
    const text = prev.textContent?.trim();
    if (text && text.length < 100) return text;
  }

  return undefined;
}

function getSection(el: Element): string | undefined {
  // Walk up to find section/fieldset/legend
  let current: Element | null = el;
  while (current && current !== document.body) {
    if (current.tagName === 'FIELDSET') {
      const legend = current.querySelector('legend');
      if (legend) return legend.textContent?.trim();
    }
    if (current.getAttribute('role') === 'group' || current.getAttribute('role') === 'region') {
      const label = current.getAttribute('aria-label') || current.getAttribute('aria-labelledby');
      if (label) {
        const labelEl = label.startsWith('http') ? null : document.getElementById(label);
        return labelEl?.textContent?.trim() || label;
      }
    }
    // Check for section headings
    const heading = current.querySelector('h1, h2, h3, h4, h5, h6');
    if (heading && current.contains(el)) {
      return heading.textContent?.trim();
    }
    current = current.parentElement;
  }
  return undefined;
}

function getSurroundingText(el: Element, range: number = 2): string {
  const texts: string[] = [];
  let sibling: Element | null = el;

  // Get preceding siblings
  for (let i = 0; i < range; i++) {
    sibling = sibling.previousElementSibling;
    if (!sibling) break;
    const text = sibling.textContent?.trim();
    if (text && text.length < 200) texts.unshift(text);
  }

  // Get following siblings
  sibling = el;
  for (let i = 0; i < range; i++) {
    sibling = sibling.nextElementSibling;
    if (!sibling) break;
    const text = sibling.textContent?.trim();
    if (text && text.length < 200) texts.push(text);
  }

  return texts.join(' ');
}

function getPageContext(el: Element): string {
  // Get nearby headings, company name, job title
  const contexts: string[] = [];

  // Check for job title
  const h1 = document.querySelector('h1');
  if (h1) contexts.push(h1.textContent?.trim() || '');

  // Check for company
  const companyEl = document.querySelector('[class*="company"], [data-company], .company-name');
  if (companyEl) contexts.push(companyEl.textContent?.trim() || '');

  // Check for job metadata
  const metaEls = document.querySelectorAll('[class*="job"], [class*="position"], [class*="role"]');
  metaEls.forEach(el => {
    const text = el.textContent?.trim();
    if (text && text.length < 100) contexts.push(text);
  });

  return contexts.filter(Boolean).join(' | ');
}

function isHidden(el: Element): boolean {
  const style = window.getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return true;
  if (el.getAttribute('type') === 'hidden') return true;
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return true;
  return false;
}

function isInteractive(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  const type = (el as HTMLInputElement).type?.toLowerCase();

  // Skip non-interactive elements
  if (['script', 'style', 'link', 'meta', 'head', 'title'].includes(tag)) return false;
  if (tag === 'input' && ['hidden', 'submit', 'button', 'reset', 'image'].includes(type || '')) return false;
  if (tag === 'button' && (el as HTMLButtonElement).type === 'submit') return false;

  return true;
}

function getOptions(el: HTMLSelectElement): { value: string; label: string }[] {
  return Array.from(el.options)
    .filter(opt => opt.value && opt.value !== '')
    .map(opt => ({ value: opt.value, label: opt.textContent?.trim() || opt.value }));
}

function detectFieldType(el: Element): { elementType: FieldType; inputType?: InputType } {
  const tag = el.tagName.toLowerCase();
  if (tag === 'select') return { elementType: 'select' };
  if (tag === 'textarea') return { elementType: 'textarea' };
  if (tag === 'input') {
    const type = (el as HTMLInputElement).type?.toLowerCase() || 'text';
    if (type === 'checkbox') return { elementType: 'checkbox', inputType: type };
    if (type === 'radio') return { elementType: 'radio', inputType: type };
    return { elementType: 'input', inputType: type };
  }
  // Check for custom combobox / autocomplete
  const role = el.getAttribute('role');
  if (role === 'combobox' || role === 'listbox') return { elementType: 'combobox' };
  // Check for contenteditable
  if (el.getAttribute('contenteditable') === 'true') return { elementType: 'textarea' };
  return { elementType: 'input', inputType: 'text' };
}

export function extractFormFields(root: Document = document): FormField[] {
  const fields: FormField[] = [];
  const selectors = 'input, textarea, select, [role="combobox"], [contenteditable="true"], [data-automation-id]';
  const elements = root.querySelectorAll<HTMLElement>(selectors);

  elements.forEach((el, index) => {
    // Skip hidden and non-interactive
    if (isHidden(el)) return;
    if (!isInteractive(el)) return;

    // Skip submit buttons and navigation elements
    if (el.closest('nav, [role="navigation"], [class*="nav"]')) return;
    if (el.closest('[class*="footer"], footer')) return;

    const { elementType, inputType } = detectFieldType(el);
    const label = getLabel(el);
    const name = el.getAttribute('name') || undefined;
    const placeholder = el.getAttribute('placeholder') || undefined;
    const ariaLabel = el.getAttribute('aria-label') || undefined;
    const autocomplete = el.getAttribute('autocomplete') || undefined;
    const section = getSection(el);
    const surroundingText = getSurroundingText(el);
    const pageContext = getPageContext(el);
    const required = el.hasAttribute('required') || el.getAttribute('aria-required') === 'true';
    const currentValue = (el as HTMLInputElement).value || '';
    const options = el.tagName === 'SELECT' ? getOptions(el as HTMLSelectElement) : undefined;

    fields.push({
      id: generateFieldId(),
      elementType,
      inputType,
      label,
      name,
      placeholder,
      ariaLabel,
      autocomplete,
      options,
      section,
      surroundingText,
      selector: getSelector(el),
      required,
      currentValue,
      pageContext,
      index,
    });
  });

  return fields;
}

// Re-fetch the DOM element for a field
export function getFieldElement(field: FormField): Element | null {
  try {
    // Try exact selector first
    const el = document.querySelector(field.selector);
    if (el) return el;

    // Fallback: match by name/label
    if (field.name) {
      const byName = document.querySelector(`[name="${CSS.escape(field.name)}"]`);
      if (byName) return byName;
    }
    if (field.label) {
      const labels = document.querySelectorAll('label');
      for (const label of labels) {
        if (label.textContent?.trim() === field.label) {
          const forAttr = label.getAttribute('for');
          if (forAttr) return document.getElementById(forAttr);
          return label.querySelector('input, select, textarea');
        }
      }
    }
  } catch { /* selector invalid */ }
  return null;
}
