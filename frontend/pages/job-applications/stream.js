import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { Panel, Button, Spinner, Input } from '../../components/ui';
import { api, getToken } from '../../lib/api';

export default function BrowserStreamPage() {
  const [url, setUrl] = useState('');
  const [connected, setConnected] = useState(false);
  const [screenshot, setScreenshot] = useState(null);
  const [fields, setFields] = useState([]);
  const [profile, setProfile] = useState(null);
  const [fieldValues, setFieldValues] = useState({});
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [step, setStep] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [pageTitle, setPageTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const wsRef = useRef(null);

  const connect = useCallback(() => {
    if (!url.trim()) return;
    if (wsRef.current) wsRef.current.close();

    const token = getToken();
    const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsBase = base.replace('http', 'ws');

    setStatus('Connecting...');
    const ws = new WebSocket(`${wsBase}/api/ws/browser-stream?token=${token || ''}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setStatus('Opening page...');
      ws.send(JSON.stringify({ action: 'open', url: url.trim() }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'profile') {
        setProfile(data.data);
      } else if (data.type === 'screenshot') {
        setScreenshot(data.data);
      } else if (data.type === 'step') {
        setFields(data.fields || []);
        setStep(data.step || 1);
        setHasNext(data.has_next || false);
        setPageTitle(data.page_title || '');
        if (data.profile) setProfile(data.profile);
        setFieldValues({});
        setSearch('');
        if (data.filled_count !== undefined) {
          setStatus(`Filled ${data.filled_count} fields`);
        }
        setBusy(false);
      } else if (data.type === 'error') {
        setStatus('Error: ' + data.message);
        setBusy(false);
      }
    };

    ws.onclose = () => { setConnected(false); setStatus('Disconnected'); setBusy(false); };
    ws.onerror = () => { setStatus('Connection error'); setBusy(false); };
  }, [url]);

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: 'close' }));
      wsRef.current.close();
    }
    setConnected(false); setScreenshot(null); setFields([]); setFieldValues({});
    setStatus(''); setStep(0); setHasNext(false); setPageTitle('');
  };

  const setFieldValue = (fieldName, value) => {
    setFieldValues((prev) => ({ ...prev, [fieldName]: value }));
  };

  const fillAndNext = () => {
    if (!wsRef.current || busy) return;
    const fieldsToSend = fields
      .filter((f) => fieldValues[f.name] !== undefined && fieldValues[f.name] !== '')
      .map((f) => ({ ...f, value: fieldValues[f.name] }));
    if (fieldsToSend.length === 0) {
      alert('Fill at least one field before proceeding');
      return;
    }
    setBusy(true);
    setStatus('Filling and advancing...');
    wsRef.current.send(JSON.stringify({ action: 'fill-and-next', fields: fieldsToSend }));
  };

  const fillAndSubmit = () => {
    if (!wsRef.current || busy) return;
    if (!confirm('Submit this application?')) return;
    const fieldsToSend = fields
      .filter((f) => fieldValues[f.name] !== undefined && fieldValues[f.name] !== '')
      .map((f) => ({ ...f, value: fieldValues[f.name] }));
    setBusy(true);
    setStatus('Filling and submitting...');
    wsRef.current.send(JSON.stringify({ action: 'fill-and-submit', fields: fieldsToSend }));
  };

  const autoFillFromProfile = () => {
    if (!profile || !fields.length) return;
    const newValues = { ...fieldValues };
    for (const f of fields) {
      if (newValues[f.name]) continue; // don't overwrite
      const label = f.label.toLowerCase();
      const name = f.name.toLowerCase();
      // Match profile fields to form fields by label/name
      for (const [key, val] of Object.entries(profile)) {
        if (!val || val === '') continue;
        const valStr = String(val);
        const keyNorm = key.replace(/_/g, ' ').toLowerCase();
        if (label.includes(keyNorm) || name.includes(keyNorm) ||
            keyNorm.includes(label) || keyNorm.includes(name)) {
          newValues[f.name] = valStr;
          break;
        }
        // Common aliases
        if ((label.includes('name') || name.includes('name')) && key === 'full_name') { newValues[f.name] = valStr; break; }
        if ((label.includes('email') || name.includes('email')) && key === 'email') { newValues[f.name] = valStr; break; }
        if ((label.includes('phone') || label.includes('tel') || name.includes('phone')) && key === 'phone') { newValues[f.name] = valStr; break; }
        if ((label.includes('city') || name.includes('city')) && key === 'city') { newValues[f.name] = valStr; break; }
        if ((label.includes('state') || name.includes('state')) && key === 'state') { newValues[f.name] = valStr; break; }
        if ((label.includes('linkedin') || name.includes('linkedin')) && key === 'linkedin') { newValues[f.name] = valStr; break; }
        if ((label.includes('github') || name.includes('github')) && key === 'github') { newValues[f.name] = valStr; break; }
        if ((label.includes('salary') || name.includes('salary')) && key === 'desired_salary') { newValues[f.name] = valStr; break; }
        if ((label.includes('experience') || name.includes('experience')) && key === 'years_experience') { newValues[f.name] = valStr; break; }
        if ((label.includes('company') || name.includes('company')) && key === 'current_company') { newValues[f.name] = valStr; break; }
        if ((label.includes('title') || label.includes('role') || name.includes('title')) && key === 'current_title') { newValues[f.name] = valStr; break; }
        if ((label.includes('authoriz') || name.includes('authoriz')) && key === 'work_authorization') { newValues[f.name] = valStr; break; }
        if ((label.includes('sponsor') || name.includes('sponsor')) && key === 'requires_sponsorship') { newValues[f.name] = valStr; break; }
      }
    }
    setFieldValues(newValues);
    const filled = Object.keys(newValues).filter((k) => newValues[k] && !fieldValues[k]).length;
    setStatus(`Auto-filled ${filled} fields from profile`);
  };

  const getProfileSuggestion = (field) => {
    if (!profile) return [];
    const label = (field.label + ' ' + field.name).toLowerCase();
    const suggestions = [];
    for (const [key, val] of Object.entries(profile)) {
      if (!val || val === '') continue;
      const valStr = String(val);
      const keyNorm = key.replace(/_/g, ' ').toLowerCase();
      let score = 0;
      if (label.includes(keyNorm) || keyNorm.includes(label)) score = 3;
      else if (label.split(' ').some((w) => keyNorm.includes(w) && w.length > 2)) score = 2;
      else if (valStr.length > 0 && valStr.length < 100) score = 1;
      if (score > 0) suggestions.push({ key, label: key.replace(/_/g, ' '), value: valStr, score });
    }
    return suggestions.sort((a, b) => b.score - a.score).slice(0, 5);
  };

  const filteredFields = search
    ? fields.filter((f) => (f.label + f.name).toLowerCase().includes(search.toLowerCase()))
    : fields;

  return (
    <Layout title="Guided Application Fill" breadcrumb={<><Link href="/job-applications">Applications</Link> / <span>Guided Fill</span></>}>
      {/* URL bar */}
      <Panel bodyClassName="p-16" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Input value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste job application URL..."
            style={{ flex: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && !connected && connect()}
            disabled={connected} />
          {!connected ? (
            <Button onClick={connect} disabled={!url.trim()}>Open</Button>
          ) : (
            <Button variant="outline" onClick={disconnect}>Close</Button>
          )}
          {status && <span className="muted" style={{ fontSize: 12 }}>{status}</span>}
        </div>
      </Panel>

      {!connected && !screenshot && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <h3 style={{ marginBottom: 8 }}>Paste a job URL and click Open</h3>
          <p className="muted" style={{ fontSize: 14 }}>
            The system opens the page step-by-step. Fill fields from your profile, then click Next to advance.
          </p>
        </div>
      )}

      {connected && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 16, alignItems: 'start' }}>
          {/* Left: Screenshot + step info */}
          <div>
            <Panel style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>Step {step}{pageTitle ? ` — ${pageTitle}` : ''}</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Button variant="outline" onClick={autoFillFromProfile} disabled={busy || !profile || fields.length === 0}>
                    Auto-Fill from Profile
                  </Button>
                  {hasNext ? (
                    <Button onClick={fillAndNext} disabled={busy || Object.values(fieldValues).every((v) => !v)}>
                      {busy ? 'Filling...' : 'Fill & Next'}
                    </Button>
                  ) : fields.length > 0 ? (
                    <Button onClick={fillAndSubmit} disabled={busy}>
                      {busy ? 'Submitting...' : 'Fill & Submit'}
                    </Button>
                  ) : null}
                </div>
              </div>
              {screenshot && (
                <div style={{ textAlign: 'center' }}>
                  <img src={`data:image/png;base64,${screenshot}`} alt="Page"
                    style={{ maxWidth: '100%', borderRadius: 4, border: '1px solid var(--border)' }} />
                </div>
              )}
              {!screenshot && <div style={{ textAlign: 'center', padding: 40 }}><Spinner /></div>}
            </Panel>
          </div>

          {/* Right: Fields to fill */}
          <Panel title={`Fields (${filteredFields.length})`} style={{ position: 'sticky', top: 80 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search fields..." style={{ marginBottom: 8, fontSize: 12 }} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 600, overflowY: 'auto' }}>
              {!profile ? <Spinner /> : filteredFields.length === 0 ? (
                <div className="muted" style={{ fontSize: 12, textAlign: 'center', padding: 16 }}>
                  {fields.length === 0 ? 'No fields on this step' : 'No matching fields'}
                </div>
              ) : filteredFields.map((f) => {
                const val = fieldValues[f.name] || '';
                const suggestions = getProfileSuggestion(f);
                return (
                  <div key={f.name + f.index} style={{
                    padding: '10px 12px', borderRadius: 6,
                    border: `1px solid ${val ? 'var(--success)' : 'var(--border)'}`,
                    background: val ? 'rgba(0,200,0,0.03)' : 'transparent',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 500, fontSize: 13 }}>{f.label}</span>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {f.required && <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: 'var(--error)', color: 'white' }}>Required</span>}
                        <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: 'var(--bg-secondary)' }}>{f.type}</span>
                      </div>
                    </div>

                    {/* Input */}
                    {f.type === 'select' && f.options.length > 0 ? (
                      <select value={val} onChange={(e) => setFieldValue(f.name, e.target.value)}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--input)', fontSize: 13 }}>
                        <option value="">-- Select --</option>
                        {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    ) : f.type === 'radio' ? (
                      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                        {f.options.map((o) => (
                          <label key={o.value} style={{ display: 'flex', gap: 4, fontSize: 13, cursor: 'pointer' }}>
                            <input type="radio" name={`f_${f.name}_${f.index}`} checked={val === o.value}
                              onChange={() => setFieldValue(f.name, o.value)} />
                            {o.label}
                          </label>
                        ))}
                      </div>
                    ) : f.type === 'checkbox' ? (
                      <label style={{ display: 'flex', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                        <input type="checkbox" checked={val === 'true' || val === 'Yes'}
                          onChange={(e) => setFieldValue(f.name, e.target.checked ? 'true' : 'false')} />
                        Yes
                      </label>
                    ) : (
                      <input value={val} onChange={(e) => setFieldValue(f.name, e.target.value)}
                        placeholder={f.label}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--input)', fontSize: 13 }} />
                    )}

                    {/* Profile suggestions */}
                    {suggestions.length > 0 && !val && (
                      <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {suggestions.map((s) => (
                          <button key={s.key} onClick={() => setFieldValue(f.name, s.value)}
                            style={{ padding: '2px 8px', borderRadius: 3, fontSize: 11, border: '1px solid var(--accent)',
                              background: 'rgba(255,153,0,0.08)', cursor: 'pointer', color: 'var(--accent)' }}
                            title={s.value}>
                            {s.label}: {s.value.length > 30 ? s.value.substring(0, 30) + '...' : s.value}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Panel>
        </div>
      )}
    </Layout>
  );
}
