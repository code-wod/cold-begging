import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import {
  Button, Confirm, Empty, Field, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, fmtDate, useToast,
} from '../components/ui';

const EMPTY_FORM = {
  provider: 'smtp', email: '', display_name: '', app_password: '',
  smtp_host: 'smtp.gmail.com', smtp_port: 465, smtp_secure: true, smtp_username: '',
};

export default function EmailAccounts() {
  const toast = useToast();
  const router = useRouter();
  const [accounts, setAccounts] = useState(null);
  const [smtpOpen, setSmtpOpen] = useState(false);
  const [editAccount, setEditAccount] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [connectBusy, setConnectBusy] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    if (router.query.connected === '1') toast('Gmail account connected', 'success');
    if (router.query.oauth_error === '1') toast('OAuth connection failed or was cancelled', 'error');
    router.replace('/email-accounts', undefined, { shallow: true });
  }, [router.query]);

  const load = () => {
    api('/api/email-accounts').then(setAccounts).catch((e) => toast(e.message, 'error'));
  };
  useEffect(() => { load(); }, []);

  const connectGoogle = async () => {
    setConnectBusy(true);
    try {
      const res = await api('/api/email-accounts/connect');
      window.location.href = res.authorize_url;
    } catch (e) {
      toast(e.message, 'error');
      setConnectBusy(false);
    }
  };

  const addSmtp = async () => {
    try {
      await api('/api/email-accounts', { method: 'POST', body: form });
      setSmtpOpen(false);
      setForm(EMPTY_FORM);
      toast('SMTP account added', 'success');
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const saveEdit = async () => {
    try {
      const body = { ...editAccount };
      delete body.id; delete body.status; delete body.created_at; delete body.is_default;
      await api(`/api/email-accounts/${editAccount.id}`, { method: 'PATCH', body });
      toast('Account updated', 'success');
      setEditAccount(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDisconnect = async () => {
    try {
      await api(`/api/email-accounts/${confirmDisconnect.id}/disconnect`, { method: 'POST' });
      toast('Account disconnected', 'success');
      setConfirmDisconnect(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/email-accounts/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Account deleted', 'success');
      setConfirmDelete(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const setDefault = async (a) => {
    setBusyId(a.id);
    try {
      await api(`/api/email-accounts/${a.id}/default`, { method: 'POST' });
      toast(`Default sending account set to ${a.email}`, 'success');
      load();
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
      load();
    } catch (e) {
      toast(e.message, 'error');
      load();
    } finally {
      setTestingId(null);
    }
  };

  return (
    <Layout title="Email Accounts" breadcrumb={<span>Email Accounts</span>}>
      <div className="page-head">
        <h1>Email Accounts</h1>
        <div className="muted">
          Connect your Gmail or SMTP accounts to send emails from your own address. Gmail uses Google's
          OAuth flow — we never ask for or store your Gmail password.
        </div>
      </div>

      <div className="toolbar">
        <Button disabled={connectBusy} onClick={connectGoogle}>
          {connectBusy ? <Spinner /> : Icons.google} Connect Google / Gmail
        </Button>
        <Button variant="secondary" onClick={() => setSmtpOpen(true)}>
          {Icons.plus} Add SMTP
        </Button>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))' }}>
        {accounts === null ? (
          <Spinner />
        ) : accounts.length === 0 ? (
          <Panel>
            <Empty message="No email accounts connected yet. Connect your Gmail to start sending." />
          </Panel>
        ) : (
          accounts.map((a) => (
            <Panel key={a.id} title={
              <span className="flex">
                {a.provider === 'google' ? Icons.google : Icons.email} {a.email}
                {a.is_default && <StatusBadge status="Default" tone="blue" />}
              </span>
            }
              actions={
                a.status === 'connected' ? (
                  <StatusBadge status="Connected" tone="green" />
                ) : (
                  <StatusBadge status={a.status} tone={a.status === 'disconnected' ? 'gray' : 'red'} />
                )
              }>
              <div className="field">
                <div className="label">Provider</div>
                <span className="muted">
                  {a.provider === 'google' ? 'Google (OAuth)' : 'SMTP'}
                  {a.provider === 'smtp' && ` · ${a.smtp_host}:${a.smtp_port}${a.smtp_secure ? ' (SSL/TLS)' : ''}`}
                </span>
              </div>
              {a.display_name && (
                <div className="field">
                  <div className="label">Display name</div>
                  <span className="muted">{a.display_name}</span>
                </div>
              )}
              <div className="field">
                <div className="label">Added</div>
                <span className="muted">{fmtDate(a.created_at)}</span>
              </div>
              <div className="flex" style={{ gap: 8, flexWrap: 'wrap' }}>
                <Button variant="secondary" sm disabled={testingId === a.id} onClick={() => testConnection(a)}>
                  {testingId === a.id ? <Spinner /> : Icons.check} Test
                </Button>
                {!a.is_default && (
                  <Button variant="secondary" sm disabled={busyId === a.id} onClick={() => setDefault(a)}>
                    {busyId === a.id ? <Spinner /> : Icons.check} Set as default
                  </Button>
                )}
                {a.provider === 'smtp' && (
                  <Button variant="secondary" sm onClick={() => setEditAccount(a)}>{Icons.edit} Edit</Button>
                )}
                {a.status === 'connected' && (
                  <Button variant="secondary" sm onClick={() => setConfirmDisconnect(a)}>
                    {Icons.x} Disconnect
                  </Button>
                )}
                <Button variant="danger" sm onClick={() => setConfirmDelete(a)}>
                  {Icons.trash} Delete
                </Button>
              </div>
            </Panel>
          ))
        )}
      </div>

      <Modal open={smtpOpen} title="Add SMTP account" onClose={() => setSmtpOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSmtpOpen(false)}>Cancel</Button>
            <Button onClick={addSmtp}>Connect</Button>
          </>
        }>
        <p className="muted mb-16" style={{ marginTop: -6 }}>
          For Gmail use an <b>app password</b> (Settings → Security → App passwords). Never your regular password.
        </p>
        <Field label="Email">
          <Input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" />
        </Field>
        <Field label="Display name (optional)">
          <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} placeholder="Your Name" />
        </Field>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="SMTP host" help="Default: smtp.gmail.com">
            <Input value={form.smtp_host} onChange={(e) => setForm({ ...form, smtp_host: e.target.value })} placeholder="smtp.gmail.com" />
          </Field>
          <Field label="Port">
            <Input type="number" value={form.smtp_port} onChange={(e) => setForm({ ...form, smtp_port: Number(e.target.value) })} placeholder="465" />
          </Field>
        </div>
        <Field label="Connection">
          <Select value={form.smtp_secure ? 'ssl' : 'tls'} onChange={(e) => setForm({ ...form, smtp_secure: e.target.value === 'ssl' })}>
            <option value="ssl">SSL/TLS (implicit, port 465)</option>
            <option value="tls">STARTTLS (port 587)</option>
          </Select>
        </Field>
        <Field label="SMTP username (optional)" help="Defaults to the email above.">
          <Input value={form.smtp_username} onChange={(e) => setForm({ ...form, smtp_username: e.target.value })} placeholder={form.email || 'you@example.com'} />
        </Field>
        <Field label="Password / app password" help="Stored encrypted on the server.">
          <Input type="password" required value={form.app_password} onChange={(e) => setForm({ ...form, app_password: e.target.value })} placeholder="password" />
        </Field>
      </Modal>

      <Modal open={!!editAccount} title="Edit SMTP account" onClose={() => setEditAccount(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditAccount(null)}>Cancel</Button>
            <Button onClick={saveEdit}>Save</Button>
          </>
        }>
        <Field label="Email">
          <Input type="email" required value={editAccount?.email || ''} onChange={(e) => setEditAccount({ ...editAccount, email: e.target.value })} />
        </Field>
        <Field label="Display name (optional)">
          <Input value={editAccount?.display_name || ''} onChange={(e) => setEditAccount({ ...editAccount, display_name: e.target.value })} />
        </Field>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="SMTP host">
            <Input value={editAccount?.smtp_host || ''} onChange={(e) => setEditAccount({ ...editAccount, smtp_host: e.target.value })} />
          </Field>
          <Field label="Port">
            <Input type="number" value={editAccount?.smtp_port || ''} onChange={(e) => setEditAccount({ ...editAccount, smtp_port: Number(e.target.value) })} />
          </Field>
        </div>
        <Field label="Connection">
          <Select value={editAccount?.smtp_secure ? 'ssl' : 'tls'} onChange={(e) => setEditAccount({ ...editAccount, smtp_secure: e.target.value === 'ssl' })}>
            <option value="ssl">SSL/TLS (implicit, port 465)</option>
            <option value="tls">STARTTLS (port 587)</option>
          </Select>
        </Field>
        <Field label="SMTP username (optional)">
          <Input value={editAccount?.smtp_username || ''} onChange={(e) => setEditAccount({ ...editAccount, smtp_username: e.target.value })} />
        </Field>
        <Field label="New password / app password (optional)" help="Leave blank to keep the current one. Stored encrypted.">
          <Input type="password" value={editAccount?.app_password || ''} onChange={(e) => setEditAccount({ ...editAccount, app_password: e.target.value })} />
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