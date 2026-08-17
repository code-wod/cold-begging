import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { Button, Field, Icons, Input, Panel, Select, StatusBadge, TextArea, useToast } from '../../components/ui';

const STEPS = [
  'Campaign Details', 'Recipients', 'AI Agent', 'Sending Account', 'Schedule', 'Review',
];

const DAYS = [
  ['Monday', 0], ['Tuesday', 1], ['Wednesday', 2], ['Thursday', 3], ['Friday', 4], ['Saturday', 5], ['Sunday', 6],
];

export default function NewCampaign() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [recipients, setRecipients] = useState([]);
  const [agents, setAgents] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [billing, setBilling] = useState(null);
  const [form, setForm] = useState({
    name: '', tone: 'professional', subject_style: 'personalized', email_length: 'medium',
    custom_prompt: '', use_company_research: true, review_required: true, dry_run: true,
    agent_id: null, email_account_id: null,
    send_start_time: '09:00', send_end_time: '17:00', active_days: [0, 1, 2, 3, 4],
    emails_per_hour: 10, delay_seconds: 0, daily_limit: 0, max_sends: 0, timezone: 'UTC', start_at: '', end_at: '',
  });
  const [selectedIds, setSelectedIds] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api('/api/recipients?limit=500').then(setRecipients).catch((e) => toast(e.message, 'error'));
    api('/api/ai-agents').then(setAgents).catch((e) => toast(e.message, 'error'));
    api('/api/email-accounts')
      .then((list) => {
        setAccounts(list);
        setForm((f) => {
          if (f.email_account_id) return f;
          const def = list.find((a) => a.is_default && a.status === 'connected') || list.find((a) => a.status === 'connected');
          return def ? { ...f, email_account_id: def.id } : f;
        });
      })
      .catch((e) => toast(e.message, 'error'));
    api('/api/billing').then(setBilling).catch(() => {});
  }, []);

  const plan = billing?.plan || 'free';
  const planRateLimit = billing?.limits?.emails_per_hour || 10;
  const isPro = plan === 'pro';
  const maxRate = Math.max(planRateLimit, 4);

  const intervalText = (rate) => {
    const secs = Math.max(1, Math.round(3600 / (rate || 10)));
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return s ? `${m}m ${s}s` : `${m}m`;
  };

  const toggleDay = (d) =>
    setForm((f) => ({
      ...f,
      active_days: f.active_days.includes(d) ? f.active_days.filter((x) => x !== d) : [...f.active_days, d],
    }));

  const toggleRecipient = (id) =>
    setSelectedIds((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const canNext =
    (step !== 0 || form.name.trim()) &&
    (step !== 1 || selectedIds.length > 0) &&
    (step !== 2 || form.agent_id) &&
    (step !== 3 || form.email_account_id);

  const create = async () => {
    setBusy(true);
    try {
      const payload = { ...form, recipient_ids: selectedIds };
      if (!payload.start_at) payload.start_at = null;
      if (!payload.end_at) payload.end_at = null;
      const campaign = await api('/api/campaigns', { method: 'POST', body: payload });
      toast('Campaign created', 'success');
      router.push(`/campaigns/${campaign.id}`);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const selected = agents.find((a) => a.id === form.agent_id);
  const account = accounts.find((a) => a.id === form.email_account_id);

  return (
    <Layout title="Create Campaign" breadcrumb={<><Link href="/campaigns">Campaigns</Link> / New</>}>
      <div className="wizard-steps">
        {STEPS.map((s, i) => (
          <span key={s} className={`wizard-step ${i < step ? 'done' : ''} ${i === step ? 'active' : ''}`}>
            {i + 1}. {s}
          </span>
        ))}
      </div>

      <Panel title={STEPS[step]} bodyClassName="panel-body">
        {step === 0 && (
          <>
            <Field label="Campaign name" help="A clear name you'll recognize later.">
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Software Engineering Outreach" />
            </Field>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <Field label="Tone">
                <Select options={['professional', 'conversational', 'friendly', 'formal']} value={form.tone} onChange={(e) => setForm({ ...form, tone: e.target.value })} />
              </Field>
              <Field label="Subject style">
                <Select options={['personalized', 'curiosity', 'benefit']} value={form.subject_style} onChange={(e) => setForm({ ...form, subject_style: e.target.value })} />
              </Field>
              <Field label="Email length">
                <Select options={['short', 'medium', 'long']} value={form.email_length} onChange={(e) => setForm({ ...form, email_length: e.target.value })} />
              </Field>
            </div>
            <Field label="Company research" help="Research each company profile before writing the email.">
              <Select options={[{ value: 'true', label: 'Enabled (better personalization)' }, { value: 'false', label: 'Disabled (faster)' }]}
                value={String(form.use_company_research)} onChange={(e) => setForm({ ...form, use_company_research: e.target.value === 'true' })} />
            </Field>
            <Field label="Custom AI prompt (optional)" help="Extra instructions for the agent, e.g. 'mention product-market fit'.">
              <TextArea rows={3} value={form.custom_prompt} onChange={(e) => setForm({ ...form, custom_prompt: e.target.value })} />
            </Field>
            <div className="flex">
              <label className="flex" style={{ fontSize: 13.5 }}>
                <input type="checkbox" checked={form.review_required} onChange={(e) => setForm({ ...form, review_required: e.target.checked })} />
                Review emails before sending
              </label>
              <label className="flex" style={{ fontSize: 13.5 }}>
                <input type="checkbox" checked={form.dry_run} onChange={(e) => setForm({ ...form, dry_run: e.target.checked })} />
                Dry run (generate without sending)
              </label>
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <p className="muted">Select recipients for this campaign. <b>{selectedIds.length}</b> selected.</p>
            <div style={{ maxHeight: 360, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 6 }}>
              <table className="dense">
                <thead><tr><th></th><th>Email</th><th>Company</th><th>Industry</th></tr></thead>
                <tbody>
                  {recipients.map((r) => (
                    <tr key={r.id}>
                      <td><input type="checkbox" checked={selectedIds.includes(r.id)} onChange={() => toggleRecipient(r.id)} /></td>
                      <td>{r.email}</td>
                      <td>{r.company_name || '—'}</td>
                      <td>{r.industry || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-8">
              <Link href="/recipients" className="btn secondary sm">{Icons.plus} Add recipients first</Link>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <Field label="AI agent" help="The agent's prompt and model shape the generated emails.">
              <Select value={form.agent_id || ''} onChange={(e) => setForm({ ...form, agent_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">Select an agent…</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name} {a.model_name ? `· ${a.model_name}` : ''}</option>
                ))}
              </Select>
            </Field>
            {selected && (
              <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
                <div className="muted" style={{ fontSize: 12 }}>PURPOSE</div>
                <p style={{ margin: '4px 0 8px' }}>{selected.purpose || '—'}</p>
                <div className="muted" style={{ fontSize: 12 }}>MODEL</div>
                <p style={{ margin: '4px 0 0' }}>{selected.model_name || 'Default model'}</p>
              </div>
            )}
          </>
        )}

        {step === 3 && (
          <>
            <Field label="Sending account" help="The Gmail/email account used to send this campaign.">
              <Select value={form.email_account_id || ''} onChange={(e) => setForm({ ...form, email_account_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">Select an account…</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.email} ({a.status}{a.is_default ? ' · default' : ''})</option>
                ))}
              </Select>
            </Field>
            {account && (
              <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
                <StatusBadge status={account.status} tone={account.status === 'connected' ? 'green' : 'red'} />
                <p className="muted mt-8">{account.provider === 'google' ? 'Google OAuth' : 'SMTP'} account. {account.is_default ? 'This is your default sending account.' : ''}</p>
              </div>
            )}
            <div className="mt-8"><Link href="/email-accounts" className="btn secondary sm">Manage email accounts</Link></div>
          </>
        )}

        {step === 4 && (
          <>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Field label="Send start time" hint="Local to campaign timezone">
                <Input type="time" value={form.send_start_time} onChange={(e) => setForm({ ...form, send_start_time: e.target.value })} />
              </Field>
              <Field label="Send end time">
                <Input type="time" value={form.send_end_time} onChange={(e) => setForm({ ...form, send_end_time: e.target.value })} />
              </Field>
            </div>
            <Field label="Active days">
              <div className="flex" style={{ flexWrap: 'wrap' }}>
                {DAYS.map(([label, d]) => (
                  <label key={d} className="flex" style={{ marginRight: 14, fontSize: 13.5 }}>
                    <input type="checkbox" checked={form.active_days.includes(d)} onChange={() => toggleDay(d)} />
                    {label}
                  </label>
                ))}
              </div>
            </Field>
            <Field label="Sending speed" hint="emails per hour"
              help={`${form.emails_per_hour} emails/hour → 1 email every ${intervalText(form.emails_per_hour)}.`}>
              <input type="range" min="4" max={maxRate} value={form.emails_per_hour}
                onChange={(e) => setForm({ ...form, emails_per_hour: Number(e.target.value) })} />
              <div className="flex justify-between muted" style={{ fontSize: 12 }}>
                <span>4/hr</span>
                <b>{form.emails_per_hour} / hour</b>
                <span>{isPro ? '50/hr (Pro)' : `${planRateLimit}/hr (free plan)`}</span>
              </div>
              {!isPro && form.emails_per_hour > planRateLimit && (
                <div className="alert warning mt-8">
                  The free plan caps sending at {planRateLimit} emails/hour.
                  <Link href="/billing" style={{ marginLeft: 6 }}>Upgrade to Pro</Link> to go higher.
                </div>
              )}
            </Field>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Field label="Optional daily safety cap" hint="0 = unlimited"
                help="An extra, stricter cap per day on top of the hourly rate. Leave at 0 unless you want one.">
                <Input type="number" min="0" value={form.daily_limit} onChange={(e) => setForm({ ...form, daily_limit: Number(e.target.value) })} />
              </Field>
              <Field label="Stop after N sends" hint="0 = unlimited"
                help="Auto-stop the campaign once this many emails have been sent. The agent stops itself when the limit is reached.">
                <Input type="number" min="0" value={form.max_sends} onChange={(e) => setForm({ ...form, max_sends: Number(e.target.value) })} />
              </Field>
            </div>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Field label="Start date (optional)">
                <Input type="datetime-local" value={form.start_at} onChange={(e) => setForm({ ...form, start_at: e.target.value })} />
              </Field>
              <Field label="End date (optional)">
                <Input type="datetime-local" value={form.end_at} onChange={(e) => setForm({ ...form, end_at: e.target.value })} />
              </Field>
            </div>
            <Field label="Timezone">
              <Input value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })} placeholder="UTC" />
            </Field>
          </>
        )}

        {step === 5 && (
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
              <div className="stat-label">Campaign</div>
              <b>{form.name}</b>
              <div className="muted">{form.review_required ? 'Review before send' : 'Auto-send'}{form.dry_run ? ' · dry run' : ''}</div>
            </div>
            <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
              <div className="stat-label">Recipients</div>
              <b>{selectedIds.length}</b>
            </div>
            <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
              <div className="stat-label">AI agent</div>
              <b>{selected?.name || '—'}</b>
              <div className="muted">{selected?.model_name || 'Default model'}</div>
            </div>
            <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
              <div className="stat-label">Sending account</div>
              <b>{account?.email || '—'}</b>
            </div>
            <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
              <div className="stat-label">Schedule</div>
              <b>{form.send_start_time} – {form.send_end_time}</b>
              <div className="muted">
                {form.active_days.map((d) => ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d]).join(', ')}
                · {form.emails_per_hour}/hr · {form.daily_limit ? `${form.daily_limit}/day cap` : 'no daily cap'}
              </div>
            </div>
            <div className="panel" style={{ padding: 12, background: '#f8fafc' }}>
              <div className="stat-label">Estimated sends</div>
              <b>{form.max_sends ? `Stops after ${form.max_sends}` : `${selectedIds.length} recipients`}</b>
              <div className="muted">
                {selectedIds.length} recipients at {form.emails_per_hour}/hr
                {form.daily_limit ? ` · ${form.daily_limit}/day cap` : ''}
                {form.max_sends ? ' · auto-stop' : ''}
              </div>
            </div>
          </div>
        )}

        <div className="flex mt-16" style={{ justifyContent: 'space-between' }}>
          <Button variant="secondary" onClick={() => (step === 0 ? router.push('/campaigns') : setStep(step - 1))}>
            {step === 0 ? 'Cancel' : 'Back'}
          </Button>
          {step < 5 ? (
            <Button disabled={!canNext} onClick={() => setStep(step + 1)}>Continue <span style={{ transform: 'rotate(90deg)', display: 'inline-flex' }}>{Icons.up}</span></Button>
          ) : (
            <Button disabled={busy} onClick={create}>
              {busy ? 'Creating…' : 'Create Campaign'}
            </Button>
          )}
        </div>
      </Panel>
    </Layout>
  );
}