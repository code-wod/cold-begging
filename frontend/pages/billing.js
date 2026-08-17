import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Button, Empty, Panel, Spinner, StatusBadge, fmtDate, useToast, Progress } from '../components/ui';

export default function Billing() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [usage, setUsage] = useState(null);
  const [sub, setSub] = useState(null);

  const load = () => {
    api('/api/billing').then(setUsage).catch((e) => toast(e.message, 'error'));
    api('/api/billing/subscription').then(setSub).catch((e) => toast(e.message, 'error'));
  };
  useEffect(() => { load(); }, []);

  const change = async (action) => {
    try {
      await api(`/api/billing/${action}`, { method: 'POST' });
      toast(action === 'upgrade' ? 'Upgraded to Pro' : 'Downgraded to Free', 'success');
      load();
      api('/api/auth/me').then(setUser).catch(() => {});
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  if (!usage || !sub) {
    return (
      <Layout title="Billing">
        <Spinner />
      </Layout>
    );
  }

  const bars = [
    ['AI Generation', usage.ai_generation, usage.limits.ai_generation],
    ['Emails Processed', usage.email_sent, usage.limits.email_sent],
  ];

  return (
    <Layout title="Billing" breadcrumb={<span>Billing</span>}>
      <div className="grid" style={{ gridTemplateColumns: '2fr 1fr', gap: 16, alignItems: 'start' }}>
        <div>
          <Panel title="Current plan">
            <div className="justify-between">
              <div>
                <div className="flex">
                  <h2 style={{ fontSize: 22 }}>{sub.plan === 'pro' ? 'Pro' : 'Free'}</h2>
                  <StatusBadge status={sub.status} tone={sub.status === 'active' ? 'green' : 'amber'} />
                </div>
                <div className="muted">
                  {sub.plan === 'pro'
                    ? `Renews ${fmtDate(sub.renews_at)}`
                    : 'Free plan — connect your own Gmail and AI key.'}
                </div>
              </div>
              <div>
                {sub.plan === 'free' ? (
                  <Button onClick={() => change('upgrade')}>Upgrade to Pro</Button>
                ) : (
                  <Button variant="secondary" onClick={() => change('downgrade')}>Downgrade to Free</Button>
                )}
              </div>
            </div>
            <div className="mt-16" style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
              <h3 style={{ fontSize: 15, marginBottom: 6 }}>What you get</h3>
              {sub.plan === 'pro' ? (
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>Managed default AI model (no API key needed)</li>
                  <li>Sending speed up to {usage.limits.emails_per_hour} emails/hour</li>
                  <li>Multiple AI agents</li>
                  <li>Advanced scheduling & window controls</li>
                  <li>Higher AI usage limits</li>
                  <li>Campaign analytics & email history</li>
                </ul>
              ) : (
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>Connect your own Gmail (OAuth or app password)</li>
                  <li>Import recipients from Excel / CSV</li>
                  <li>Use your own AI API key</li>
                  <li>Sending speed up to {usage.limits.emails_per_hour} emails/hour</li>
                  <li>Email preview, editing, manual sending</li>
                  <li>Basic campaigns</li>
                </ul>
              )}
            </div>
            <div className="mt-16" style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
              <h3 style={{ fontSize: 15, marginBottom: 6 }}>How billing works</h3>
              <p className="muted" style={{ margin: 0 }}>
                Plans are rate-based. Free users can send up to <b>{usage.limits.emails_per_hour} emails/hour</b> from
                their own Gmail with their own AI key. Pro raises the hourly sending speed to{' '}
                <b>{sub.plan === 'pro' ? usage.limits.emails_per_hour : '50'} emails/hour</b>, adds the managed AI model,
                and lifts usage caps. Email sending speed is enforced by the server, not just the UI.
              </p>
            </div>
          </Panel>

          <Panel title="Usage" className="mt-16">
            {bars.map(([label, used, limit]) => (
              <div key={label} className="field">
                <div className="flex" style={{ justifyContent: 'space-between' }}>
                  <span className="label">{label}</span>
                  <b>{used} / {limit}</b>
                </div>
                <Progress percent={(used / limit) * 100} />
              </div>
            ))}
            <div className="field">
              <div className="flex" style={{ justifyContent: 'space-between' }}>
                <span className="label">Sending Speed</span>
                <b>{usage.limits.emails_per_hour} emails/hour</b>
              </div>
              <div className="muted" style={{ fontSize: 12 }}>
                One email every {Math.round(3600 / usage.limits.emails_per_hour)}s on average
              </div>
            </div>
          </Panel>
        </div>

        <div>
          <Panel title="Payment method">
            <Empty message="No payment method on file. This build simulates billing — no card is charged." />
          </Panel>
          <Panel title="Invoices" className="mt-16">
            <Empty message="No invoices yet." />
          </Panel>
          <Panel title="Billing cycle" className="mt-16">
            <table className="dense">
              <tbody>
                <tr><td className="muted">Started</td><td>{fmtDate(sub.started_at)}</td></tr>
                <tr><td className="muted">Renews</td><td>{fmtDate(sub.renews_at)}</td></tr>
              </tbody>
            </table>
          </Panel>
        </div>
      </div>
    </Layout>
  );
}