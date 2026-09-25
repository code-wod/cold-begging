import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { Panel, Button, Spinner, Input } from '../../components/ui';
import { api } from '../../lib/api';

export default function AutoFillPage() {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('');
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    api('/api/job-applications/profile').then((data) => setProfile(data)).catch(() => {});
  }, []);

  const autoFill = async () => {
    if (!url.trim()) return;
    setBusy(true);
    setResult(null);
    setStatus('Opening page and filling fields...');
    try {
      const res = await api('/api/job-applications/auto-fill', {
        method: 'POST',
        body: { job_url: url.trim() },
      });
      setResult(res);
      setStatus(`Done! Filled ${res.total_filled}/${res.total_fields} fields across ${res.total_steps} step(s)`);
    } catch (e) {
      setStatus('Error: ' + e.message);
    } finally {
      setBusy(false);
    }
  };

  const filledPct = result && result.total_fields > 0
    ? Math.round((result.total_filled / result.total_fields) * 100)
    : 0;

  return (
    <Layout title="Auto-Fill Application" breadcrumb={<><Link href="/job-applications">Applications</Link> / <span>Auto-Fill</span></>}>
      {/* URL input */}
      <Panel bodyClassName="p-16" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste job application URL..."
            style={{ flex: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && !busy && autoFill()}
            disabled={busy}
          />
          <Button onClick={autoFill} disabled={busy || !url.trim()}>
            {busy ? 'Filling...' : 'Auto-Fill'}
          </Button>
        </div>
        {status && (
          <div className="muted" style={{ fontSize: 13, marginTop: 8 }}>{status}</div>
        )}
      </Panel>

      {/* Loading */}
      {busy && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spinner />
          <div className="muted" style={{ marginTop: 12 }}>
            Opening browser, detecting form fields, filling from your profile...
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            This may take 30-60 seconds per step
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div>
          {/* Summary */}
          <Panel style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--accent)' }}>{filledPct}%</div>
                <div className="muted" style={{ fontSize: 12 }}>Filled</div>
              </div>
              <div>
                <div style={{ fontSize: 24, fontWeight: 600 }}>{result.total_filled}/{result.total_fields}</div>
                <div className="muted" style={{ fontSize: 12 }}>Fields Filled</div>
              </div>
              <div>
                <div style={{ fontSize: 24, fontWeight: 600 }}>{result.total_steps}</div>
                <div className="muted" style={{ fontSize: 12 }}>Steps Completed</div>
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{result.ats_platform}</div>
                <div className="muted" style={{ fontSize: 12 }}>ATS Platform</div>
              </div>
            </div>
          </Panel>

          {/* Per-step results */}
          {result.steps.map((step, i) => (
            <Panel key={i} title={`Step ${step.step} — ${step.filled}/${step.total_fields} filled`} style={{ marginBottom: 16 }}>
              <div style={{ display: 'grid', gridTemplateColumns: result.screenshots[i] ? '1fr 1fr' : '1fr', gap: 16 }}>
                {/* Screenshot */}
                {result.screenshots[i] && (
                  <div style={{ textAlign: 'center' }}>
                    <img
                      src={`data:image/png;base64,${result.screenshots[i]}`}
                      alt={`Step ${step.step}`}
                      style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid var(--border)' }}
                    />
                  </div>
                )}

                {/* Fields */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 300, overflowY: 'auto' }}>
                  {step.fields.map((f, j) => {
                    const val = f.user_value || f.mapped_value || '';
                    const isFilled = f.status === 'filled';
                    return (
                      <div key={j} style={{
                        padding: '6px 10px', borderRadius: 4,
                        border: `1px solid ${isFilled ? 'var(--success)' : 'var(--border)'}`,
                        background: isFilled ? 'rgba(0,200,0,0.03)' : 'transparent',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 500 }}>{f.field_label || f.field_name || `Field ${j+1}`}</div>
                          {val && <div style={{ fontSize: 11, color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{val}</div>}
                        </div>
                        <div style={{ flexShrink: 0, marginLeft: 8 }}>
                          {isFilled ? (
                            <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, background: 'var(--success)', color: 'white' }}>Filled</span>
                          ) : f.confidence >= 0.7 ? (
                            <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, background: 'var(--warning)' }}>Partial</span>
                          ) : (
                            <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, background: 'var(--bg-secondary)' }}>Skipped</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {step.fields.length === 0 && (
                    <div className="muted" style={{ fontSize: 12, textAlign: 'center', padding: 12 }}>
                      {step.blocked ? 'Blocked by CAPTCHA/login' : 'No fields found on this step'}
                    </div>
                  )}
                </div>
              </div>
            </Panel>
          ))}

          {/* Profile used */}
          {profile && (
            <Panel title="Profile Data Used" style={{ marginTop: 16 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                {Object.entries(profile).filter(([k, v]) => v && typeof v === 'string' && v.length > 0).map(([key, val]) => (
                  <div key={key} style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid var(--border)' }}>
                    <div className="muted" style={{ fontSize: 10 }}>{key.replace(/_/g, ' ')}</div>
                    <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{val}</div>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      )}

      {/* Empty state */}
      {!busy && !result && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <h3 style={{ marginBottom: 8 }}>One-click auto-fill</h3>
          <p className="muted" style={{ fontSize: 14 }}>
            Paste a job URL, click Auto-Fill, and we will open the page,<br />
            detect all form fields, and fill them from your profile automatically.<br />
            Works across multiple steps — navigates through Next buttons.
          </p>
          {!profile && (
            <div style={{ marginTop: 16, padding: 12, borderRadius: 6, background: 'var(--bg-secondary)', fontSize: 13 }}>
              <Link href="/job-profile"><strong>Create your Job Profile first</strong></Link> so we know what to fill.
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
