import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { Panel, Button, Spinner, Input } from '../../components/ui';
import { api, getToken } from '../../lib/api';

const PROFILE_FIELDS = [
  { key: 'full_name', label: 'Full Name' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'location', label: 'Location' },
  { key: 'city', label: 'City' },
  { key: 'state', label: 'State' },
  { key: 'linkedin', label: 'LinkedIn' },
  { key: 'github', label: 'GitHub' },
  { key: 'portfolio', label: 'Portfolio' },
  { key: 'years_experience', label: 'Years Experience' },
  { key: 'current_company', label: 'Current Company' },
  { key: 'current_title', label: 'Current Title' },
  { key: 'desired_salary', label: 'Desired Salary' },
  { key: 'work_authorization', label: 'Work Authorization' },
  { key: 'requires_sponsorship', label: 'Requires Sponsorship' },
];

export default function BrowserStreamPage() {
  const [url, setUrl] = useState('');
  const [connected, setConnected] = useState(false);
  const [screenshot, setScreenshot] = useState(null);
  const [fields, setFields] = useState([]);
  const [profile, setProfile] = useState(null);
  const [selectedField, setSelectedField] = useState(null);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  const wsRef = useRef(null);
  const imgRef = useRef(null);

  useEffect(() => {
    api('/api/job-applications/profile').then((data) => setProfile(data)).catch(() => {});
  }, []);

  const connect = useCallback(() => {
    if (!url.trim()) return;
    if (wsRef.current) wsRef.current.close();

    const token = getToken();
    const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsBase = base.replace('http', 'ws');
    const wsUrl = `${wsBase}/api/ws/browser-stream?token=${token || ''}`;

    setStatus('Connecting...');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setStatus('Opening page...');
      ws.send(JSON.stringify({ action: 'open', url: url.trim() }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'screenshot') {
        setScreenshot(data.data);
        setStatus('Live');
      } else if (data.type === 'fields') {
        setFields(data.fields || []);
      } else if (data.type === 'filled') {
        if (data.success) setStatus('Field filled!');
        else setStatus('Fill failed');
      } else if (data.type === 'error') {
        setStatus('Error: ' + data.message);
      }
    };

    ws.onclose = () => { setConnected(false); setStatus('Disconnected'); };
    ws.onerror = () => { setStatus('Connection error'); };
  }, [url]);

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: 'close' }));
      wsRef.current.close();
    }
    setConnected(false); setScreenshot(null); setFields([]); setStatus(''); setSelectedField(null);
  };

  const sendMsg = (msg) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  };

  const fillField = (fieldIndex, value) => {
    sendMsg({ action: 'fill', index: fieldIndex, value });
  };

  const handleImgClick = (e) => {
    if (!imgRef.current || !fields.length) return;
    const rect = imgRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Scale from displayed size to natural screenshot size
    const scaleX = imgRef.current.naturalWidth / rect.width;
    const scaleY = imgRef.current.naturalHeight / rect.height;
    const pageX = clickX * scaleX;
    const pageY = clickY * scaleY;

    // Find which field was clicked based on bounding box
    for (const f of fields) {
      const r = f.rect;
      if (pageX >= r.x && pageX <= r.x + r.width && pageY >= r.y && pageY <= r.y + r.height) {
        setSelectedField(f);
        setStatus(`Selected: ${f.label}`);
        return;
      }
    }
    // Clicked on empty area - deselect
    setSelectedField(null);
  };

  const handleImgLoad = () => {
    if (imgRef.current) {
      setImgSize({ w: imgRef.current.naturalWidth, h: imgRef.current.naturalHeight });
    }
  };

  const filteredProfile = PROFILE_FIELDS.filter((pf) => {
    if (!profile) return false;
    const val = profile[pf.key];
    if (!val) return false;
    if (search) {
      const q = search.toLowerCase();
      return pf.label.toLowerCase().includes(q) || String(val).toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <Layout title="Browser Stream" breadcrumb={<><Link href="/job-applications">Applications</Link> / <span>Browser Stream</span></>}>
      {/* URL bar */}
      <Panel bodyClassName="p-16" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Input value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste job application URL and press Open..."
            style={{ flex: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && !connected && connect()}
            disabled={connected} />
          {!connected ? (
            <Button onClick={connect} disabled={!url.trim()}>Open</Button>
          ) : (
            <Button variant="outline" onClick={disconnect}>Close</Button>
          )}
          {status && <span className="muted" style={{ fontSize: 12, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{status}</span>}
        </div>
      </Panel>

      {!connected && !screenshot && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <h3 style={{ marginBottom: 8 }}>Paste a job URL above and click Open</h3>
          <p className="muted" style={{ fontSize: 14 }}>The page will stream here. Click on form fields to fill them from your profile.</p>
        </div>
      )}

      {/* Main: browser + profile sidebar */}
      {connected && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 16, alignItems: 'start' }}>
          {/* Browser */}
          <Panel title="Browser" style={{ minHeight: 400 }}>
            {!screenshot ? (
              <div style={{ textAlign: 'center', padding: 60 }}><Spinner /><div className="muted" style={{ marginTop: 12 }}>Loading page...</div></div>
            ) : (
              <div style={{ position: 'relative', display: 'inline-block', width: '100%', textAlign: 'center' }}>
                <img
                  ref={imgRef}
                  src={`data:image/png;base64,${screenshot}`}
                  alt="Browser"
                  onLoad={handleImgLoad}
                  onClick={handleImgClick}
                  style={{ maxWidth: '100%', borderRadius: 4, cursor: 'crosshair', border: '1px solid var(--border)' }}
                />
                {/* Field overlay boxes */}
                {imgRef.current && imgRef.current.naturalWidth > 0 && fields.map((f) => {
                  const rect = imgRef.current.getBoundingClientRect();
                  const sx = rect.width / imgRef.current.naturalWidth;
                  const sy = rect.height / imgRef.current.naturalHeight;
                  const r = f.rect;
                  const isSel = selectedField && selectedField.index === f.index;
                  return (
                    <div key={f.index}
                      onClick={(e) => { e.stopPropagation(); setSelectedField(f); setStatus('Selected: ' + f.label); }}
                      style={{
                        position: 'absolute',
                        left: r.x * sx, top: r.y * sy,
                        width: r.width * sx, height: r.height * sy,
                        border: `2px solid ${isSel ? '#ff9900' : 'rgba(255,153,0,0.25)'}`,
                        background: isSel ? 'rgba(255,153,0,0.12)' : 'transparent',
                        cursor: 'pointer', borderRadius: 2, pointerEvents: 'auto',
                      }}
                      title={f.label}
                    />
                  );
                })}
              </div>
            )}
          </Panel>

          {/* Profile sidebar */}
          <Panel title={selectedField ? `Fill: ${selectedField.label}` : 'Your Profile'} style={{ position: 'sticky', top: 80 }}>
            {selectedField && (
              <div style={{ padding: 10, borderRadius: 6, background: 'var(--bg-secondary)', marginBottom: 12, border: '1px solid var(--accent)' }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{selectedField.label}</div>
                <div className="muted" style={{ fontSize: 11 }}>
                  Type: {selectedField.type}{selectedField.name ? ` | Name: ${selectedField.name}` : ''}
                </div>
                {selectedField.value && (
                  <div style={{ fontSize: 12, marginTop: 4, padding: '4px 6px', borderRadius: 3, background: 'var(--card)', border: '1px solid var(--border)' }}>
                    Current: {selectedField.value}
                  </div>
                )}
              </div>
            )}

            <Input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search profile values..." style={{ marginBottom: 8, fontSize: 12 }} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 450, overflowY: 'auto' }}>
              {!profile ? <Spinner /> : filteredProfile.length === 0 ? (
                <div className="muted" style={{ fontSize: 12, textAlign: 'center', padding: 16 }}>No matching values</div>
              ) : filteredProfile.map((pf) => {
                const val = String(profile[pf.key]);
                const clickable = !!selectedField;
                return (
                  <div key={pf.key}
                    onClick={() => {
                      if (!clickable) return;
                      fillField(selectedField.index, val);
                      setStatus(`Filled "${pf.label}" -> ${selectedField.label}`);
                    }}
                    style={{
                      padding: '8px 10px', borderRadius: 4,
                      border: `1px solid ${clickable ? 'var(--border)' : 'var(--border)'}`,
                      cursor: clickable ? 'pointer' : 'default',
                      background: clickable ? 'var(--bg-secondary)' : 'transparent',
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={(e) => { if (clickable) { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.background = 'rgba(255,153,0,0.05)'; } }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = clickable ? 'var(--bg-secondary)' : 'transparent'; }}
                  >
                    <div className="muted" style={{ fontSize: 10, marginBottom: 2 }}>{pf.label}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{val}</div>
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 4, background: 'var(--bg-secondary)', fontSize: 11, color: 'var(--muted)', textAlign: 'center' }}>
              {selectedField
                ? 'Click a profile value above to fill this field'
                : 'Click a field on the page (orange boxes) to select it, then pick a value'}
            </div>
          </Panel>
        </div>
      )}
    </Layout>
  );
}
