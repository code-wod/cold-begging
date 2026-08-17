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
    ])
      .then(([analytics, campaigns, rc, accounts, billing, history, upcoming, models]) =>
        setData({ analytics, campaigns, rc, accounts, billing, history, upcoming, models })
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

  const { analytics, campaigns, rc, accounts, billing, history, upcoming, models } = data;
  const connected = accounts.find((a) => a.status === 'connected');
  const scheduled = campaigns.filter((c) => ['scheduled', 'running'].includes(c.status)).length;
  const hasModel = models.length > 0;
  const aiReady = user.plan === 'pro' || hasModel;
  const rateLimit = billing.limits?.emails_per_hour || 10;

  return (
    <Layout title="Dashboard" breadcrumb={<Link href="/dashboard">Dashboard</Link>}>
      <div className="page-head">
        <h1>Welcome back{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}</h1>
        <div className="muted">Overview of your outreach automation workspace.</div>
      </div>

      <div className="grid stats">
        <div className="panel stat-card">
          <div className="stat-label">Emails Sent</div>
          <div className="stat-value">{analytics.emails_sent}</div>
          <div className="muted" style={{ fontSize: 12 }}>Failed: {analytics.emails_failed}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Sending Speed</div>
          <div className="stat-value">{rateLimit}/hr</div>
          <div className="muted" style={{ fontSize: 12 }}>{user.plan === 'pro' ? 'Pro limit' : 'Free limit'}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Recipients</div>
          <div className="stat-value">{rc.count}</div>
          <Link href="/recipients" className="muted" style={{ fontSize: 12 }}>Manage →</Link>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Campaigns</div>
          <div className="stat-value">{analytics.campaigns}</div>
          <Link href="/campaigns" className="muted" style={{ fontSize: 12 }}>View all →</Link>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 320px', marginTop: 16 }}>
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
                      <td style={{ minWidth: 160 }}>
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
          <Panel title="Environment">
            <div className="field" style={{ marginBottom: 10 }}>
              <div className="label">Plan</div>
              <StatusBadge status={user.plan === 'pro' ? 'Pro' : 'Free'} tone={user.plan === 'pro' ? 'green' : 'gray'} />
              {user.plan === 'free' && (
                <div className="help"><Link href="/billing">Upgrade to Pro</Link> for higher sending speed and the managed AI model.</div>
              )}
            </div>
            <div className="field" style={{ marginBottom: 10 }}>
              <div className="label">Gmail</div>
              {connected ? (
                <StatusBadge status={`Connected · ${connected.email}`} tone="green" />
              ) : (
                <>
                  <StatusBadge status="Not connected" tone="red" />
                  <div className="help"><Link href="/email-accounts">Connect your Gmail account</Link> to send emails.</div>
                </>
              )}
            </div>
            <div className="field" style={{ marginBottom: 10 }}>
              <div className="label">AI</div>
              {aiReady ? (
                <StatusBadge status={user.plan === 'pro' ? 'Managed model (Pro)' : `${models.length} model(s) configured`} tone="green" />
              ) : (
                <>
                  <StatusBadge status="No AI model" tone="red" />
                  <div className="help"><Link href="/ai-models">Add your own AI model</Link> or upgrade to Pro for the managed model.</div>
                </>
              )}
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <div className="label">AI usage</div>
              <div className="flex" style={{ justifyContent: 'space-between' }}>
                <span className="muted">AI generations</span>
                <b>{billing.ai_generation} / {billing.limits.ai_generation}</b>
              </div>
              <div className="progress mt-8">
                <div style={{ width: `${Math.min(100, (billing.ai_generation / billing.limits.ai_generation) * 100)}%` }} />
              </div>
              <div className="flex mt-8" style={{ justifyContent: 'space-between' }}>
                <span className="muted">Emails processed</span>
                <b>{billing.email_sent} / {billing.limits.email_sent}</b>
              </div>
              <div className="progress mt-8">
                <div style={{ width: `${Math.min(100, (billing.email_sent / billing.limits.email_sent) * 100)}%` }} />
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