import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, fmtDate, useToast, Icons, Button, Modal } from '../../components/ui';

export default function Applications() {
  const { user } = useAuth();
  const toast = useToast();
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState('');
  const [stats, setStats] = useState({});
  const [selectedApp, setSelectedApp] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionType, setActionType] = useState('');

  useEffect(() => {
    fetchApplications();
    fetchStats();
  }, [page, statusFilter]);

  const fetchApplications = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
      if (statusFilter) params.append('status', statusFilter);
      const data = await api(`/api/applications?${params}`);
      setApplications(data.items);
      setTotal(data.total);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await api('/api/applications/stats');
      setStats(data);
    } catch (e) {
      console.error('Failed to fetch stats', e);
    }
  };

  const handleAction = async (app, type) => {
    setSelectedApp(app);
    setActionType(type);
    setActionLoading(true);
    try {
      if (type === 'approve') {
        await api(`/api/applications/${app.id}/approve`, { method: 'POST' });
        toast('Application approved!', 'success');
      } else if (type === 'open') {
        await api(`/api/applications/${app.id}/open`, { method: 'POST' });
        toast('Application opened!', 'success');
        if (app.application_url) {
          window.open(app.application_url, '_blank', 'noopener,noreferrer');
        }
      } else if (type === 'mark_applied') {
        await api(`/api/applications/${app.id}/mark-applied`, { method: 'POST', body: { notes: 'Applied via job board' } });
        toast('Marked as applied!', 'success');
      } else if (type === 'reject') {
        await api(`/api/applications/${app.id}/reject`, { method: 'POST', body: { reason: 'Not a good fit' } });
        toast('Application rejected', 'success');
      } else if (type === 'withdraw') {
        await api(`/api/applications/${app.id}/withdraw`, { method: 'POST', body: { reason: 'Withdrawn' } });
        toast('Application withdrawn', 'success');
      }
      fetchApplications();
      fetchStats();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setActionLoading(false);
      setSelectedApp(null);
    }
  };

  const getStatusActions = (app) => {
    const actions = [];
    if (app.status === 'ready') {
      actions.push({ type: 'approve', label: 'Approve', variant: 'primary' });
      actions.push({ type: 'reject', label: 'Reject', variant: 'danger' });
    } else if (app.status === 'approved') {
      actions.push({ type: 'open', label: 'Open Application', variant: 'primary' });
      actions.push({ type: 'reject', label: 'Reject', variant: 'danger' });
    } else if (app.status === 'application_opened') {
      actions.push({ type: 'mark_applied', label: 'Mark Applied', variant: 'primary' });
      actions.push({ type: 'reject', label: 'Reject', variant: 'danger' });
    } else if (app.status === 'applied') {
      actions.push({ type: 'reject', label: 'Reject', variant: 'danger' });
      actions.push({ type: 'withdraw', label: 'Withdraw', variant: 'secondary' });
    } else if (['screening', 'interview', 'offer'].includes(app.status)) {
      actions.push({ type: 'withdraw', label: 'Withdraw', variant: 'secondary' });
    }
    return actions;
  };

  const getScoreColor = (score) => {
    if (!score) return 'gray';
    if (score >= 80) return 'green';
    if (score >= 70) return 'teal';
    if (score >= 60) return 'amber';
    return 'red';
  };

  const statusOrder = [
    'ready',
    'approved',
    'application_opened',
    'applied',
    'screening',
    'interview',
    'offer',
    'rejected',
    'withdrawn'
  ];

  const sortedApps = [...applications].sort((a, b) => {
    const aIdx = statusOrder.indexOf(a.status);
    const bIdx = statusOrder.indexOf(b.status);
    if (aIdx !== bIdx) return aIdx - bIdx;
    return (b.match_score || 0) - (a.match_score || 0);
  });

  return (
    <Layout title="Applications" breadcrumb={<Link href="/applications">Applications</Link>}>
      <div className="page-head">
        <h1>Application Queue</h1>
        <div className="muted">Review, approve, and track your job applications.</div>
      </div>

      {/* Stats */}
      <div className="grid stats" style={{ marginBottom: 16 }}>
        {Object.entries(stats).filter(([_, v]) => v > 0).map(([status, count]) => (
          <div key={status} className="panel stat-card">
            <div className="stat-label">{status.replace('_', ' ')}</div>
            <div className="stat-value">{count}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex" style={{ gap: 16, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="flex" style={{ gap: 8 }}>
          {['', 'ready', 'approved', 'application_opened', 'applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn'].map(s => (
            <Button
              key={s}
              variant={statusFilter === s ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => { setStatusFilter(s); setPage(1); }}
            >
              {s || 'All'}
            </Button>
          ))}
        </div>
      </div>

      {/* Applications List */}
      <Panel title={`Applications (${total})`}>
        {loading ? (
          <Spinner />
        ) : sortedApps.length === 0 ? (
          <Empty message="No applications yet. Import jobs and run matches to build your queue." />
        ) : (
          <div className="applications-list">
            {sortedApps.map((app) => (
              <div key={app.id} className="panel app-card" style={{ marginBottom: 12 }}>
                <div className="flex justify-between" style={{ marginBottom: 8 }}>
                  <div>
                    <h3 style={{ fontSize: 16, marginBottom: 4 }}>{app.job?.title || 'Unknown Position'}</h3>
                    <div className="muted">{app.job?.company_name || 'Unknown Company'}</div>
                  </div>
                  <div className="flex" style={{ alignItems: 'center', gap: 12 }}>
                    {app.match_score !== null && (
                      <div className="flex" style={{ alignItems: 'center', gap: 8 }}>
                        <span className="muted" style={{ fontSize: 13 }}>Match:</span>
                        <Progress percent={app.match_score} style={{ width: 80 }} />
                        <span className="badge" style={{ background: `var(--${getScoreColor(app.match_score)})` }}>{app.match_score}%</span>
                      </div>
                    )}
                    <StatusBadge status={app.status.replace('_', ' ')} />
                  </div>
                </div>

                {app.job && (
                  <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
                    {app.job.location && `${Icons.search} ${app.job.location}`}
                    {app.job.remote_type && ` · ${app.job.remote_type}`}
                    {app.job.employment_type && ` · ${app.job.employment_type}`}
                    {app.job.salary_min && app.job.salary_max && ` · $${app.job.salary_min.toLocaleString()} - $${app.job.salary_max.toLocaleString()}`}
                  </div>
                )}

                <div className="flex justify-between" style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <Link href={`/applications/${app.id}`} className="btn sm secondary">View Details</Link>
                  <div className="flex" style={{ gap: 8 }}>
                    {getStatusActions(app).map((action) => (
                      <Button
                        key={action.type}
                        size="sm"
                        variant={action.variant}
                        onClick={() => handleAction(app, action.type)}
                        disabled={actionLoading}
                      >
                        {action.label}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {total > pageSize && (
          <div className="flex justify-between mt-16">
            <Button variant="secondary" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
              {Icons.up} Prev
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= total}>
              Next {Icons.up}
            </Button>
          </div>
        )}
      </Panel>
    </Layout>
  );
}