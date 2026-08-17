import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import {
  Button, Confirm, Empty, Field, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, TextArea, useToast,
} from '../components/ui';

const EMPTY_AGENT = {
  name: '', description: '', purpose: '', ai_model_id: null,
  system_prompt: '', temperature: 0.7, max_tokens: 1000, status: 'active',
};

const AGENT_PRESETS = [
  {
    label: 'Job Outreach Agent',
    value: {
      name: 'Job Outreach Agent',
      purpose: 'Generate personalized job opportunity emails that attract talent.',
      system_prompt:
        'Write a short, personalized, professional-but-conversational email for a job opportunity. Never mention salary first. Focus on the company, a specific value proposition, and a low-friction CTA. Format exactly as SUBJECT: ... then BODY: ...',
    },
  },
  {
    label: 'Company Research Agent',
    value: {
      name: 'Company Research Agent',
      purpose: 'Research a company profile (pain points, growth stage, culture).',
      system_prompt:
        'Given a company name and website, provide ONLY a JSON profile with company_pain_points, growth_stage, target_for_hiring, company_culture, key_keywords.',
    },
  },
  {
    label: 'Email Writer',
    value: {
      name: 'Email Writer',
      purpose: 'Write compelling cold outreach emails for any offer.',
      system_prompt:
        'Write a clear, persuasive cold email with a strong subject line, 3-4 short paragraphs, and a clear call to action. Format exactly as SUBJECT: ... then BODY: ...',
    },
  },
];

export default function AIAgents() {
  const toast = useToast();
  const [agents, setAgents] = useState(null);
  const [models, setModels] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_AGENT);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = () => {
    api('/api/ai-agents').then(setAgents).catch((e) => toast(e.message, 'error'));
    api('/api/ai-models').then(setModels).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_AGENT);
    setModalOpen(true);
  };

  const openEdit = (agent) => {
    setEditing(agent);
    setForm({
      name: agent.name, description: agent.description, purpose: agent.purpose,
      ai_model_id: agent.ai_model_id, system_prompt: agent.system_prompt,
      temperature: agent.temperature, max_tokens: agent.max_tokens, status: agent.status,
    });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      if (editing) {
        await api(`/api/ai-agents/${editing.id}`, { method: 'PUT', body: form });
        toast('Agent updated', 'success');
      } else {
        await api('/api/ai-agents', { method: 'POST', body: form });
        toast('Agent created', 'success');
      }
      setModalOpen(false);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const act = async (path, msg) => {
    try {
      await api(path, { method: 'POST' });
      toast(msg, 'success');
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/ai-agents/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Agent deleted', 'success');
      setConfirmDelete(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  return (
    <Layout title="AI Agents" breadcrumb={<span>AI Agents</span>}>
      <div className="page-head">
        <h1>AI Agents</h1>
        <div className="muted">
          Agents combine a purpose, a system prompt and a model. Create multiple agents for outreach, research and follow-ups.
        </div>
      </div>

      <div className="toolbar">
        <Button onClick={openCreate}>{Icons.plus} New Agent</Button>
      </div>

      {agents === null ? (
        <Spinner />
      ) : agents.length === 0 ? (
        <Panel>
          <Empty message="No AI agents yet. Create your first agent to generate emails." />
        </Panel>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))' }}>
          {agents.map((a) => (
            <Panel key={a.id} title={a.name}
              actions={a.status === 'active' ? <StatusBadge status="Active" tone="green" /> : <StatusBadge status="Disabled" tone="gray" />}>
              <p className="muted" style={{ marginTop: 0 }}>{a.purpose || a.description || '—'}</p>
              <table className="dense" style={{ margin: '8px 0' }}>
                <tbody>
                  <tr><td className="muted">Model</td><td><b>{a.model_name || '—'}</b></td></tr>
                  <tr><td className="muted">Temperature</td><td>{a.temperature}</td></tr>
                  <tr><td className="muted">Max tokens</td><td>{a.max_tokens}</td></tr>
                  {a.is_default && <tr><td className="muted">Default</td><td><StatusBadge status="default agent" tone="blue" /></td></tr>}
                </tbody>
              </table>
              <div className="flex">
                <Button variant="secondary" sm onClick={() => openEdit(a)}>{Icons.edit} Edit</Button>
                <Button variant="secondary" sm onClick={() => act(`/api/ai-agents/${a.id}/duplicate`, 'Agent duplicated')}>{Icons.duplicate} Duplicate</Button>
                <Button variant="secondary" sm onClick={() => act(`/api/ai-agents/${a.id}/toggle`, a.status === 'active' ? 'Agent disabled' : 'Agent enabled')}>
                  {Icons.refresh} {a.status === 'active' ? 'Disable' : 'Enable'}
                </Button>
                <Button variant="secondary" sm onClick={() => setConfirmDelete(a)}>{Icons.trash}</Button>
              </div>
            </Panel>
          ))}
        </div>
      )}

      <Panel title="Templates" className="mt-16">
        <div className="landing-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
          {AGENT_PRESETS.map((p) => (
            <div key={p.label} className="feature-card" style={{ border: '1px solid var(--border)' }}>
              <h4 style={{ margin: 0 }}>{p.label}</h4>
              <p className="muted" style={{ margin: '6px 0 12px' }}>{p.value.purpose}</p>
              <Button variant="secondary" sm onClick={() => { setForm(p.value); setEditing(null); setModalOpen(true); }}>
                {Icons.plus} Use template
              </Button>
            </div>
          ))}
        </div>
      </Panel>

      <Modal open={modalOpen} title={editing ? 'Edit agent' : 'New AI agent'} onClose={() => setModalOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={save}>{editing ? 'Save changes' : 'Create agent'}</Button>
          </>
        }>
        <Field label="Agent name">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Job Outreach Agent" />
        </Field>
        <Field label="Purpose" help="What this agent does. Shown to you when picking an agent.">
          <Input value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} placeholder="Generate personalized job opportunity emails" />
        </Field>
        <Field label="Description">
          <TextArea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="AI model" help="Free platform models need no API key on your side.">
          <Select value={form.ai_model_id || ''} onChange={(e) => setForm({ ...form, ai_model_id: e.target.value ? Number(e.target.value) : null })}>
            <option value="">Default model</option>
            {models.map((m) => (
              <option key={m.id} value={m.id}>{m.name} ({m.model}){m.is_platform && m.price_usd === 0 ? ' · Free' : m.is_platform ? ' · Pro' : ''}</option>
            ))}
          </Select>
        </Field>
        <Field label="System prompt" help="Instructions that shape how the agent writes. Keep it concise.">
          <TextArea rows={4} value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} placeholder="Write a short, personalized..." />
        </Field>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Temperature" help="Lower = more deterministic.">
            <Input type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} />
          </Field>
          <Field label="Max tokens">
            <Input type="number" min="1" value={form.max_tokens} onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })} />
          </Field>
        </div>
      </Modal>

      <Confirm open={!!confirmDelete} title="Delete agent" danger
        message={`Delete "${confirmDelete?.name}"? Existing generated emails are not affected.`}
        confirmLabel="Delete" onCancel={() => setConfirmDelete(null)} onConfirm={doDelete} />
    </Layout>
  );
}