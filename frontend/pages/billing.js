import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import CreditPurchase from '../components/CreditPurchase';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Button, Empty, Panel, Spinner, StatusBadge, fmtDate, useToast, Progress } from '../components/ui';

export default function Billing() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [usage, setUsage] = useState(null);
  const [sub, setSub] = useState(null);
  const [credits, setCredits] = useState(null);
  const [payments, setPayments] = useState(null);

  const load = () => {
    api('/api/billing').then(setUsage).catch((e) => toast(e.message, 'error'));
    api('/api/billing/subscription').then(setSub).catch((e) => toast(e.message, 'error'));
    api('/api/email-credits').then(setCredits).catch((e) => toast(e.message, 'error'));
    api('/api/billing/payment-history').then(setPayments).catch((e) => toast(e.message, 'error'));
  };
  useEffect(() => { load(); }, []);

  const handlePurchased = async (result) => {
    setCredits((prev) => prev ? { ...prev, remaining: result.new_balance } : prev);
    toast(`${result.credits_added} credits added!`, 'success');
    // Refresh everything — plan may have changed
    load();
    api('/api/auth/me').then(setUser).catch(() => {});
  };

  if (!usage || !sub || !credits || !payments) {
    return (
      <Layout title="Billing">
        <Spinner />
      </Layout>
    );
  }

  return (
    <Layout title="Billing" breadcrumb={<span>Billing</span>}>
      {/* Hero Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: 16,
        padding: '32px 40px',
        color: '#fff',
        marginBottom: 24,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 800, margin: 0 }}>
              {credits.remaining} credits remaining
            </h1>
            <p style={{ margin: '8px 0 0', opacity: 0.85, fontSize: 15 }}>
              {sub.plan === 'pro'
                ? 'Pro plan active — send up to 1,199 emails/month.'
                : 'Free plan — buy credits to start sending cold emails.'}
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{
              display: 'inline-block',
              padding: '6px 16px',
              borderRadius: 20,
              background: sub.plan === 'pro' ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.1)',
              fontSize: 14,
              fontWeight: 600,
            }}>
              {sub.plan === 'pro' ? '⭐ Pro' : 'Free'}
            </div>
            {sub.plan === 'pro' && sub.renews_at && (
              <div style={{ fontSize: 12, opacity: 0.7, marginTop: 6 }}>
                Renews {fmtDate(sub.renews_at)}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 340px', gap: 16, alignItems: 'start' }}>
        <div>
          {/* Plans */}
          <Panel title="Choose a plan" style={{ marginBottom: 16 }}>
            <p className="muted" style={{ margin: '0 0 16px', fontSize: 13 }}>
              Start sending cold emails today. All plans include AI-powered personalization.
            </p>
            <CreditPurchase onPurchased={handlePurchased} />
          </Panel>

          {/* What's included */}
          <Panel title="What's included" style={{ marginBottom: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                { icon: '✉️', title: 'AI-Personalized Emails', desc: 'Each email tailored to the recipient' },
                { icon: '📊', title: 'Campaign Analytics', desc: 'Track opens, clicks, and replies' },
                { icon: '🤖', title: 'AI Agent Support', desc: 'Smart follow-ups and scheduling' },
                { icon: '⚡', title: 'Instant Delivery', desc: 'Emails sent via your Gmail account' },
              ].map((item) => (
                <div key={item.title} style={{
                  display: 'flex', gap: 12, padding: '12px 0',
                  borderBottom: '1px solid var(--border)',
                }}>
                  <span style={{ fontSize: 24 }}>{item.icon}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{item.title}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          {/* Payment History */}
          <Panel title="Payment History">
            {payments.payments.length === 0 ? (
              <Empty message="No payments yet. Purchase a plan to get started." />
            ) : (
              <table className="dense" style={{ width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left' }}>Date</th>
                    <th style={{ textAlign: 'left' }}>Description</th>
                    <th style={{ textAlign: 'right' }}>Amount</th>
                    <th style={{ textAlign: 'right' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.payments.map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontSize: 13 }}>{fmtDate(p.created_at)}</td>
                      <td style={{ fontSize: 13 }}>{p.description}</td>
                      <td style={{ textAlign: 'right', fontSize: 13, fontWeight: 600 }}>
                        {p.type === 'PURCHASE' ? `₹${Math.abs(p.amount / 100)}` : `₹${Math.abs(p.amount / 100)}`}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <StatusBadge
                          status={p.status}
                          tone={p.status === 'completed' ? 'green' : 'amber'}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        </div>

        <div>
          {/* Balance Card */}
          <div style={{
            background: 'var(--panel)',
            border: '2px solid var(--border)',
            borderRadius: 12,
            padding: 24,
            textAlign: 'center',
            marginBottom: 16,
          }}>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 4 }}>Email Credits</div>
            <div style={{ fontSize: 48, fontWeight: 800, color: '#6366f1', lineHeight: 1 }}>
              {credits.remaining}
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>
              Free: {credits.free_credits} · Purchased: {credits.purchased_credits}
            </div>
            <div style={{
              marginTop: 16,
              padding: '8px 0',
              background: credits.remaining > 0 ? '#10b98115' : '#f4433615',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              color: credits.remaining > 0 ? '#10b981' : '#f44336',
            }}>
              {credits.remaining > 0 ? '✓ Active' : '⚠ No credits'}
            </div>
          </div>

          {/* Quick Stats */}
          <Panel title="Quick stats">
            <table className="dense" style={{ width: '100%' }}>
              <tbody>
                <tr>
                  <td className="muted">Plan</td>
                  <td style={{ fontWeight: 600 }}>{sub.plan === 'pro' ? 'Pro' : 'Free'}</td>
                </tr>
                <tr>
                  <td className="muted">Status</td>
                  <td>
                    <StatusBadge status={sub.status} tone={sub.status === 'active' ? 'green' : 'amber'} />
                  </td>
                </tr>
                <tr>
                  <td className="muted">Emails/hour</td>
                  <td>{usage.limits.emails_per_hour}</td>
                </tr>
                <tr>
                  <td className="muted">Email limit</td>
                  <td>{sub.plan === 'pro' ? '1,199/mo' : '200 one-time'}</td>
                </tr>
                <tr>
                  <td className="muted">Started</td>
                  <td>{fmtDate(sub.started_at)}</td>
                </tr>
                {sub.renews_at && (
                  <tr>
                    <td className="muted">Renews</td>
                    <td>{fmtDate(sub.renews_at)}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </Panel>

          {/* FAQ */}
          <Panel title="FAQ" style={{ marginTop: 16 }}>
            {[
              { q: 'What happens when credits run out?', a: 'Buy more credits to continue sending.' },
              { q: 'Do unused credits expire?', a: 'One-time credits never expire. Monthly credits expire with the plan.' },
              { q: 'Can I get a refund?', a: 'Contact support within 7 days for a full refund.' },
            ].map((item) => (
              <div key={item.q} style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{item.q}</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{item.a}</div>
              </div>
            ))}
          </Panel>
        </div>
      </div>
    </Layout>
  );
}
