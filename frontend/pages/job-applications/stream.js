import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { Panel, Button, Spinner, Input } from '../../components/ui';
import { api } from '../../lib/api';

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
  const wsRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    api.get('/job-applications/profile').then((r) => setProfile(r.data)).catch(() => {});
  }, []);

  const getWsUrl = useCallback(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') || sessionStorage.getItem('access_token') : '';
    const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsBase = base.replace('http', 'ws');
    return `${wsBase}/api/ws/browser-stream?token=${token}`;
  }, []);

  const connect = useCallback(() => {
    if (!url.trim()) return;
    if (wsRef.current) wsRef.current.close();

    setStatus('Connecting...');
    const ws = new WebSocket(getWsUrl());
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
        setStatus(data.success ? `Field ${data.index} filled` : 'Fill failed');
      } else if (data.type === 'error') {
        setStatus('Error: ' + data.message);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setStatus('Disconnected');
    };

    ws.onerror = () => {
      setStatus('Connection error');
    };
  }, [url, getWsUrl]);

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: 'close' }));
      wsRef.current.close();
    }
    setConnected(false);
    setScreenshot(null);
    setFields([]);
    setStatus('');
  };

  const fillField = (fieldIndex, value) => {
    if (wsRef.current && connected) {
      wsRef.current.send(JSON.stringify({ action: 'fill', index: fieldIndex, value }));
    }
  };

  const handleScreenshotClick = (e) => {
    if (!canvasRef.current || !fields.length) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Scale to actual page coordinates
    const scaleX = canvasRef.current.naturalWidth / rect.width;
    const scaleY = canvasRef.current.naturalHeight / rect.height;
    const pageX = x * scaleX;
    const pageY = y * scaleY;

    // Find which field was clicked
    for (const f of fields) {
      const r = f.rect;
      if (pageX >= r.x && pageX <= r.x + r.width && pageY >= r.y && pageY <= r.y + r.height) {
        setSelectedField(f);
        return;
      }
    }
    setSelectedField(null);
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
      {/* Controls */}
      <Panel bodyClassName="p-16" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste job application URL..."
            style={{ flex: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && !connected && connect()}
            disabled={connected}
          />
          {!connected ? (
            <Button onClick={connect} disabled={!url.trim()}>Open Page</Button>
          ) : (
            <Button variant="outline" onClick={disconnect}>Close</Button>
          )}
          {status && <span className="muted" style={{ fontSize: 12 }}>{status}</span>}
        </div>
      </Panel>

      {/* Main area */}
      <div style={{ display: 'grid', gridTemplateColumns: connected ? '1fr 280px' : '1fr', gap: 16, alignItems: 'start' }}>
        {/* Browser view */}
        <Panel title="Browser" style={{ minHeight: 400 }}>
          {!connected && !screenshot && (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <h3 style={{ marginBottom: 8 }}>Paste a job URL and click Open</h3>
              <p className="muted" style={{ fontSize: 14 }}>
                The page will open in a streamed browser. Click on any form field to see profile suggestions.
              </p>
            </div>
          )}
          {screenshot && (
            <div style={{ position: 'relative', textAlign: 'center' }}>
              <img
                ref={canvasRef}
                src={`data:image/png;base64,${screenshot}`}
                alt="Browser stream"
                onClick={handleScreenshotClick}
                style={{ maxWidth: '100%', borderRadius: 4, cursor: 'crosshair', border: '1px solid var(--border)' }}
              />
              {/* Field overlays */}
              {fields.map((f) => {
                if (!canvasRef.current) return null;
                const rect = canvasRef.current.getBoundingClientRect();
                const scaleX = rect.width / canvasRef.current.naturalWidth;
                const scaleY = rect.height / canvasRef.current.naturalHeight;
                const r = f.rect;
                const isSelected = selectedField?.index === f.index;
                return (
                  <div
                    key={f.index}
                    onClick={(e) => { e.stopPropagation(); setSelectedField(f); }}
                    style={{
                      position: 'absolute',
                      left: r.x * scaleX,
                      top: r.y * scaleY,
                      width: r.width * scaleX,
                      height: r.height * scaleY,
                      border: `1px solid ${isSelected ? 'var(--accent)' : 'rgba(255,153,0,0.3)'}`,
                      background: isSelected ? 'rgba(255,153,0,0.1)' : 'transparent',
                      cursor: 'pointer',
                      borderRadius: 2,
                      pointerEvents: 'auto',
                    }}
                    title={f.label}
                  />
                );
              })}
            </div>
          )}
          {connected && !screenshot && <div style={{ textAlign: 'center', padding: 40 }}><Spinner /></div>}
        </Panel>

        {/* Profile sidebar */}
        {connected && (
          <Panel title="Profile Values" style={{ position: 'sticky', top: 80 }}>
            {selectedField && (
              <div style={{ padding: 8, borderRadius: 4, background: 'var(--bg-secondary)', marginBottom: 12, fontSize: 12 }}>
                <div className="muted" style={{ marginBottom: 4 }}>Selected field:</div>
                <div style={{ fontWeight: 600 }}>{selectedField.label}</div>
                <div className="muted" style={{ fontSize: 11 }}>Type: {selectedField.type} | Name: {selectedField.name || selectedField.id || '—'}</div>
              </div>
            )}

            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search profile..."
              style={{ marginBottom: 8, fontSize: 12 }}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 400, overflowY: 'auto' }}>
              {!profile ? (
                <Spinner />
              ) : filteredProfile.length === 0 ? (
                <div className="muted" style={{ fontSize: 12, textAlign: 'center', padding: 12 }}>No matching profile values</div>
              ) : (
                filteredProfile.map((pf) => {
                  const val = String(profile[pf.key]);
                  return (
                    <div
                      key={pf.key}
                      onClick={() => {
                        if (selectedField) {
                          fillField(selectedField.index, val);
                        }
                      }}
                      style={{
                        padding: '8px 10px', borderRadius: 4,
                        border: '1px solid var(--border)',
                        cursor: selectedField ? 'pointer' : 'default',
                        background: selectedField ? 'var(--bg-secondary)' : 'transparent',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => { if (selectedField) e.currentTarget.style.borderColor = 'var(--accent)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; }}
                    >
                      <div className="muted" style={{ fontSize: 10, marginBottom: 2 }}>{pf.label}</div>
                      <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {val}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {!selectedField && (
              <div className="muted" style={{ fontSize: 11, textAlign: 'center', marginTop: 12 }}>
                Click a field on the page, then click a profile value to fill it
              </div>
            )}
          </Panel>
        )}
      </div>
    </Layout>
  );
}
