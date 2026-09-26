import React, { useState, useEffect } from 'react';
import type { ApplicationProfile, FormField, FieldSuggestion, AutofillState, Platform } from '../types';
import { api } from '../api/client';
import { ProfilePanel } from './components/ProfilePanel';

function App() {
  const [tab, setTab] = useState<'fill' | 'profile' | 'history'>('fill');
  const [state, setState] = useState<AutofillState>('idle');
  const [platform, setPlatform] = useState<Platform>('unknown');
  const [fields, setFields] = useState<FormField[]>([]);
  const [suggestions, setSuggestions] = useState<FieldSuggestion[]>([]);
  const [profile, setProfile] = useState<ApplicationProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [ghMapping, setGhMapping] = useState<Record<string, string>>({});
  const [fillResults, setFillResults] = useState<{ fieldId: string; success: boolean; label?: string }[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [statusText, setStatusText] = useState('');

  const [isAuth, setIsAuth] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  useEffect(() => { init(); }, []);

  async function init() {
    // Load profile from storage first (instant)
    try {
      const stored = await chrome.storage.local.get('profile');
      if (stored.profile) {
        setProfile(stored.profile);
        console.log('[CB Panel] Loaded profile from storage:', stored.profile.personal?.firstName || '(no name)');
      }
    } catch {}

    // Auth
    const authStored = await chrome.storage.local.get('auth_token');
    if (authStored.auth_token) {
      api.setToken(authStored.auth_token);
      setIsAuth(true);
      try { await api.getMe(); } catch { setIsAuth(false); api.clearToken(); }
    }

    // Load profile from backend (always, to stay in sync)
    try {
      const r = await bg({ type: 'GET_PROFILE' });
      if (r?.profile) {
        setProfile(r.profile);
        await chrome.storage.local.set({ profile: r.profile });
        console.log('[CB Panel] Profile from backend:', r.profile.personal?.firstName, r.profile.professional?.currentCompany || '(no company)');
      }
    } catch (e) {
      console.warn('[CB Panel] Failed to load profile:', e);
    }

    // Detect — always set state regardless of result
    try {
      const d = await bg({ type: 'DETECT' });
      console.log('[CB Panel] Detect result:', d);
      if (d?.isApplication) {
        setState('application_detected');
        setPlatform(d.platform || 'unknown');
        setJobTitle(d.jobTitle || '');
        setCompany(d.company || '');
        setStatusText(`${d.platform || 'Unknown'} application detected`);
      } else {
        // Not detected — still let user scan manually
        setStatusText('');
      }
    } catch (e) {
      console.warn('[CB Panel] Detect failed:', e);
    }

    // Sessions
    try {
      const s = await chrome.storage.local.get('sessions');
      setSessions(s.sessions || []);
    } catch {}
  }

  async function bg(msg: any): Promise<any> {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(msg, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[CB Panel] Message error:', chrome.runtime.lastError.message);
          reject(chrome.runtime.lastError);
        } else {
          resolve(response);
        }
      });
    });
  }

  useEffect(() => {
    const listener = (msg: any) => {
      if (msg.type === 'DETECTION_RESULT') {
        setState('application_detected');
        setPlatform(msg.platform);
        setJobTitle(msg.jobTitle || '');
        setCompany(msg.company || '');
      }
    };
    chrome.runtime.onMessage.addListener(listener);
    return () => chrome.runtime.onMessage.removeListener(listener);
  }, []);

  async function handleLogin() {
    setLoading(true);
    setError(null);
    try {
      const r = await bg({ type: 'LOGIN', email: loginEmail, password: loginPassword });
      if (r?.success) {
        setIsAuth(true);
        if (r.profile?.personal?.firstName) {
          setProfile(r.profile);
          await chrome.storage.local.set({ profile: r.profile });
        }
      } else {
        setError(r?.error || 'Login failed');
      }
    } catch (e: any) { setError(e.message || 'Login failed'); }
    setLoading(false);
  }

  // ── Build mapping based on platform ───────────────────────────────────────
  function buildMapping(p: ApplicationProfile | null, plat: Platform): Record<string, string> {
    if (!p) return {};

    switch (plat) {
      case 'greenhouse': {
        const m: Record<string, string> = {};
        if (p.personal?.firstName) m.first_name = p.personal.firstName;
        if (p.personal?.lastName) m.last_name = p.personal.lastName;
        if (p.personal?.email) m.email = p.personal.email;
        if (p.personal?.phone) m.phone = p.personal.phone;
        if (p.personal?.address?.country) m.country = p.personal.address.country;
        if (p.personal?.address?.city) m['candidate-location'] = p.personal.address.city;
        if (p.professional?.currentCompany) m['company-name-0'] = p.professional.currentCompany;
        if (p.professional?.currentTitle) m['title-0'] = p.professional.currentTitle;
        if (p.professional?.linkedin) m.question_68978657 = p.professional.linkedin;
        return m;
      }
      case 'workday': {
        const m: Record<string, string> = {};
        if (p.personal?.firstName) m['firstLegalName\\$input'] = p.personal.firstName;
        if (p.personal?.lastName) m['lastName\\$input'] = p.personal.lastName;
        if (p.personal?.email) m['email\\$input'] = p.personal.email;
        if (p.personal?.phone) m['phone\\$input'] = p.personal.phone;
        if (p.personal?.address?.street) m['addressLine1\\$input'] = p.personal.address.street;
        if (p.personal?.address?.city) m['city\\$input'] = p.personal.address.city;
        if (p.personal?.address?.state) m['state\\$input'] = p.personal.address.state;
        if (p.personal?.address?.country) m['country\\$input'] = p.personal.address.country;
        if (p.personal?.address?.postalCode) m['postalCode\\$input'] = p.personal.address.postalCode;
        if (p.professional?.currentCompany) m['companyName\\$input'] = p.professional.currentCompany;
        if (p.professional?.currentTitle) m['title\\$input'] = p.professional.currentTitle;
        if (p.professional?.linkedin) m['linkedin\\$input'] = p.professional.linkedin;
        return m;
      }
      case 'lever': {
        const m: Record<string, string> = {};
        if (p.personal?.firstName && p.personal?.lastName) m['name'] = `${p.personal.firstName} ${p.personal.lastName}`;
        if (p.personal?.email) m['email'] = p.personal.email;
        if (p.personal?.phone) m['phone'] = p.personal.phone;
        if (p.professional?.currentCompany) m['org'] = p.professional.currentCompany;
        if (p.professional?.linkedin) m['urls[LinkedIn]'] = p.professional.linkedin;
        if (p.professional?.github) m['urls[GitHub]'] = p.professional.github;
        if (p.professional?.portfolio) m['urls[Portfolio]'] = p.professional.portfolio;
        if (p.personal?.address?.city) m['location'] = p.personal.address.city;
        return m;
      }
      case 'ashby': {
        const m: Record<string, string> = {};
        if (p.personal?.firstName) m['firstName'] = p.personal.firstName;
        if (p.personal?.lastName) m['lastName'] = p.personal.lastName;
        if (p.personal?.email) m['email'] = p.personal.email;
        if (p.personal?.phone) m['phone'] = p.personal.phone;
        if (p.personal?.address?.city) m['location'] = p.personal.address.city;
        if (p.professional?.currentCompany) m['company'] = p.professional.currentCompany;
        if (p.professional?.currentTitle) m['title'] = p.professional.currentTitle;
        if (p.professional?.linkedin) m['linkedin'] = p.professional.linkedin;
        return m;
      }
      case 'smartrecruiters': {
        const m: Record<string, string> = {};
        if (p.personal?.firstName) m['firstName'] = p.personal.firstName;
        if (p.personal?.lastName) m['lastName'] = p.personal.lastName;
        if (p.personal?.email) m['email'] = p.personal.email;
        if (p.personal?.phone) m['phone'] = p.personal.phone;
        if (p.personal?.address?.city) m['location'] = p.personal.address.city;
        if (p.professional?.currentCompany) m['company'] = p.professional.currentCompany;
        if (p.professional?.currentTitle) m['title'] = p.professional.currentTitle;
        if (p.professional?.linkedin) m['linkedin'] = p.professional.linkedin;
        return m;
      }
      default: return {};
    }
  }

  function getPlatformName(p: Platform): string {
    const names: Record<string, string> = {
      greenhouse: 'Greenhouse', workday: 'Workday', lever: 'Lever',
      ashby: 'Ashby', smartrecruiters: 'SmartRecruiters', generic: 'Generic', unknown: 'Unknown',
    };
    return names[p] || p;
  }

  // ── Extract + Fill ──────────────────────────────────────────────────────
  async function handleExtractAndFill() {
    setLoading(true);
    setError(null);
    setStatusText('Waiting for form to load...');

    try {
      const res = await bg({ type: 'EXTRACT' });
      console.log('[CB Panel] Extract result:', res);

      if (res?.fields?.length > 0) {
        // Force-set detected state from extraction result
        setState('application_detected');
        setPlatform(res.platform);
        setFields(res.fields);

        // Ensure we have a profile
        let currentProfile = profile;
        if (!currentProfile || !currentProfile.personal?.firstName) {
          try {
            const stored = await chrome.storage.local.get('profile');
            currentProfile = stored.profile || null;
            if (currentProfile?.personal?.firstName) setProfile(currentProfile);
          } catch {}
        }

        if (!currentProfile || !currentProfile.personal?.firstName) {
          setStatusText('No profile found. Go to Profile tab.');
          setTab('profile');
          setLoading(false);
          return;
        }

        const mapping = buildMapping(currentProfile, res.platform);
        const mappedCount = Object.keys(mapping).length;
        console.log('[CB Panel] Mapping:', res.platform, mapping);
        setGhMapping(mapping);

        if (mappedCount === 0) {
          setStatusText(`No matching fields for ${getPlatformName(res.platform)} profile mapping`);
          setLoading(false);
          return;
        }

        setStatusText(`Filling ${mappedCount} fields on ${getPlatformName(res.platform)}...`);

        const fillRes = await bg({ type: 'FILL_PLATFORM', mapping, platform: res.platform });
        console.log('[CB Panel] Fill result:', fillRes);

        if (fillRes?.results) {
          setFillResults(fillRes.results);
          setState('completed');
          const successCount = fillRes.results.filter((r: any) => r.success).length;
          setStatusText(`Filled ${successCount} of ${fillRes.results.length} fields`);

          // Save session
          try {
            const newSession = {
              url: window.location.href,
              company: company || new URL(window.location.href).hostname,
              platform: res.platform,
              jobTitle: jobTitle || '',
              fieldsDetected: res.fields.length,
              fieldsFilled: successCount,
              timestamp: new Date().toISOString(),
            };
            const s = await chrome.storage.local.get('sessions');
            const sess = s.sessions || [];
            sess.unshift(newSession);
            if (sess.length > 50) sess.length = 50;
            await chrome.storage.local.set({ sessions: sess });
            setSessions(sess);

            // Save to backend
            try {
              await api.saveSession({
                url: newSession.url,
                company: newSession.company,
                platform: newSession.platform,
                job_title: newSession.jobTitle,
                fields_detected: newSession.fieldsDetected,
                fields_filled: newSession.fieldsFilled,
              });
            } catch {}
          } catch {}
        } else {
          setStatusText('Fill failed');
          setState('error');
        }
      } else {
        setStatusText('No form fields detected. Page may still be loading.');
        setError('No form fields found — try clicking Fill again in a few seconds');
      }
    } catch (e: any) {
      console.error('[CB Panel] Error:', e);
      setError(e.message || 'Failed');
      setStatusText('Error: ' + (e.message || 'Unknown'));
    }
    setLoading(false);
  }

  async function handleRefill() {
    if (Object.keys(ghMapping).length === 0) { setError('No mapping to retry'); return; }
    setLoading(true);
    setError(null);
    setStatusText('Retrying fill...');
    try {
      const fillRes = await bg({ type: 'FILL_PLATFORM', mapping: ghMapping, platform });
      if (fillRes?.results) {
        setFillResults(fillRes.results);
        setState('completed');
        const successCount = fillRes.results.filter((r: any) => r.success).length;
        setStatusText(`Filled ${successCount} of ${fillRes.results.length} fields`);
      }
    } catch (e: any) { setError(e.message || 'Retry failed'); }
    setLoading(false);
  }

  // ── Login screen ────────────────────────────────────────────────────────
  if (!isAuth) {
    return (
      <div style={s.container}>
        <div style={s.header}>
          <h1 style={s.title}>Cold-Begging</h1>
          <p style={s.sub}>Sign in to use your profile</p>
        </div>
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input type="email" placeholder="Email" value={loginEmail}
            onChange={e => setLoginEmail(e.target.value)} style={s.input} />
          <input type="password" placeholder="Password" value={loginPassword}
            onChange={e => setLoginPassword(e.target.value)} style={s.input} />
          <button onClick={handleLogin} disabled={loading || !loginEmail || !loginPassword}
            style={s.primaryBtn}>{loading ? 'Signing in...' : 'Sign In'}</button>
          {error && <p style={{ color: '#dc3545', fontSize: 12, textAlign: 'center' }}>{error}</p>}
        </div>
      </div>
    );
  }

  // ── Main UI ─────────────────────────────────────────────────────────────
  const fieldCount = profile ? Object.keys(buildMapping(profile, platform)).length : 0;

  return (
    <div style={s.container}>
      <div style={s.header}>
        <h1 style={s.title}>Cold-Begging</h1>
        {jobTitle && <div style={{ fontSize: 13, opacity: 0.9, marginTop: 4 }}>{jobTitle}</div>}
        {company && <div style={{ fontSize: 12, opacity: 0.6 }}>{company}</div>}
        {statusText && (
          <div style={{ fontSize: 11, opacity: 0.7, marginTop: 6, padding: '4px 8px', background: 'rgba(255,255,255,0.1)', borderRadius: 4 }}>
            {statusText}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #e0e0e0', background: 'white' }}>
        {(['fill', 'profile', 'history'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={tab === t ? { ...s.tab, borderBottom: '2px solid #ff9900', fontWeight: 600 } : s.tab}>
            {t === 'fill' ? 'Fill' : t === 'profile' ? 'Profile' : 'History'}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {/* FILL TAB */}
        {tab === 'fill' && (
          <div>
            {(state === 'idle' || state === 'login_required' || state === 'captcha_required') && (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                <p style={{ fontSize: 32, margin: '0 0 8px' }}>🔍</p>
                <p style={{ fontSize: 13 }}>Click below to detect and fill the form</p>
                <p style={{ fontSize: 11, color: '#bbb', margin: '4px 0 0' }}>Greenhouse · Workday · Lever · Ashby · SmartRecruiters</p>
                <button onClick={handleExtractAndFill} disabled={loading}
                  style={{ ...s.primaryBtn, marginTop: 16, fontSize: 16, padding: '14px 24px' }}>
                  {loading ? 'Scanning...' : '⚡ Scan & Fill'}
                </button>
              </div>
            )}

            {state === 'application_detected' && (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                  {getPlatformName(platform)} Application Detected
                </p>
                {profile?.personal?.firstName ? (
                  <button onClick={handleExtractAndFill} disabled={loading}
                    style={{ ...s.primaryBtn, fontSize: 16, padding: '14px 24px' }}>
                    {loading ? 'Scanning...' : `⚡ Fill ${fieldCount} Fields`}
                  </button>
                ) : (
                  <div>
                    <p style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>No profile loaded.</p>
                    <button onClick={() => setTab('profile')} style={s.secondaryBtn}>Set Up Profile</button>
                  </div>
                )}
              </div>
            )}

            {state === 'analyzing' && (
              <div style={{ textAlign: 'center', padding: 40, color: '#666' }}>
                <p>Scanning {getPlatformName(platform)} form fields...</p>
              </div>
            )}

            {state === 'filling' && (
              <div style={{ textAlign: 'center', padding: 40, color: '#666' }}>
                <p>Filling fields on {getPlatformName(platform)}...</p>
              </div>
            )}

            {!['greenhouse', 'workday', 'lever', 'ashby', 'smartrecruiters'].includes(platform) &&
             (state === 'ready' || state === 'review_required') && (
              <div>
                <p style={{ fontSize: 13, color: '#666', margin: '0 0 8px' }}>
                  Found {suggestions.filter(s => s.value).length} matching fields
                </p>
                {suggestions.filter(s => s.value).map(sug => {
                  const field = fields.find(f => f.id === sug.fieldId);
                  return (
                    <div key={sug.fieldId} style={s.fieldRow}>
                      <span style={s.fieldLabel}>{field?.label || sug.fieldId}</span>
                      <span style={s.fieldValue}>{sug.value}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {state === 'completed' && (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <p style={{ fontSize: 32, margin: '0 0 8px' }}>✅</p>
                <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                  {fillResults.filter(r => r.success).length} of {fillResults.length} fields filled
                </p>
                {fillResults.filter(r => !r.success).length > 0 && (
                  <p style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
                    Failed: {fillResults.filter(r => !r.success).map(r => r.label || r.fieldId).join(', ')}
                  </p>
                )}
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                  <button onClick={handleRefill} disabled={loading} style={{ ...s.secondaryBtn, fontSize: 13 }}>
                    {loading ? 'Retrying...' : 'Retry Fill'}
                  </button>
                  <button onClick={() => { setState('idle'); setFillResults([]); setStatusText(''); }}
                    style={{ ...s.secondaryBtn, fontSize: 13, background: '#ff9900', color: 'white', border: 'none' }}>
                    Done
                  </button>
                </div>
              </div>
            )}

            {state === 'error' && (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <p style={{ fontSize: 32, margin: '0 0 8px' }}>❌</p>
                <p style={{ fontSize: 14, color: '#dc3545', marginBottom: 8 }}>{error || 'Fill failed'}</p>
                <button onClick={() => { setState('idle'); setStatusText(''); }} style={s.secondaryBtn}>Try Again</button>
              </div>
            )}
          </div>
        )}

        {/* PROFILE TAB */}
        {tab === 'profile' && (
          <ProfilePanel profile={profile}
            onUpdateProfile={async (p) => {
              const updated = { ...profile, ...p } as ApplicationProfile;
              setProfile(updated);
              await chrome.storage.local.set({ profile: updated });
              try { await api.updateProfile(updated); } catch {}
            }} />
        )}

        {/* HISTORY TAB */}
        {tab === 'history' && (
          <div>
            <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>Recent Applications</h3>
            {sessions.length === 0 ? (
              <p style={{ color: '#999', fontSize: 12, textAlign: 'center', padding: 20 }}>
                No applications tracked yet
              </p>
            ) : sessions.slice(0, 30).map((ses: any, i: number) => (
              <div key={i} style={s.sessionCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>
                      {ses.jobTitle || ses.company || new URL(ses.url).hostname}
                    </div>
                    <div style={{ fontSize: 11, color: '#666' }}>
                      {ses.company && ses.jobTitle ? ses.company + ' · ' : ''}
                      {getPlatformName(ses.platform)} · {ses.fieldsFilled || 0} fields filled
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: '#999' }}>
                    {new Date(ses.timestamp).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8f9fa', fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif' },
  header: { padding: '16px', background: '#1a1a2e', color: 'white' },
  title: { fontSize: 16, fontWeight: 700, margin: 0 },
  sub: { fontSize: 11, opacity: 0.6, margin: '4px 0 0' },
  tab: { flex: 1, padding: '10px', border: 'none', background: 'none', cursor: 'pointer', fontSize: 13, color: '#666' },
  input: { padding: '10px 12px', border: '1px solid #ddd', borderRadius: 6, fontSize: 13, outline: 'none' },
  primaryBtn: { width: '100%', padding: '12px', background: '#ff9900', color: 'white', border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: 'pointer' },
  secondaryBtn: { padding: '10px 16px', background: 'white', color: '#333', border: '1px solid #ddd', borderRadius: 6, fontSize: 13, cursor: 'pointer' },
  fieldRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'white', borderRadius: 4, marginBottom: 4, border: '1px solid #f0f0f0' },
  fieldLabel: { fontSize: 12, color: '#666', textTransform: 'capitalize' },
  fieldValue: { fontSize: 12, fontWeight: 500, color: '#333', maxWidth: '60%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  sessionCard: { padding: '8px 12px', background: 'white', borderRadius: 6, border: '1px solid #eee', marginBottom: 6 },
};

export default App;
