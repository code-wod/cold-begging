import { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import { useAuth } from '../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function ExtensionApplications() {
  const { user } = useAuth();
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) loadData();
  }, [user]);

  async function loadData() {
    try {
      const token = localStorage.getItem('cold_email_token');
      const headers = { Authorization: `Bearer ${token}` };

      const [appsRes, statsRes] = await Promise.all([
        fetch(`${API}/extension/applications`, { headers }),
        fetch(`${API}/extension/stats`, { headers }),
      ]);

      if (appsRes.ok) setApplications(await appsRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (err) {
      console.error('Failed to load extension data:', err);
    } finally {
      setLoading(false);
    }
  }

  function getPlatformColor(platform) {
    const colors = {
      greenhouse: '#28a745',
      workday: '#007bff',
      lever: '#4a154b',
      ashby: '#ff6b35',
      smartrecruiters: '#2196f3',
      generic: '#6c757d',
    };
    return colors[platform] || '#6c757d';
  }

  if (!user) {
    return (
      <Layout>
        <div style={{ padding: 40, textAlign: 'center' }}>
          <p>Sign in to view your extension activity.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 20px' }}>
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 8px' }}>Extension Applications</h1>
          <p style={{ color: '#666', margin: 0 }}>Track every job application filled via the Codessy browser extension.</p>
        </div>

        {/* Stats cards */}
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
            <StatCard label="Total Applications" value={stats.totalSessions} icon="📋" />
            <StatCard label="Fields Filled" value={stats.totalFieldsFilled} icon="⚡" />
            <StatCard label="Detection Rate" value={stats.totalFieldsDetected > 0 ? `${Math.round((stats.totalFieldsFilled / stats.totalFieldsDetected) * 100)}%` : '—'} icon="🎯" />
            <StatCard label="Completed" value={stats.completedSessions} icon="✓" />
          </div>
        )}

        {/* Platform breakdown */}
        {stats && Object.keys(stats.platformBreakdown).length > 0 && (
          <div style={{ marginBottom: 32 }}>
            <h3 style={{ fontSize: 16, margin: '0 0 12px' }}>Platform Breakdown</h3>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {Object.entries(stats.platformBreakdown).map(([platform, count]) => (
                <div key={platform} style={{
                  padding: '8px 16px', borderRadius: 20, fontSize: 13, fontWeight: 500,
                  background: getPlatformColor(platform) + '15', color: getPlatformColor(platform),
                  border: `1px solid ${getPlatformColor(platform)}30`,
                }}>
                  {platform} ({count})
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Applications list */}
        <div>
          <h3 style={{ fontSize: 16, margin: '0 0 12px' }}>Recent Applications</h3>

          {loading ? (
            <p style={{ color: '#999', textAlign: 'center', padding: 40 }}>Loading...</p>
          ) : applications.length === 0 ? (
            <div style={{
              textAlign: 'center', padding: 60, background: '#f8f9fa', borderRadius: 12, border: '1px solid #eee',
            }}>
              <p style={{ fontSize: 48, margin: '0 0 12px' }}>📋</p>
              <h3 style={{ margin: '0 0 8px', fontSize: 16 }}>No applications yet</h3>
              <p style={{ color: '#666', margin: '0 0 16px', fontSize: 14 }}>
                Install the browser extension and start filling job applications.
              </p>
              <a href="/extension/download" style={{
                display: 'inline-block', padding: '10px 24px', background: '#ff9900', color: '#fff',
                borderRadius: 8, textDecoration: 'none', fontSize: 14, fontWeight: 600,
              }}>
                Download Extension
              </a>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {applications.map((app) => (
                <div key={app.id} style={{
                  padding: '14px 16px', background: '#fff', borderRadius: 10, border: '1px solid #eee',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16,
                }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 14, fontWeight: 600 }}>
                        {app.company || extractCompany(app.url)}
                      </span>
                      {app.platform && (
                        <span style={{
                          padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 500,
                          background: getPlatformColor(app.platform) + '15',
                          color: getPlatformColor(app.platform),
                        }}>
                          {app.platform}
                        </span>
                      )}
                    </div>
                    {app.jobTitle && (
                      <div style={{ fontSize: 13, color: '#333', marginBottom: 2 }}>{app.jobTitle}</div>
                    )}
                    <a href={app.url} target="_blank" rel="noreferrer"
                      style={{ fontSize: 12, color: '#0066cc', textDecoration: 'none', wordBreak: 'break-all' }}>
                      {app.url}
                    </a>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#28a745' }}>
                      {app.fieldsFilled}/{app.fieldsDetected}
                    </div>
                    <div style={{ fontSize: 11, color: '#999' }}>fields filled</div>
                    <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                      {app.createdAt ? new Date(app.createdAt).toLocaleDateString() : '—'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

function StatCard({ label, value, icon }) {
  return (
    <div style={{
      padding: '16px 20px', background: '#fff', borderRadius: 10, border: '1px solid #eee',
    }}>
      <div style={{ fontSize: 24, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a2e' }}>{value}</div>
      <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{label}</div>
    </div>
  );
}

function extractCompany(url) {
  try {
    const hostname = new URL(url).hostname;
    const parts = hostname.replace('www.', '').split('.');
    return parts[0] || hostname;
  } catch {
    return url;
  }
}
