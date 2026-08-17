import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Panel, Spinner, StatusBadge, useToast, Icons } from '../components/ui';

export default function Settings() {
  const { user } = useAuth();
  const toast = useToast();
  const [accounts, setAccounts] = useState(null);

  useEffect(() => {
    api('/api/email-accounts').then(setAccounts).catch((e) => toast(e.message, 'error'));
  }, []);

  if (!user || !accounts) {
    return (
      <Layout title="Settings">
        <Spinner />
      </Layout>
    );
  }

  const groups = [
    {
      title: 'Automation',
      items: [
        ['Email Accounts', 'Connect Gmail or SMTP accounts used for sending.', '/email-accounts', 'email'],
        ['AI Agents', 'Create and configure your AI agents.', '/ai-agents', 'agents'],
        ['AI Models', 'Manage provider API keys and the managed model.', '/ai-models', 'settings'],
        ['Recipients', 'Manage your recipient database.', '/recipients', 'recipients'],
      ],
    },
    {
      title: 'Account',
      items: [
        ['Profile', 'Your name, email and avatar.', '/profile', 'profile'],
        ['Billing', 'Plan, usage and invoices.', '/billing', 'billing'],
      ],
    },
  ];

  return (
    <Layout title="Settings" breadcrumb={<span>Settings</span>}>
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', alignItems: 'start' }}>
        {groups.map((g) => (
          <div key={g.title}>
            <div className="sidebar-section" style={{ color: 'var(--muted)', padding: '0 0 8px' }}>{g.title}</div>
            <div className="panel">
              {g.items.map(([title, desc, href, icon]) => (
                <Link key={href} href={href}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px', borderBottom: '1px solid var(--border)', color: 'var(--text)' }}
                    className="hover">
                    {Icons[icon]}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600 }}>{title}</div>
                      <div className="muted" style={{ fontSize: 12.5 }}>{desc}</div>
                    </div>
                    <span className="muted">›</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>

      <Panel title="Connection status" className="mt-16">
        <table className="dense">
          <thead><tr><th>Account</th><th>Provider</th><th>Status</th></tr></thead>
          <tbody>
            {accounts.length === 0 && (
              <tr><td colSpan={3} className="muted">No email accounts connected. <Link href="/email-accounts">Connect one</Link>.</td></tr>
            )}
            {accounts.map((a) => (
              <tr key={a.id}>
                <td><b>{a.email}</b></td>
                <td>{a.provider === 'google' ? 'Google OAuth' : 'SMTP'}</td>
                <td>
                  <StatusBadge status={a.status} tone={a.status === 'connected' ? 'green' : a.status === 'disconnected' ? 'gray' : 'red'} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </Layout>
  );
}