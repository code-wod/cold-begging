import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { Panel, Spinner, StatusBadge, useToast, Icons } from '../components/ui';

export default function Onboarding() {
  const toast = useToast();
  const [state, setState] = useState(null);

  useEffect(() => {
    Promise.all([
      api('/api/email-accounts'),
      api('/api/recipients/count'),
      api('/api/ai-agents'),
      api('/api/campaigns'),
    ])
      .then(([accounts, rc, agents, campaigns]) =>
        setState({
          gmail: accounts.filter((a) => a.status === 'connected').length > 0,
          recipients: rc.count > 0,
          ai: agents.length > 0,
          campaign: campaigns.length > 0,
        })
      )
      .catch((e) => toast(e.message, 'error'));
  }, []);

  if (!state) {
    return (
      <Layout title="Get started">
        <Spinner />
      </Layout>
    );
  }

  const steps = [
    { n: 1, name: 'Account', done: true, href: '/profile', desc: 'Your account is ready.' },
    { n: 2, name: 'Gmail', done: state.gmail, href: '/email-accounts', desc: 'Connect your Gmail to send from your own address.' },
    { n: 3, name: 'Recipients', done: state.recipients, href: '/recipients', desc: 'Import your recipient list (Excel / CSV) or add manually.' },
    { n: 4, name: 'AI', done: state.ai, href: '/ai-agents', desc: 'Create an AI agent and pick a model (your key or managed).' },
    { n: 5, name: 'Campaign', done: state.campaign, href: '/campaigns/new', desc: 'Create your first campaign and generate emails.' },
  ];

  return (
    <Layout title="Get started" breadcrumb={<Link href="/dashboard">Dashboard</Link>}>
      <div className="page-head">
        <h1>Set up your workspace</h1>
        <div className="muted">Complete each step — optional steps can be skipped and finished later.</div>
      </div>

      <div className="wizard-steps" style={{ marginBottom: 24 }}>
        {steps.map((s) => (
          <span key={s.n} className={`wizard-step ${s.done ? 'done' : ''}`}>
            {s.n}. {s.name}
          </span>
        ))}
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        {steps.map((s) => (
          <Panel key={s.n} title={`Step ${s.n} — ${s.name}`}
            actions={s.done ? <StatusBadge status="Done" tone="green" /> : <StatusBadge status="Pending" tone="gray" />}>
            <p className="muted">{s.desc}</p>
            <Link href={s.href} className="btn secondary sm" style={{ marginTop: 8 }}>
              {s.done ? 'Open' : s.n === 1 ? 'View' : 'Complete'} <span style={{ transform: 'rotate(90deg)', display: 'inline-flex' }}>{Icons.up}</span>
            </Link>
          </Panel>
        ))}
      </div>

      {state.gmail && state.recipients && state.ai && (
        <div className="panel mt-16" style={{ padding: 18, borderColor: 'var(--success-soft-border)', background: 'var(--success-soft-bg)' }}>
          <strong>You're ready to launch. 🎉</strong>
          <p className="muted mb-8">Everything is set up. Create your first campaign now.</p>
          <Link href="/campaigns/new" className="btn">Create Campaign</Link>
        </div>
      )}
    </Layout>
  );
}