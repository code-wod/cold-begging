import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, fmtDate, useToast, Icons } from '../components/ui';

export default function Dashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const [data, setData] = useState(null);

  useEffect(() => {
    Promise.all([
      api('/api/analytics'),
      api('/api/campaigns'),
      api('/api/recipients/count'),
      api('/api/email-accounts'),
      api('/api/billing'),
      api('/api/emails/history?limit=8'),
      api('/api/emails/history?status=scheduled&limit=6'),
      api('/api/ai-models'),
      api('/api/email-credits'),
    ])
      .then(([analytics, campaigns, rc, accounts, billing, history, upcoming, models, credits]) =>
        setData({ analytics, campaigns, rc, accounts, billing, history, upcoming, models, credits })
      )
      .catch((e) => toast(e.message, 'error'));
  }, []);

  if (!data) {
    return (
      <Layout title="Dashboard">
        <Spinner />
      </Layout>
    );
  }

  const { analytics, campaigns, rc, accounts, billing, history, upcoming, models, credits } = data;
  const connected = accounts.find((a) => a.status === 'connected');
  const scheduled = campaigns.filter((c) => ['scheduled', 'running'].includes(c.status)).length;
  const hasModel = models.length > 0;
  const aiReady = user.plan === 'pro' || hasModel;
  const rateLimit = billing.limits?.emails_per_hour || 10;

  const isPro = user.plan === 'pro';

  return (
    <Layout title="Dashboard" breadcrumb={<Link href="/dashboard">Dashboard</Link>}>
      <div className="page-head">
        <div className="flex" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Welcome back{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}</h1>
            <div className="muted">Overview of your outreach automation workspace.</div>
          </div>
          <div className="plan-badge-wrap">
            {isPro ? (
              <Link href="/billing" className="plan-badge plan-badge-pro">
                <span className="plan-badge-icon">&#9733;</span>
                <span>Pro Plan</span>
              </Link>
            ) : (
              <Link href="/billing" className="plan-badge plan-badge-free">
                <span>Free Plan</span>
                <span className="plan-badge-arrow">&rarr;</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="grid stats">
        <div className="panel stat-card">
          <div className="stat-card-icon" style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: '#fff', width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
            {Icons.email}
          </div>
          <div className="stat-label">Emails Sent</div>
          <div className="stat-value">{analytics.emails_sent}</div>
          <div className="muted" style={{ fontSize: 12 }}>Failed: {analytics.emails_failed}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-card-icon" style={{ background: 'linear-gradient(135deg, #8b5cf6, #6366f1)', color: '#fff', width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
            {Icons.analytics}
          </div>
          <div className="stat-label">Sending Speed</div>
          <div className="stat-value">{rateLimit}/hr</div>
          <div className="muted" style={{ fontSize: 12 }}>{isPro ? 'Pro limit' : 'Free limit'}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-card-icon" style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
            {Icons.recipients}
          </div>
          <div className="stat-label">Recipients</div>
          <div className="stat-value">{rc.count}</div>
          <Link href="/recipients" className="muted" style={{ fontSize: 12 }}>Manage &rarr;</Link>
        </div>
        <div className="panel stat-card">
          <div className="stat-card-icon" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', color: '#fff', width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
            {Icons.campaigns}
          </div>
          <div className="stat-label">Campaigns</div>
          <div className="stat-value">{analytics.campaigns}</div>
          <Link href="/campaigns" className="muted" style={{ fontSize: 12 }}>View all &rarr;</Link>
        </div>
        <div className="panel stat-card">
          <div className="stat-card-icon" style={{ background: 'linear-gradient(135deg, #ec4899, #d946ef)', color: '#fff', width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
            {Icons.billing}
          </div>
          <div className="stat-label">Email Credits</div>
          <div className="stat-value">{credits?.remaining ?? '—'}</div>
          <Link href="/billing" className="muted" style={{ fontSize: 12 }}>Buy more &rarr;</Link>
        </div>
      </div>

      <div className="grid dashboard-grid" style={{ marginTop: 16 }}>
        <Panel title="Recent campaigns" actions={<Link href="/campaigns/new" className="btn sm">{Icons.plus} New</Link>}>
          {campaigns.length === 0 ? (
            <Empty message="No campaigns yet. Create your first campaign to get started." />
          ) : (
            <table className="dense">
              <thead>
                <tr><th>Name</th><th>Status</th><th>Progress</th><th>Created</th></tr>
              </thead>
              <tbody>
                {campaigns.slice(0, 6).map((c) => {
                  const done = c.sent_count + c.failed_count;
                  const total = c.generated_count || 1;
                  return (
                    <tr key={c.id}>
                      <td><Link href={`/campaigns/${c.id}`}>{c.name}</Link></td>
                      <td><StatusBadge status={c.status} /></td>
                      <td style={{ minWidth: 120, maxWidth: 180 }}>
                        <div className="flex">
                          <div className="progress" style={{ flex: 1 }}><div style={{ width: `${(done / total) * 100}%` }} /></div>
                          <span className="muted">{done}/{total}</span>
                        </div>
                      </td>
                      <td className="muted">{fmtDate(c.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Panel>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Panel title="Quick setup">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
                <span style={{ width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, background: isPro ? 'linear-gradient(135deg, #f59e0b, #f97316)' : 'var(--badge-gray-bg)', color: isPro ? '#fff' : 'var(--muted)', flexShrink: 0 }}>{isPro ? '\u2713' : '1'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>Plan</div>
                  <div className="muted" style={{ fontSize: 12 }}>{isPro ? 'Pro — unlimited speed' : 'Free — upgrade for more'}</div>
                </div>
                {!isPro && <Link href="/billing" className="btn sm secondary">Upgrade</Link>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
                <span style={{ width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, background: connected ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--badge-gray-bg)', color: connected ? '#fff' : 'var(--muted)', flexShrink: 0 }}>{connected ? '\u2713' : '2'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>Email Account</div>
                  <div className="muted" style={{ fontSize: 12 }}>{connected ? connected.email : 'Connect Gmail or SMTP'}</div>
                </div>
                {!connected && <Link href="/email-accounts" className="btn sm secondary">Connect</Link>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
                <span style={{ width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, background: aiReady ? 'linear-gradient(135deg, #8b5cf6, #6366f1)' : 'var(--badge-gray-bg)', color: aiReady ? '#fff' : 'var(--muted)', flexShrink: 0 }}>{aiReady ? '\u2713' : '3'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>AI Model</div>
                  <div className="muted" style={{ fontSize: 12 }}>{aiReady ? (isPro ? 'Managed model' : `${models.length} model(s)`) : 'Add an AI model'}</div>
                </div>
                {!aiReady && <Link href="/ai-models" className="btn sm secondary">Add</Link>}
              </div>
            </div>
          </Panel>

          <Panel title="Upcoming sends" actions={<Link href="/history" className="muted" style={{ fontSize: 12 }}>History →</Link>}>
            {upcoming.items.length === 0 ? (
              <div className="empty" style={{ padding: 24 }}>Nothing queued right now.</div>
            ) : (
              <table className="dense">
                <tbody>
                  {upcoming.items.map((h) => (
                    <tr key={h.id}>
                      <td>
                        <div>{h.recipient}</div>
                        <div className="muted" style={{ fontSize: 12 }}>{h.subject?.slice(0, 42) || '—'}</div>
                      </td>
                      <td className="muted" style={{ whiteSpace: 'nowrap' }}>{fmtDate(h.scheduled_at || h.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>

          <Panel title="Recent activity">
            {history.items.length === 0 ? (
              <div className="empty" style={{ padding: 24 }}>No email activity yet.</div>
            ) : (
              <table className="dense">
                <tbody>
                  {history.items.map((h) => (
                    <tr key={h.id}>
                      <td>
                        <div>{h.recipient}</div>
                        <div className="muted" style={{ fontSize: 12 }}>{h.subject?.slice(0, 42) || '—'}</div>
                      </td>
                      <td><StatusBadge status={h.status} tone={h.status === 'sent' ? 'green' : h.status === 'failed' ? 'red' : 'gray'} /></td>
                      <td className="muted" style={{ whiteSpace: 'nowrap' }}>{fmtDate(h.sent_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        </div>
      </div>
    </Layout>
  );
}