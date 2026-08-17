import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  Button, Confirm, Empty, Field, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, fmtDate, useToast,
} from '../components/ui';

const EMPTY_MODEL = {
  name: '', provider: 'gemini', model: '', api_key: '', base_url: '',
  temperature: 0.7, max_tokens: 1000, price_usd: 0,
};

const PROVIDER_LABELS = {
  openai: 'OpenAI / compatible',
  anthropic: 'Anthropic (Claude)',
  gemini: 'Google Gemini',
};

const providerOptions = Object.entries(PROVIDER_LABELS).map(([value, label]) => ({ value, label }));

export default function Admin() {
  const toast = useToast();
  const router = useRouter();
  const { user } = useAuth();
  const [tab, setTab] = useState('models');
  const [models, setModels] = useState(null);
  const [users, setUsers] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_MODEL);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    if (user && !user.is_admin) router.replace('/dashboard');
  }, [user]);

  const loadModels = () => {
    api('/api/admin/models').then(setModels).catch((e) => toast(e.message, 'error'));
  };
  const loadUsers = () => {
    api('/api/admin/users').then(setUsers).catch((e) => toast(e.message, 'error'));
  };
  useEffect(() => {
    loadModels();
    loadUsers();
  }, []);

  if (!user || !user.is_admin) return null;

  const openCreate = () => { setEditing(null); setForm(EMPTY_MODEL); setModalOpen(true); };
  const openEdit = (m) => {
    setEditing(m);
    setForm({ ...EMPTY_MODEL, ...m, api_key: '' });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      if (editing) {
        await api(`/api/admin/models/${editing.id}`, { method: 'PATCH', body: form });
        toast('Platform model updated', 'success');
      } else {
        await api('/api/admin/models', { method: 'POST', body: form });
        toast('Platform model added', 'success');
      }
      setModalOpen(false);
      loadModels();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/admin/models/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Platform model deleted', 'success');
      setConfirmDelete(null);
      loadModels();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const testConnection = async (m) => {
    setTestingId(m.id);
    try {
      const res = await api(`/api/admin/models/${m.id}/test`, { method: 'POST' });
      toast(res.message || 'Connection verified', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setTestingId(null);
    }
  };

  const setPlan = async (u, plan) => {
    setBusyId(`plan-${u.id}`);
    try {
      await api(`/api/admin/users/${u.id}/plan`, { method: 'PATCH', body: { plan } });
      toast(`${u.email} is now on ${plan}`, 'success');
      loadUsers();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBusyId(null);
    }
  };

  const toggleAdmin = async (u) => {
    setBusyId(`role-${u.id}`);
    try {
      await api(`/api/admin/users/${u.id}/role`, { method: 'PATCH', body: { is_admin: !u.is_admin } });
      toast(`${u.email} is ${u.is_admin ? 'no longer' : 'now'} an admin`, 'success');
      loadUsers();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Layout title="Admin" breadcrumb={<span>Admin</span>}>
      <div className="page-head">
        <h1>Admin</h1>
        <div className="muted">
          Platform AI models (with pricing) and user management. Changes apply instantly and persist.
        </div>
      </div>

      <div className="toolbar">
        {(['models', 'users']).map((t) => (
          <Button key={t} variant={tab === t ? 'primary' : 'secondary'} onClick={() => setTab(t)}>
            {t === 'models' ? 'AI Models' : 'Users'}
          </Button>
        ))}
        {tab === 'models' && <Button onClick={openCreate}>{Icons.plus} Add platform model</Button>}
      </div>

      {tab === 'models' && (
        <Panel title="Platform AI Models">
          <div className="muted mb-16">
            Free models (price 0) are shown to all users in the campaign and AI Agents — no user API key needed.
            Paid models (price &gt; 0) are visible only to Pro users. Credentials are encrypted at rest.
          </div>
          {models === null ? (
            <Spinner />
          ) : models.length === 0 ? (
            <Empty message="No platform models yet. Add one so free users can generate emails without their own API key." />
          ) : (
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))' }}>
              {models.map((m) => (
                <Panel key={m.id} title={m.name}
                  actions={m.price_usd === 0 ? <StatusBadge status="Free" tone="green" /> : <StatusBadge status={`$${m.price_usd} / Pro`} tone="amber" />}>
                  <table className="dense" style={{ margin: '6px 0' }}>
                    <tbody>
                      <tr><td className="muted">Provider</td><td>{PROVIDER_LABELS[m.provider] || m.provider}</td></tr>
                      <tr><td className="muted">Model</td><td><b>{m.model}</b></td></tr>
                      <tr><td className="muted">Pricing</td><td>{m.price_usd === 0 ? 'Free for all users' : `$${m.price_usd}/mo · Pro only`}</td></tr>
                      <tr><td className="muted">API key</td><td>{m.has_api_key ? '•••••••• (encrypted)' : 'Not set'}</td></tr>
                      {m.base_url && <tr><td className="muted">Base URL</td><td>{m.base_url}</td></tr>}
                      <tr><td className="muted">Added</td><td>{fmtDate(m.created_at)}</td></tr>
                    </tbody>
                  </table>
                  <div className="flex" style={{ gap: 8 }}>
                    <Button variant="secondary" sm disabled={testingId === m.id} onClick={() => testConnection(m)}>
                      {testingId === m.id ? <Spinner /> : Icons.check} Test
                    </Button>
                    <Button variant="secondary" sm onClick={() => openEdit(m)}>{Icons.edit} Edit</Button>
                    <Button variant="danger" sm onClick={() => setConfirmDelete(m)}>{Icons.trash} Delete</Button>
                  </div>
                </Panel>
              ))}
            </div>
          )}
        </Panel>
      )}

      {tab === 'users' && (
        <Panel title="Users">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Plan</th>
                <th>Role</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users === null ? (
                <tr><td colSpan={4}><Spinner /></td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={4} className="muted">No users</td></tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <b>{u.full_name || u.email}</b>
                      <div className="muted">{u.email} · joined {fmtDate(u.created_at)}</div>
                    </td>
                    <td>
                      <Select
                        value={u.plan}
                        disabled={busyId === `plan-${u.id}`}
                        onChange={(e) => setPlan(u, e.target.value)}
                        style={{ width: 110 }}>
                        <option value="free">Free</option>
                        <option value="pro">Pro</option>
                      </Select>
                    </td>
                    <td>{u.is_admin ? <StatusBadge status="Admin" tone="blue" /> : <StatusBadge status="User" tone="gray" />}</td>
                    <td style={{ textAlign: 'right' }}>
                      <Button variant="secondary" sm disabled={busyId === `role-${u.id}`} onClick={() => toggleAdmin(u)}>
                        {u.is_admin ? 'Revoke admin' : 'Make admin'}
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </Panel>
      )}

      <Modal open={modalOpen} title={editing ? 'Edit platform model' : 'Add platform model'} onClose={() => setModalOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={save}>{editing ? 'Save changes' : 'Add model'}</Button>
          </>
        }>
        <Field label="Name">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="PulseBoard Free Gemini" />
        </Field>
        <Field label="AI provider">
          <Select options={providerOptions} value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} />
        </Field>
        <Field label="Model">
          <Input required value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="gemini-3.5-flash-lite" />
        </Field>
        <Field label="API key (platform credential)" help={editing ? 'Leave blank to keep the existing key.' : 'Stored encrypted. Used for all users of this model.'}>
          <Input type="password" required={!editing} value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="sk-..." />
        </Field>
        <Field label="Base URL (optional)">
          <Input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder="https://api.openai.com/v1" />
        </Field>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Temperature">
            <Input type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} />
          </Field>
          <Field label="Max tokens">
            <Input type="number" min="1" value={form.max_tokens} onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })} />
          </Field>
        </div>
        <label className="flex" style={{ fontSize: 13.5 }}>
          <input type="checkbox" checked={form.price_usd === 0} onChange={(e) => setForm({ ...form, price_usd: e.target.checked ? 0 : 49 })} />
          Free for all users
        </label>
        {form.price_usd > 0 && (
          <Field label="Price (USD / month)" help="Paid platform models are Pro-only.">
            <Input type="number" min="0" value={form.price_usd} onChange={(e) => setForm({ ...form, price_usd: Number(e.target.value) })} />
          </Field>
        )}
      </Modal>

      <Confirm open={!!confirmDelete} title="Delete platform model" danger
        message={`Delete "${confirmDelete?.name}"? This removes it for every user.`}
        confirmLabel="Delete" onCancel={() => setConfirmDelete(null)} onConfirm={doDelete} />
    </Layout>
  );
}