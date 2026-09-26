import { useState, useEffect, useRef } from 'react';
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

export default function IframeFillPage() {
  const [url, setUrl] = useState('');
  const [iframeUrl, setIframeUrl] = useState('');
  const [iframeBlocked, setIframeBlocked] = useState(false);
  const [profile, setProfile] = useState(null);
  const [search, setSearch] = useState('');
  const [copiedKey, setCopiedKey] = useState('');
  const [autoFilling, setAutoFilling] = useState(false);
  const [autoFillResult, setAutoFillResult] = useState(null);
  const iframeRef = useRef(null);

  useEffect(() => {
    api('/api/job-applications/profile').then((data) => setProfile(data)).catch(() => {});
  }, []);

  const loadInIframe = () => {
    if (!url.trim()) return;
    setIframeBlocked(false);
    setAutoFillResult(null);
    setIframeUrl(url.trim());
  };

  const handleIframeError = () => {
    setIframeBlocked(true);
  };

  const autoFillViaPlaywright = async () => {
    if (!url.trim()) return;
    setAutoFilling(true);
    setAutoFillResult(null);
    try {
      const res = await api('/api/job-applications/auto-fill', {
        method: 'POST',
        body: { job_url: url.trim() },
      });
      setAutoFillResult(res);
      // Refresh iframe to show filled state
      if (iframeRef.current) {
        iframeRef.current.src = iframeRef.current.src;
      }
    } catch (e) {
      setAutoFillResult({ error: e.message });
    } finally {
      setAutoFilling(false);
    }
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(''), 1500);
    });
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
    <Layout title="Fill Application" breadcrumb={<><Link href="/job-applications">Applications</Link> / <span>Fill</span></>}>
      {/* URL bar */}
      <Panel bodyClassName="p-16" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste job application URL..."
            style={{ flex: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && loadInIframe()}
          />
          <Button onClick={loadInIframe} disabled={!url.trim()}>Open</Button>
          {iframeUrl && (
            <Button variant="outline" onClick={autoFillViaPlaywright} disabled={autoFilling}>
              {autoFilling ? 'Auto-Filling...' : 'Auto-Fill with Profile'}
            </Button>
          )}
        </div>
        {autoFillResult && !autoFillResult.error && (
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Auto-filled {autoFillResult.total_filled}/{autoFillResult.total_fields} fields
            across {autoFillResult.total_steps} step(s)
          </div>
        )}
        {autoFillResult?.error && (
          <div style={{ fontSize: 12, marginTop: 8, color: 'var(--error)' }}>
            Auto-fill error: {autoFillResult.error}
          </div>
        )}
      </Panel>

      {/* Main: iframe + profile sidebar */}
      {iframeUrl && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 16, alignItems: 'start' }}>
          {/* Iframe */}
          <Panel title="Application Form" style={{ minHeight: 600 }}>
            {iframeBlocked ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <h3 style={{ marginBottom: 8, color: 'var(--error)' }}>iframe Blocked</h3>
                <p className="muted" style={{ fontSize: 14, marginBottom: 16 }}>
                  This job site blocks iframe embedding (X-Frame-Options / CSP).
                </p>
                <p className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
                  Options:
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 400, margin: '0 auto' }}>
                  <Button onClick={autoFillViaPlaywright} disabled={autoFilling}>
                    {autoFilling ? 'Auto-Filling...' : 'Auto-Fill via Playwright (background)'}
                  </Button>
                  <Button variant="outline" onClick={() => window.open(url, '_blank')}>
                    Open in New Tab
                  </Button>
                </div>
                {autoFillResult && !autoFillResult.error && (
                  <div style={{ marginTop: 16, padding: 12, borderRadius: 6, background: 'var(--bg-secondary)', fontSize: 13 }}>
                    Playwright filled {autoFillResult.total_filled}/{autoFillResult.total_fields} fields.
                    Open in new tab to review and submit.
                  </div>
                )}
              </div>
            ) : (
              <div style={{ position: 'relative', width: '100%', height: '70vh' }}>
                <iframe
                  ref={iframeRef}
                  src={iframeUrl}
                  onError={handleIframeError}
                  onLoad={() => {
                    // Check if iframe loaded same-origin content
                    try {
                      iframeRef.current.contentDocument;
                    } catch (e) {
                      // Cross-origin - iframe loaded but we can't access it
                      // This is fine - user can still interact with it
                    }
                  }}
                  style={{
                    width: '100%',
                    height: '100%',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                  }}
                  sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                  title="Job Application"
                />
              </div>
            )}
          </Panel>

          {/* Profile sidebar */}
          <Panel title="Your Profile" style={{ position: 'sticky', top: 80 }}>
            <div className="muted" style={{ fontSize: 11, marginBottom: 8 }}>
              Click a value to copy it, then paste into the form
            </div>
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              style={{ marginBottom: 8, fontSize: 12 }}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 500, overflowY: 'auto' }}>
              {!profile ? <Spinner /> : filteredProfile.length === 0 ? (
                <div className="muted" style={{ fontSize: 12, textAlign: 'center', padding: 12 }}>No values</div>
              ) : filteredProfile.map((pf) => {
                const val = String(profile[pf.key]);
                const isCopied = copiedKey === pf.key;
                return (
                  <div
                    key={pf.key}
                    onClick={() => copyToClipboard(val, pf.key)}
                    style={{
                      padding: '8px 10px', borderRadius: 4,
                      border: `1px solid ${isCopied ? 'var(--success)' : 'var(--border)'}`,
                      cursor: 'pointer',
                      background: isCopied ? 'rgba(0,200,0,0.05)' : 'var(--bg-secondary)',
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = isCopied ? 'var(--success)' : 'var(--border)'; }}
                  >
                    <div className="muted" style={{ fontSize: 10, marginBottom: 2 }}>{pf.label}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {isCopied ? 'Copied!' : val}
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 4, background: 'var(--bg-secondary)', fontSize: 11, color: 'var(--muted)', textAlign: 'center' }}>
              Click a value to copy, then paste into the form field
            </div>
          </Panel>
        </div>
      )}

      {/* Empty state */}
      {!iframeUrl && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <h3 style={{ marginBottom: 8 }}>Paste a job URL and click Open</h3>
          <p className="muted" style={{ fontSize: 14 }}>
            The application form opens in an embedded frame.<br />
            Click profile values on the right to copy, then paste into the form.<br />
            Or use "Auto-Fill with Profile" to fill everything automatically.
          </p>
          {!profile && (
            <div style={{ marginTop: 16, padding: 12, borderRadius: 6, background: 'var(--bg-secondary)', fontSize: 13 }}>
              <Link href="/job-profile"><strong>Create your Job Profile first</strong></Link>
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
