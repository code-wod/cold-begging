import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  Button, Confirm, Empty, Field, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, useToast,
} from '../components/ui';

const EMPTY_MODEL = {
  name: '', provider: 'openai', model: '', api_key: '', base_url: '',
  temperature: 0.7, max_tokens: 1000, is_default: false,
};

export default function AIModels() {
  const toast = useToast();
  const { user } = useAuth();
  const [models, setModels] = useState(null);
  const [managed, setManaged] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_MODEL);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [testingId, setTestingId] = useState(null);

  const load = () => {
    api('/api/ai-models').then(setModels).catch((e) => toast(e.message, 'error'));
    api('/api/ai-models/available').then(setManaged).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); setForm(EMPTY_MODEL); setModalOpen(true); };
  const openEdit = (m) => {
    setEditing(m);
    setForm({ ...EMPTY_MODEL, ...m, api_key: '' });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      if (editing) {
        await api(`/api/ai-models/${editing.id}`, { method: 'PUT', body: form });
        toast('Model updated', 'success');
      } else {
        await api('/api/ai-models', { method: 'POST', body: form });
        toast('Model added', 'success');
      }
      setModalOpen(false);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/ai-models/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Model deleted', 'success');
      setConfirmDelete(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const testConnection = async (m) => {
    setTestingId(m.id);
    try {
      const res = await api(`/api/ai-models/${m.id}/test`, { method: 'POST' });
      toast(res.message || 'Connection verified', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setTestingId(null);
    }
  };

  const providerOptions = [
    { value: 'openai', label: 'OpenAI / compatible' },
    { value: 'anthropic', label: 'Anthropic (Claude)' },
    { value: 'gemini', label: 'Google Gemini' },
  ];

  const PROVIDER_LABELS = {
    openai: 'OpenAI / compatible',
    anthropic: 'Anthropic (Claude)',
    gemini: 'Google Gemini',
  };

  return (
    <Layout title="AI Models" breadcrumb={<span>AI Models</span>}>
      <div className="page-head">
        <h1>AI Models</h1>
        <div className="muted">
          Bring your own provider API keys, use a free platform model (no key needed), or upgrade to Pro for the
          platform-managed model. Keys are encrypted and never sent to your browser. <b>You are responsible for
          usage charges</b> from your own AI provider.
        </div>
      </div>

      <div className="toolbar">
        <Button onClick={openCreate}>{Icons.plus} Add Model</Button>
      </div>

      {managed && (
        <Panel title="Default AI Model" className="mb-16"
          actions={managed.managed_available ? <StatusBadge status="Available" tone="green" /> : <StatusBadge status="Pro only" tone="amber" />}>
          <div className="flex" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="stat-label">Managed by PulseBoard</div>
              <b style={{ fontSize: 16 }}>{managed.managed.name}</b>
              <div className="muted">Model: {managed.managed.model}</div>
            </div>
            {managed.managed_available ? (
              <div className="muted">Included in your Pro plan.</div>
            ) : (
              <div style={{ textAlign: 'right' }}>
                <div className="muted mb-8">This feature requires a paid plan.</div>
                <Link href="/billing" className="btn sm">{Icons.up} Upgrade Plan</Link>
              </div>
            )}
          </div>
        </Panel>
      )}

      {models === null ? (
        <Spinner />
      ) : models.length === 0 ? (
        <Panel>
          <Empty message="No models configured yet. Add an OpenAI or Anthropic API key to generate emails." />
        </Panel>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))' }}>
          {models.map((m) => (
            <Panel key={m.id} title={m.name}
              actions={
                m.is_platform ? (
                  m.price_usd === 0 ? <StatusBadge status="Free (platform)" tone="green" /> : <StatusBadge status="Pro (platform)" tone="amber" />
                ) : m.is_default ? (
                  <StatusBadge status="Default" tone="blue" />
                ) : (
                  <StatusBadge status={m.provider} tone="gray" />
                )
              }>
              <table className="dense" style={{ margin: '6px 0' }}>
                <tbody>
                  <tr><td className="muted">Provider</td><td>{PROVIDER_LABELS[m.provider] || m.provider}</td></tr>
                  <tr><td className="muted">Model</td><td><b>{m.model}</b></td></tr>
                  <tr><td className="muted">Temperature</td><td>{m.temperature}</td></tr>
                  <tr><td className="muted">Max tokens</td><td>{m.max_tokens}</td></tr>
                  <tr><td className="muted">API key</td><td>{m.has_api_key ? '•••••••• (encrypted)' : 'Not set'}</td></tr>
                  {m.base_url && <tr><td className="muted">Base URL</td><td>{m.base_url}</td></tr>}
                  {m.is_platform && (
                    <tr><td className="muted">Pricing</td><td>{m.price_usd === 0 ? 'Free for all users' : `$${m.price_usd}/mo · Pro only`}</td></tr>
                  )}
                </tbody>
              </table>
              <div className="flex">
                <Button variant="secondary" sm disabled={testingId === m.id} onClick={() => testConnection(m)}>
                  {testingId === m.id ? <Spinner /> : Icons.check} Test
                </Button>
                {!m.is_platform && (
                  <>
                    <Button variant="secondary" sm onClick={() => openEdit(m)}>{Icons.edit} Edit</Button>
                    <Button variant="secondary" sm onClick={() => setConfirmDelete(m)}>{Icons.trash}</Button>
                  </>
                )}
              </div>
            </Panel>
          ))}
        </div>
      )}

      <Modal open={modalOpen} title={editing ? 'Edit model' : 'Add AI model'} onClose={() => setModalOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={save}>{editing ? 'Save changes' : 'Add model'}</Button>
          </>
        }>
        <Field label="Name">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My OpenAI key" />
        </Field>
        <Field label="AI provider">
          <Select options={providerOptions} value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} />
        </Field>
        <Field label="Model"
            help={form.provider === 'anthropic' ? 'e.g. claude-3-5-sonnet' : form.provider === 'gemini' ? 'e.g. gemini-2.5-flash' : 'e.g. gpt-4o or any OpenAI-compatible model'}>
          <Input required value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="gpt-4o" />
        </Field>
        <Field label="API key" help={editing ? 'Leave blank to keep the existing key.' : 'Stored encrypted. Never sent to the browser.'}>
          <Input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="sk-..." />
        </Field>
        <Field label="Base URL (optional)" help="For OpenAI-compatible providers.">
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
          <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
          Set as default model
        </label>
      </Modal>

      <Confirm open={!!confirmDelete} title="Delete model" danger
        message={`Delete "${confirmDelete?.name}"? Agents using it will fall back to the default.`}
        confirmLabel="Delete" onCancel={() => setConfirmDelete(null)} onConfirm={doDelete} />
    </Layout>
  );
}