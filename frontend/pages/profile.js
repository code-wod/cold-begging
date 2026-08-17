import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  Button, Confirm, Empty, Field, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, fmtDate, useToast,
} from '../components/ui';

const EMPTY_FORM = {
  provider: 'smtp', email: '', display_name: '', app_password: '',
  smtp_host: 'smtp.gmail.com', smtp_port: 465, smtp_secure: true, smtp_username: '',
};

export default function Profile() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [accounts, setAccounts] = useState([]);
  const [form, setForm] = useState({ full_name: '', avatar_url: '' });
  const [busy, setBusy] = useState(false);
  const [smtpOpen, setSmtpOpen] = useState(false);
  const [smtpForm, setSmtpForm] = useState(EMPTY_FORM);
  const [testingId, setTestingId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  useEffect(() => {
    if (user) setForm({ full_name: user.full_name || '', avatar_url: user.avatar_url || '' });
    api('/api/email-accounts').then(setAccounts).catch(() => {});
  }, [user?.id]);

  const save = async () => {
    setBusy(true);
    try {
      const updated = await api('/api/auth/profile', { method: 'PATCH', body: form });
      setUser(updated);
      toast('Profile updated', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const connectGoogle = async () => {
    try {
      const res = await api('/api/email-accounts/connect');
      window.location.href = res.authorize_url;
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const addSmtp = async () => {
    try {
      await api('/api/email-accounts', { method: 'POST', body: smtpForm });
      setSmtpOpen(false);
      setSmtpForm(EMPTY_FORM);
      toast('SMTP account added', 'success');
      api('/api/email-accounts').then(setAccounts).catch(() => {});
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const setDefault = async (a) => {
    setBusyId(a.id);
    try {
      await api(`/api/email-accounts/${a.id}/default`, { method: 'POST' });
      toast(`Default sending account set to ${a.email}`, 'success');
      api('/api/email-accounts').then(setAccounts).catch(() => {});
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBusyId(null);
    }
  };

  const testConnection = async (a) => {
    setTestingId(a.id);
    try {
      const res = await api(`/api/email-accounts/${a.id}/test`, { method: 'POST' });
      toast(res.message || 'Connection verified', 'success');
      api('/api/email-accounts').then(setAccounts).catch(() => {});
    } catch (e) {
      toast(e.message, 'error');
      api('/api/email-accounts').then(setAccounts).catch(() => {});
    } finally {
      setTestingId(null);
    }
  };

  const doDisconnect = async () => {
    try {
      await api(`/api/email-accounts/${confirmDisconnect.id}/disconnect`, { method: 'POST' });
      toast('Account disconnected', 'success');
      setConfirmDisconnect(null);
      api('/api/email-accounts').then(setAccounts).catch(() => {});
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/email-accounts/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Account deleted', 'success');
      setConfirmDelete(null);
      api('/api/email-accounts').then(setAccounts).catch(() => {});
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  if (!user) {
    return (
      <Layout title="Profile">
        <Spinner />
      </Layout>
    );
  }

  const connected = accounts.find((a) => a.status === 'connected');

  return (
    <Layout title="Profile" breadcrumb={<span>Profile</span>}>
      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' }}>
        <Panel title="Edit profile">
          <div className="flex mb-16">
            <span className="avatar" style={{ width: 48, height: 48, fontSize: 18 }}>
              {(form.full_name || user.email).slice(0, 2).toUpperCase()}
            </span>
            <div>
              <div style={{ fontWeight: 600 }}>{user.full_name || user.email}</div>
              <div className="muted">{user.email}</div>
            </div>
          </div>
          <Field label="Name">
            <Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Your name" />
          </Field>
          <Field label="Avatar URL (optional)">
            <Input value={form.avatar_url} onChange={(e) => setForm({ ...form, avatar_url: e.target.value })} placeholder="https://…/avatar.png" />
          </Field>
          <Button disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save changes'}</Button>
        </Panel>

        <Panel title="Account details">
          <table className="dense">
            <tbody>
              <tr><td className="muted">Email</td><td>{user.email}</td></tr>
              <tr><td className="muted">Email verified</td><td>{user.is_verified ? 'Yes' : 'No (verification not required in this build)'}</td></tr>
              <tr><td className="muted">Plan</td><td><StatusBadge status={user.plan === 'pro' ? 'Pro' : 'Free'} tone={user.plan === 'pro' ? 'green' : 'gray'} /></td></tr>
              <tr><td className="muted">Account created</td><td>{fmtDate(user.created_at)}</td></tr>
              <tr><td className="muted">Default sender</td><td>{accounts.find((a) => a.is_default)?.email || <span className="muted">None</span>}</td></tr>
            </tbody>
          </table>
          <div className="mt-16">
            <Link href="/billing" className="btn secondary sm">Manage billing</Link>
          </div>
        </Panel>
      </div>

      <div style={{ marginTop: 16 }}>
        <Panel title="Email Accounts"
          actions={
            <div className="flex" style={{ gap: 8 }}>
              <Button sm onClick={connectGoogle}>{Icons.google} Connect Google / Gmail</Button>
              <Button sm variant="secondary" onClick={() => setSmtpOpen(true)}>{Icons.plus} Add SMTP</Button>
            </div>
          }>
        <div className="muted mb-16">
          Emails are sent from the account you pick, never from a shared project address. Every account below
          is private to your user.
        </div>
        {accounts.length === 0 ? (
          <Empty message="No sending accounts yet. Connect your Gmail or add an SMTP account." />
        ) : (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 12 }}>
            {accounts.map((a) => (
              <div key={a.id} className="panel" style={{ padding: 14 }}>
                <div className="flex" style={{ justifyContent: 'space-between', marginBottom: 6 }}>
                  <b>{a.email}</b>
                  {a.is_default && <StatusBadge status="Default" tone="blue" />}
                </div>
                <div className="muted" style={{ marginBottom: 10 }}>
                  {a.provider === 'google' ? 'Gmail / Google (OAuth)' : `SMTP · ${a.smtp_host}:${a.smtp_port}`} ·{' '}
                  {a.status === 'connected' ? <StatusBadge status="Connected" tone="green" /> : <StatusBadge status={a.status} tone="gray" />}
                </div>
                <div className="flex" style={{ gap: 6, flexWrap: 'wrap' }}>
                  <Button sm variant="secondary" disabled={testingId === a.id} onClick={() => testConnection(a)}>
                    {testingId === a.id ? <Spinner /> : Icons.check} Test
                  </Button>
                  {!a.is_default && (
                    <Button sm variant="secondary" disabled={busyId === a.id} onClick={() => setDefault(a)}>
                      Set default
                    </Button>
                  )}
                  {a.status === 'connected' && (
                    <Button sm variant="secondary" onClick={() => setConfirmDisconnect(a)}>{Icons.x} Disconnect</Button>
                  )}
                  <Button sm variant="danger" onClick={() => setConfirmDelete(a)}>{Icons.trash} Delete</Button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="mt-16">
          <Link href="/email-accounts" className="btn secondary sm">Open full Email Accounts page</Link>
        </div>
        </Panel>
      </div>

      <Modal open={smtpOpen} title="Add SMTP account" onClose={() => setSmtpOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSmtpOpen(false)}>Cancel</Button>
            <Button onClick={addSmtp}>Connect</Button>
          </>
        }>
        <Field label="Email">
          <Input type="email" required value={smtpForm.email} onChange={(e) => setSmtpForm({ ...smtpForm, email: e.target.value })} placeholder="you@example.com" />
        </Field>
        <Field label="Display name (optional)">
          <Input value={smtpForm.display_name} onChange={(e) => setSmtpForm({ ...smtpForm, display_name: e.target.value })} placeholder="Your Name" />
        </Field>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="SMTP host">
            <Input value={smtpForm.smtp_host} onChange={(e) => setSmtpForm({ ...smtpForm, smtp_host: e.target.value })} placeholder="smtp.gmail.com" />
          </Field>
          <Field label="Port">
            <Input type="number" value={smtpForm.smtp_port} onChange={(e) => setSmtpForm({ ...smtpForm, smtp_port: Number(e.target.value) })} />
          </Field>
        </div>
        <Field label="Connection">
          <Select value={smtpForm.smtp_secure ? 'ssl' : 'tls'} onChange={(e) => setSmtpForm({ ...smtpForm, smtp_secure: e.target.value === 'ssl' })}>
            <option value="ssl">SSL/TLS (implicit, port 465)</option>
            <option value="tls">STARTTLS (port 587)</option>
          </Select>
        </Field>
        <Field label="SMTP username (optional)" help="Defaults to the email above.">
          <Input value={smtpForm.smtp_username} onChange={(e) => setSmtpForm({ ...smtpForm, smtp_username: e.target.value })} />
        </Field>
        <Field label="Password / app password" help="Stored encrypted on the server.">
          <Input type="password" required value={smtpForm.app_password} onChange={(e) => setSmtpForm({ ...smtpForm, app_password: e.target.value })} placeholder="password" />
        </Field>
      </Modal>

      <Confirm open={!!confirmDisconnect} title="Disconnect account" danger
        message={`Disconnect ${confirmDisconnect?.email}? Its credentials will be removed. You can reconnect later.`}
        confirmLabel="Disconnect" onCancel={() => setConfirmDisconnect(null)} onConfirm={doDisconnect} />

      <Confirm open={!!confirmDelete} title="Delete account" danger
        message={`Delete ${confirmDelete?.email}? This removes the account permanently. Emails already sent stay in your history.`}
        confirmLabel="Delete" onCancel={() => setConfirmDelete(null)} onConfirm={doDelete} />
    </Layout>
  );
}