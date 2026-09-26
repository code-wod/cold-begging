import type { ApplicationProfile, FieldSuggestion, AutofillState, Platform, FormField } from '../types';
import { storage } from '../storage/store';
import { api } from '../api/client';
import { matchFields } from '../matcher/matcher';

let currentTabId: number | null = null;
let currentState: AutofillState = 'idle';
let detectedFields: FormField[] = [];
let suggestions: FieldSuggestion[] = [];
let profile: ApplicationProfile | null = null;

function log(...args: any[]) { console.log('[CB BG]', ...args); }

// ── Initialize ──────────────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(async () => {
  log('Extension installed');
});

chrome.runtime.onStartup.addListener(async () => {
  await api.init();
  await syncProfileFromBackend();
});

async function syncProfileFromBackend() {
  if (!api.isAuthenticated()) return;
  try {
    const p = await api.getProfile();
    if (p) {
      // Merge: backend is source of truth, but don't overwrite local non-empty fields with empty
      profile = {
        personal: { ...(p.personal || {}), ...filterEmpty((profile?.personal || {}), (p.personal || {})) },
        professional: { ...(p.professional || {}), ...filterEmpty((profile?.professional || {}), (p.professional || {})) },
        education: p.education?.length ? p.education : profile?.education || [],
        workAuthorization: { ...(p.workAuthorization || {}), ...filterEmpty((profile?.workAuthorization || {}), (p.workAuthorization || {})) },
        preferences: { ...(p.preferences || {}), ...filterEmpty((profile?.preferences || {}), (p.preferences || {})) },
        documents: { ...(p.documents || {}), ...filterEmpty((profile?.documents || {}), (p.documents || {})) },
        customAnswers: { ...(p.customAnswers || {}), ...(profile?.customAnswers || {}) },
      } as ApplicationProfile;
      await storage.setProfile(profile);
      await chrome.storage.local.set({ profile });
      log('Profile synced from backend');
    }
  } catch (e) {
    log('Failed to sync profile:', e);
  }
}

// Merge helper: prefer backend values, but keep local non-empty values if backend is empty
function filterEmpty(local: Record<string, any>, backend: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {};
  for (const key of Object.keys(local)) {
    if (local[key] && !backend[key]) {
      result[key] = local[key];
    }
  }
  return result;
}

// ── Message handler ─────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg: any, sender, sendResponse: (r: any) => void) => {
  log('Message:', msg.type, sender.tab ? 'from tab ' + sender.tab.id : 'from panel');

  if (sender.tab) {
    handleContentMsg(msg, sender.tab).then(sendResponse).catch(e => { log('Error:', e); sendResponse({}); });
    return true;
  }
  handleSidePanelMsg(msg).then(sendResponse).catch(e => { log('Error:', e); sendResponse({ error: e.message }); });
  return true;
});

// ── Content script messages ─────────────────────────────────────────────────
async function handleContentMsg(msg: any, tab: chrome.tabs.Tab): Promise<any> {
  switch (msg.type) {
    case 'STATE_UPDATE':
      currentState = msg.state;
      // Forward to side panel
      try { chrome.runtime.sendMessage({ type: 'CONTENT_STATE_UPDATE', state: msg.state }); } catch {}
      return {};

    case 'FORM_DETECTED':
      log('Form detected on tab:', tab.id, msg.platform);
      currentTabId = tab.id || null;

      // Auto-open side panel
      if (tab.id) {
        try {
          await chrome.sidePanel.open({ tabId: tab.id });
          log('Side panel opened');
        } catch (e) {
          log('Could not open side panel:', e);
        }
      }

      // Forward detection to side panel
      try {
        chrome.runtime.sendMessage({
          type: 'DETECTION_RESULT',
          platform: msg.platform,
          jobTitle: msg.jobTitle,
          company: msg.company,
          url: msg.url,
        });
      } catch {}

      return {};

    default:
      return {};
  }
}

// ── Side panel messages ─────────────────────────────────────────────────────
async function handleSidePanelMsg(msg: any): Promise<any> {
  switch (msg.type) {
    case 'INIT': {
      profile = profile || await storage.getProfile();
      if (profile) {
        await storage.setProfile(profile);
        await chrome.storage.local.set({ profile });
      }
      return { success: true, profile };
    }

    case 'LOGIN': {
      try {
        const result = await api.login(msg.email, msg.password);
        await syncProfileFromBackend();
        return { success: true, profile };
      } catch (e: any) {
        return { success: false, error: e.message };
      }
    }

    case 'DETECT': {
      const result = await detectTab();
      return result;
    }

    case 'EXTRACT': {
      const result = await extractTab();
      return result;
    }

    case 'ANALYZE': {
      profile = profile || await storage.getProfile();
      suggestions = await matchFields(detectedFields, profile);
      return { suggestions };
    }

    case 'FILL': {
      return await fillTab(msg.suggestions || suggestions);
    }

    case 'FILL_GREENHOUSE': {
      return await fillGreenhouseTab(msg.mapping);
    }

    case 'UPDATE_SUGGESTION': {
      const i = suggestions.findIndex(s => s.fieldId === msg.fieldId);
      if (i >= 0) suggestions[i] = { ...suggestions[i], value: msg.value, requiresReview: false };
      return {};
    }

    case 'REJECT_SUGGESTION': {
      const i = suggestions.findIndex(s => s.fieldId === msg.fieldId);
      if (i >= 0) suggestions[i] = { ...suggestions[i], value: undefined, requiresReview: false };
      return {};
    }

    case 'GET_PROFILE': {
      // Always try backend first if authenticated
      if (api.isAuthenticated()) {
        await syncProfileFromBackend();
      }
      if (!profile) {
        profile = await storage.getProfile();
      }
      return { profile };
    }

    case 'UPDATE_PROFILE': {
      profile = msg.profile;
      if (profile) await storage.setProfile(profile);
      await chrome.storage.local.set({ profile });
      if (api.isAuthenticated()) {
        try { await api.updateProfile(msg.profile); } catch {}
      }
      return { profile };
    }

    case 'GET_STATE': {
      return { state: currentState, fields: detectedFields, suggestions, profile };
    }

    case 'SAVE_ANSWER': {
      await storage.saveLearnedAnswer({
        question: msg.question,
        normalizedQuestion: msg.question.toLowerCase().replace(/[:*?]+$/, '').trim(),
        answer: msg.answer,
        answerType: 'text',
        scope: msg.scope || 'global',
        source: 'user',
        confidence: 1,
        userConfirmed: true,
      });
      return {};
    }

    case 'SAVE_SESSION': {
      await saveSession(msg.data);
      return {};
    }

    default:
      return { error: 'Unknown: ' + msg.type };
  }
}

// ── Ensure content script is injected ───────────────────────────────────────
async function ensureContentScript(tabId: number): Promise<boolean> {
  try {
    await chrome.tabs.sendMessage(tabId, { type: 'PING' });
    return true;
  } catch {
    // Inject content script
    try {
      await chrome.scripting.executeScript({
        target: { tabId },
        files: ['content/content-script.js'],
      });
      // Wait for script to initialize
      await new Promise(r => setTimeout(r, 500));
      // Verify
      try {
        await chrome.tabs.sendMessage(tabId, { type: 'PING' });
        return true;
      } catch {
        return false;
      }
    } catch (e) {
      log('Failed to inject content script:', e);
      return false;
    }
  }
}

// ── Detect tab ──────────────────────────────────────────────────────────────
async function detectTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return { isApplication: false, platform: 'unknown', jobTitle: '', company: '' };

  currentTabId = tab.id;

  const injected = await ensureContentScript(tab.id);
  if (!injected) {
    log('Content script not injected');
    return { isApplication: false, platform: 'unknown', jobTitle: '', company: '' };
  }

  try {
    const result = await chrome.tabs.sendMessage(tab.id, { type: 'DETECT_APPLICATION' });
    log('Detect result:', result);
    return result;
  } catch (e) {
    log('Detect failed:', e);
    return { isApplication: false, platform: 'unknown', jobTitle: '', company: '' };
  }
}

// ── Extract tab ─────────────────────────────────────────────────────────────
async function extractTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return { fields: [], allFields: [], platform: 'unknown' };

  currentTabId = tab.id;

  const injected = await ensureContentScript(tab.id);
  if (!injected) {
    log('Content script not injected for extract');
    return { fields: [], allFields: [], platform: 'unknown' };
  }

  try {
    // Use WAIT_AND_EXTRACT which waits for React SPA to render form fields
    const res = await chrome.tabs.sendMessage(tab.id, { type: 'WAIT_AND_EXTRACT', timeout: 6000 });
    log('Extract result:', res?.fields?.length, 'fields for', res?.platform);
    detectedFields = res.allFields || res.fields || [];
    return res;
  } catch (e) {
    log('Extract failed:', e);
    return { fields: [], allFields: [], platform: 'unknown' };
  }
}

// ── Fill tab (generic) ──────────────────────────────────────────────────────
async function fillTab(sugs: FieldSuggestion[]) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return { results: [] };

  currentState = 'filling';

  const fieldsToFill = sugs
    .filter(s => s.value)
    .map(s => {
      const field = detectedFields.find(f => f.id === s.fieldId);
      return { selector: field?.selector || '', value: s.value!, fieldId: s.fieldId };
    })
    .filter(f => f.value);

  try {
    const res = await chrome.tabs.sendMessage(tab.id, { type: 'FILL_FIELDS', fields: fieldsToFill });
    currentState = 'completed';
    const successCount = (res.results || []).filter((r: any) => r.success).length;
    await saveSession({ url: tab.url || '', platform: 'generic', fieldsDetected: detectedFields.length, fieldsFilled: successCount });
    return res;
  } catch (e) {
    log('Fill failed:', e);
    currentState = 'error';
    return { results: [] };
  }
}

// ── Fill Greenhouse ─────────────────────────────────────────────────────────
async function fillGreenhouseTab(mapping: Record<string, string>) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return { results: [] };

  currentState = 'filling';
  log('Filling Greenhouse on tab:', tab.id, mapping);

  try {
    const res = await chrome.tabs.sendMessage(tab.id, { type: 'FILL_GREENHOUSE', mapping });
    log('Fill result:', res);
    currentState = 'completed';
    const successCount = (res.results || []).filter((r: any) => r.success).length;
    await saveSession({
      url: tab.url || '',
      company: extractCompanyFromUrl(tab.url || ''),
      platform: 'greenhouse',
      fieldsDetected: Object.keys(mapping).length,
      fieldsFilled: successCount,
    });
    return res;
  } catch (e) {
    log('Fill greenhouse failed:', e);
    currentState = 'error';
    return { results: [] };
  }
}

// ── Save session ────────────────────────────────────────────────────────────
async function saveSession(data: any) {
  const session = { id: crypto.randomUUID(), timestamp: new Date().toISOString(), ...data };
  await storage.saveSession(session);
  if (api.isAuthenticated()) {
    try {
      await api.saveSession({
        url: data.url,
        company: data.company,
        platform: data.platform,
        fields_detected: data.fieldsDetected,
        fields_filled: data.fieldsFilled,
        duration_seconds: 0,
      });
    } catch {}
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function extractCompanyFromUrl(url: string): string {
  try {
    const params = new URL(url).searchParams;
    return params.get('for') || new URL(url).hostname.split('.')[0];
  } catch { return ''; }
}

// ── Context menu ────────────────────────────────────────────────────────────
chrome.contextMenus?.create({
  id: 'cb-fill',
  title: 'Cold-Begging: Fill this form',
  contexts: ['page', 'editable'],
  documentUrlPatterns: ['<all_urls>'],
});

chrome.contextMenus?.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'cb-fill' && tab?.id) {
    chrome.sidePanel?.open({ tabId: tab.id });
  }
});

// ── Tab update ──────────────────────────────────────────────────────────────
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === 'complete' && tabId === currentTabId) {
    currentState = 'idle';
    detectedFields = [];
    suggestions = [];
  }
});

log('Background loaded');
