import type { FormField, AutofillState, Platform } from '../types';
import {
  isGreenhousePage, extractGreenhouseFields, fillGreenhouseField as _fillGH, extractJobTitle as _ghTitle, extractCompany as _ghCompany,
} from '../adapters/greenhouse';
import {
  isWorkdayPage, extractWorkdayFields, fillWorkdayField as _fillWD, extractWorkdayJobInfo,
} from '../adapters/workday';
import {
  isLeverPage, extractLeverFields, fillLeverField as _fillLever, extractLeverJobInfo,
} from '../adapters/lever';
import {
  isAshbyPage, extractAshbyFields, fillAshbyField as _fillAshby, extractAshbyJobInfo,
} from '../adapters/ashby';
import {
  isSmartRecruitersPage, extractSmartRecruitersFields, fillSmartRecruitersField as _fillSR, extractSmartRecruitersJobInfo,
} from '../adapters/smartrecruiters';

let currentState: AutofillState = 'idle';
let detectedFields: FormField[] = [];
let currentPlatform: Platform = 'unknown';
let extracting = false; // Lock to prevent parallel extractions

function log(...args: any[]) { console.log('[CB]', ...args); }

// ── Detect platform ─────────────────────────────────────────────────────────
function detectPlatform(url: string): Platform {
  if (isGreenhousePage(url)) return 'greenhouse';
  if (isWorkdayPage(url)) return 'workday';
  if (isLeverPage(url)) return 'lever';
  if (isAshbyPage(url)) return 'ashby';
  if (isSmartRecruitersPage(url)) return 'smartrecruiters';
  return 'generic';
}

// ── Extract fields based on platform ────────────────────────────────────────
function extractForPlatform(doc: Document, platform: Platform): FormField[] {
  switch (platform) {
    case 'greenhouse': return extractGreenhouseFields(doc);
    case 'workday': return extractWorkdayFields(doc);
    case 'lever': return extractLeverFields(doc);
    case 'ashby': return extractAshbyFields(doc);
    case 'smartrecruiters': return extractSmartRecruitersFields(doc);
    default: return extractGenericFields(doc);
  }
}

// ── Fill field based on platform ────────────────────────────────────────────
function fillForPlatform(fieldId: string, value: string, platform: Platform): boolean {
  switch (platform) {
    case 'greenhouse': return _fillGH(fieldId, value);
    case 'workday': return _fillWD(fieldId, value);
    case 'lever': return _fillLever(fieldId, value);
    case 'ashby': return _fillAshby(fieldId, value);
    case 'smartrecruiters': return _fillSR(fieldId, value);
    default: return fillGenericField(fieldId, value);
  }
}

// ── Extract job info based on platform ──────────────────────────────────────
function getJobInfo(doc: Document, platform: Platform, url: string): { jobTitle: string; company: string } {
  switch (platform) {
    case 'greenhouse': return { jobTitle: _ghTitle(doc), company: _ghCompany(doc, url) };
    case 'workday': return extractWorkdayJobInfo(doc);
    case 'lever': return extractLeverJobInfo(doc);
    case 'ashby': return extractAshbyJobInfo(doc);
    case 'smartrecruiters': return extractSmartRecruitersJobInfo(doc);
    default: return { jobTitle: doc.querySelector('h1')?.textContent?.trim() || '', company: '' };
  }
}

// ── Build mapping from profile based on platform ────────────────────────────
export function buildMappingForPlatform(profile: any, platform: Platform): Record<string, string> {
  switch (platform) {
    case 'greenhouse': {
      const m: Record<string, string> = {};
      if (profile.personal?.firstName) m.first_name = profile.personal.firstName;
      if (profile.personal?.lastName) m.last_name = profile.personal.lastName;
      if (profile.personal?.email) m.email = profile.personal.email;
      if (profile.personal?.phone) m.phone = profile.personal.phone;
      if (profile.personal?.address?.country) m.country = profile.personal.address.country;
      if (profile.personal?.address?.city) m['candidate-location'] = profile.personal.address.city;
      if (profile.professional?.currentCompany) m['company-name-0'] = profile.professional.currentCompany;
      if (profile.professional?.currentTitle) m['title-0'] = profile.professional.currentTitle;
      if (profile.professional?.linkedin) m.question_68978657 = profile.professional.linkedin;
      return m;
    }
    case 'workday': {
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
      return m;
    }
    case 'lever': {
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
    case 'ashby': {
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
    case 'smartrecruiters': {
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
    default:
      return {};
  }
}

// ── Generic field extraction (fallback) ─────────────────────────────────────
function extractGenericFields(doc: Document): FormField[] {
  const fields: FormField[] = [];

  const form = doc.querySelector('form');
  if (!form) return fields;

  const inputs = form.querySelectorAll('input, textarea, select');
  inputs.forEach((el) => {
    const type = (el as HTMLInputElement).type || 'text';
    if (['file', 'hidden', 'submit', 'button', 'image', 'password'].includes(type)) return;

    const id = el.id || '';
    const name = el.getAttribute('name') || id;
    const label = el.getAttribute('aria-label') ||
                  el.getAttribute('placeholder') ||
                  (id ? doc.querySelector(`label[for="${CSS.escape(id)}"]`)?.textContent?.trim() : '') ||
                  name;

    if (!label && !name) return;

    const selector = id ? `#${CSS.escape(id)}` : `[name="${CSS.escape(name)}"]`;

    fields.push({
      id: `gen_${name}`,
      elementType: el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'SELECT' ? 'select' : 'input',
      inputType: type,
      label: label.replace(/\*/g, '').trim(),
      name,
      selector,
      required: (el as HTMLInputElement).required || (el as HTMLInputElement).getAttribute('aria-required') === 'true',
      currentValue: (el as HTMLInputElement).value || '',
      index: fields.length,
    });
  });

  return fields;
}

// ── Fill generic field (fallback) ───────────────────────────────────────────
function fillGenericField(fieldId: string, value: string): boolean {
  const rawId = fieldId.startsWith('gen_') ? fieldId.slice(4) : fieldId;

  let el = document.getElementById(rawId) as HTMLInputElement;
  if (!el) el = document.querySelector(`[name="${CSS.escape(rawId)}"]`) as HTMLInputElement;
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

// ── Check for application form (any platform) ───────────────────────────────
function hasApplicationForm(): boolean {
  const formEl = document.querySelector('form');
  if (!formEl) return false;
  const hasEmail = formEl.querySelector('input[type="email"], input#email, input[name="email"]');
  const hasFileUpload = formEl.querySelector('input[type="file"]');
  const hasPhone = formEl.querySelector('input[type="tel"], input#phone, input[name="phone"]');
  const text = formEl.textContent?.toLowerCase() || '';
  const hasResume = text.includes('resume') || text.includes('cv');
  return !!(hasEmail || hasFileUpload || hasPhone || hasResume);
}

// ── Message handler ─────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener(
  (msg: any, _sender, sendResponse: (response: any) => void) => {
    log('Received:', msg.type);

    switch (msg.type) {
      case 'PING':
        sendResponse({ alive: true });
        return false;

      case 'DETECT_APPLICATION':
        handleDetect().then(sendResponse).catch(e => { log('DETECT error:', e); sendResponse({ isApplication: false }); });
        return true;

      case 'EXTRACT_FIELDS':
        handleExtract().then(sendResponse).catch(e => { log('EXTRACT error:', e); sendResponse({ fields: [], allFields: [], isGreenhouse: false }); });
        return true;

      case 'WAIT_AND_EXTRACT':
        if (extracting) {
          // Already extracting — return cached result
          const fillable = detectedFields.filter(f =>
            f.inputType !== 'file' && f.inputType !== 'hidden' && f.inputType !== 'submit'
          );
          sendResponse({ fields: fillable, allFields: detectedFields, platform: currentPlatform });
        } else {
          waitForForm(msg.timeout || 6000).then(() => handleExtract()).then(sendResponse).catch(e => { log('WAIT+EXTRACT error:', e); sendResponse({ fields: [], allFields: [], platform: currentPlatform }); });
        }
        return true;

      case 'FILL_GREENHOUSE':
        handleFill(msg.mapping, msg.platform || 'greenhouse').then(sendResponse).catch(e => { log('FILL error:', e); sendResponse({ results: [] }); });
        return true;

      case 'FILL_PLATFORM':
        handleFill(msg.mapping, msg.platform).then(sendResponse).catch(e => { log('FILL error:', e); sendResponse({ results: [] }); });
        return true;

      case 'FILL_FIELDS':
        handleFillGeneric(msg.fields).then(sendResponse).catch(e => { log('FILL error:', e); sendResponse({ results: [] }); });
        return true;

      case 'GET_STATE':
        sendResponse({ state: currentState, fields: detectedFields, platform: currentPlatform });
        return false;

      default:
        sendResponse({ error: 'Unknown: ' + msg.type });
        return false;
    }
  }
);

// ── Detect ──────────────────────────────────────────────────────────────────
async function handleDetect() {
  const url = window.location.href;
  currentPlatform = detectPlatform(url);
  const isApp = currentPlatform !== 'generic' || hasApplicationForm();
  const { jobTitle, company } = getJobInfo(document, currentPlatform, url);

  if (isApp) setState('application_detected');

  log('Detection:', { platform: currentPlatform, isApp, jobTitle, company });

  return {
    isApplication: isApp,
    confidence: currentPlatform !== 'generic' ? 0.95 : 0.5,
    platform: currentPlatform,
    jobTitle,
    company,
  };
}

// ── Extract ─────────────────────────────────────────────────────────────────
async function handleExtract() {
  if (extracting) {
    log('Already extracting, returning cached result');
    const fillable = detectedFields.filter(f =>
      f.inputType !== 'file' && f.inputType !== 'hidden' && f.inputType !== 'submit'
    );
    return { fields: fillable, allFields: detectedFields, platform: currentPlatform };
  }
  extracting = true;
  try {
    setState('analyzing');
    detectedFields = extractForPlatform(document, currentPlatform);

    log('Extracted', detectedFields.length, 'fields for platform:', currentPlatform);

    const fillable = detectedFields.filter(f =>
      f.inputType !== 'file' && f.inputType !== 'hidden' && f.inputType !== 'submit'
    );

    setState('ready');
    return { fields: fillable, allFields: detectedFields, platform: currentPlatform };
  } finally {
    extracting = false;
  }
}

// ── Wait for form to appear (used by background before extract) ──────────────
async function waitForForm(timeoutMs = 6000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const fields = extractForPlatform(document, currentPlatform);
    const fillable = fields.filter(f =>
      f.inputType !== 'file' && f.inputType !== 'hidden' && f.inputType !== 'submit'
    );
    if (fillable.length > 0) {
      log('Form appeared after', Date.now() - start, 'ms with', fillable.length, 'fields');
      detectedFields = fields;
      return true;
    }
    await new Promise(r => setTimeout(r, 500));
  }
  log('Timeout waiting for form after', timeoutMs, 'ms');
  return false;
}

// ── Fill ────────────────────────────────────────────────────────────────────
async function handleFill(mapping: Record<string, string>, platform?: string) {
  setState('filling');
  const p = (platform as Platform) || currentPlatform;
  log('Filling for platform:', p, mapping);

  const results: { fieldId: string; success: boolean; label?: string }[] = [];

  for (const [fieldId, value] of Object.entries(mapping)) {
    const success = fillForPlatform(fieldId, value, p);
    const field = detectedFields.find(f => f.id === fieldId);
    log('Fill:', fieldId, success ? 'OK' : 'FAIL');
    results.push({ fieldId, success, label: field?.label || fieldId });
  }

  setState('completed');
  return { results };
}

// ── Fill generic ────────────────────────────────────────────────────────────
async function handleFillGeneric(fieldsToFill: { selector: string; value: string; fieldId?: string }[]) {
  setState('filling');
  const results: { fieldId: string; success: boolean }[] = [];

  for (const item of fieldsToFill) {
    const el = document.querySelector(item.selector) as HTMLInputElement;
    if (!el) { results.push({ fieldId: item.fieldId || item.selector, success: false }); continue; }
    const success = fillGenericField(item.fieldId || item.selector, item.value);
    results.push({ fieldId: item.fieldId || item.selector, success });
  }

  setState('completed');
  return { results };
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function setState(state: AutofillState) {
  currentState = state;
  try { chrome.runtime.sendMessage({ type: 'STATE_UPDATE', state }); } catch {}
}

function sleep(ms: number) { return new Promise(r => setTimeout(r, ms)); }

// ── Auto-detect on page load ────────────────────────────────────────────────
function autoDetect() {
  log('Auto-detecting on:', window.location.href);
  currentPlatform = detectPlatform(window.location.href);

  if (currentPlatform !== 'generic' || hasApplicationForm()) {
    setState('application_detected');
    try {
      chrome.runtime.sendMessage({
        type: 'FORM_DETECTED',
        platform: currentPlatform,
        jobTitle: getJobInfo(document, currentPlatform, window.location.href).jobTitle,
        company: getJobInfo(document, currentPlatform, window.location.href).company,
        url: window.location.href,
      });
    } catch {}
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => setTimeout(autoDetect, 500));
} else {
  setTimeout(autoDetect, 500);
}

let lastUrl = location.href;
new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    detectedFields = [];
    setState('idle');
    setTimeout(autoDetect, 1000);
  }
}).observe(document.body || document.documentElement, { childList: true, subtree: true });

log('Content script loaded:', window.location.href);
