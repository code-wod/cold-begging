import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import { Panel, Button, Empty, Spinner, Input, Select } from '../../components/ui';
import { api } from '../../lib/api';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'preparing', label: 'Preparing' },
  { value: 'needs_review', label: 'Needs Review' },
  { value: 'ready', label: 'Ready' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

const PLATFORM_OPTIONS = [
  { value: '', label: 'All Platforms' },
  { value: 'greenhouse', label: 'Greenhouse' },
  { value: 'lever', label: 'Lever' },
  { value: 'ashby', label: 'Ashby' },
  { value: 'workday', label: 'Workday' },
  { value: 'unknown', label: 'Other' },
];

const STATUS_COLORS = {
  preparing: 'var(--muted)', needs_review: 'var(--warning)', ready: 'var(--info)',
  submitted: 'var(--success)', failed: 'var(--error)', cancelled: 'var(--muted)', submitting: 'var(--info)',
};

function Tag({ color, children, style }) {
  return <span style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600, background: color || 'var(--bg-secondary)', color: color ? 'white' : 'var(--text)', ...style }}>{children}</span>;
}

export default function ApplicationHistory() {
  const router = useRouter();
  const [apps, setApps] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [cleaning, setCleaning] = useState(false);

  const loadApps = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set('status', statusFilter);
      if (platformFilter) params.set('ats_platform', platformFilter);
      params.set('limit', '100');
      const [appsRes, statsRes] = await Promise.all([
        api(`/api/job-applications/history?${params.toString()}`),
        api('/api/job-applications/stats'),
      ]);
      setApps(appsRes); setStats(statsRes);
    } catch (e) { console.error('Failed to load history', e); }
    finally { setLoading(false); }
  }, [statusFilter, platformFilter]);

  useEffect(() => { loadApps(); }, [loadApps]);

  const cleanup = async () => {
    if (!confirm('Delete applications older than 30 days?')) return;
    setCleaning(true);
    try {
      const res = await api('/api/job-applications/cleanup?max_age_days=30', { method: 'POST' });
      alert(`Deleted ${res.deleted} old applications`); loadApps();
    } catch (e) { alert('Cleanup failed: ' + (e.response?.data?.detail || e.message)); }
    finally { setCleaning(false); }
  };

  const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '--';

  return (
    <Layout title="Application History">
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 24 }}>
          <Panel bodyClassName="p-16" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent)' }}>{stats.total}</div>
            <div className="muted" style={{ fontSize: 12 }}>Total Applications</div>
          </Panel>
          {Object.entries(stats.by_status || {}).map(([status, count]) => (
            <Panel key={status} bodyClassName="p-16" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: STATUS_COLORS[status] || 'var(--text)' }}>{count}</div>
              <div className="muted" style={{ fontSize: 12 }}>{status.replace('_', ' ')}</div>
            </Panel>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} options={STATUS_OPTIONS} style={{ flex: 1 }} />
        <Select value={platformFilter} onChange={(e) => setPlatformFilter(e.target.value)} options={PLATFORM_OPTIONS} style={{ flex: 1 }} />
        <Button variant="outline" onClick={cleanup} disabled={cleaning} style={{ flexShrink: 0 }}>{cleaning ? 'Cleaning...' : 'Cleanup Old'}</Button>
      </div>

      {loading ? <Spinner /> : apps.length === 0 ? <Empty message="No applications found." /> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {apps.map((app) => (
            <Panel key={app.id} style={{ padding: 16, cursor: 'pointer' }} onClick={() => router.push(`/job-applications/${app.id}`)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 15, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app.role_title || 'Untitled Role'}</span>
                    <Tag color={STATUS_COLORS[app.status] || 'var(--muted)'} style={{ fontSize: 10 }}>{app.status.replace('_', ' ')}</Tag>
                  </div>
                  <div className="muted" style={{ fontSize: 13 }}>{app.company_name || 'Unknown Company'}{app.ats_platform && app.ats_platform !== 'unknown' && <span style={{ marginLeft: 8, opacity: 0.6 }}>({app.ats_platform})</span>}</div>
                  <div className="muted" style={{ fontSize: 12, marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app.job_url}</div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 16 }}>
                  <div className="muted" style={{ fontSize: 12 }}>{formatDate(app.created_at)}</div>
                  {app.total_fields > 0 && <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>{app.auto_filled}/{app.total_fields} fields</div>}
                  {app.match_score && <div style={{ fontSize: 12, marginTop: 4, color: app.match_score >= 0.8 ? 'var(--success)' : 'var(--muted)' }}>Match: {Math.round(app.match_score * 100)}%</div>}
                </div>
              </div>
            </Panel>
          ))}
        </div>
      )}
    </Layout>
  );
}
