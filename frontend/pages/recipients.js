import { useEffect, useRef, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import {
  Button, Confirm, Empty, Field, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, TextArea, fmtRel, useToast,
} from '../components/ui';

const EMPTY_RECIPIENT = {
  email: '', company_name: '', industry: '', company_website: '', job_role: '', position_level: '',
};

export default function Recipients() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState([]);
  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_RECIPIENT);
  const [importing, setImporting] = useState(false);
  const [preview, setPreview] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const fileRef = useRef(null);
  const pendingFile = useRef(null);
  const [accounts, setAccounts] = useState([]);
  const [compose, setCompose] = useState(null);
  const [composeForm, setComposeForm] = useState({ email_account_id: '', subject: '', body: '' });
  const [composeBusy, setComposeBusy] = useState(false);

  useEffect(() => {
    api('/api/email-accounts').then(setAccounts).catch(() => {});
  }, []);

  const load = () => {
    api(`/api/recipients?search=${encodeURIComponent(search)}&limit=500`)
      .then(setItems)
      .catch((e) => toast(e.message, 'error'));
  };

  useEffect(() => { load(); }, [search]);

  const submitAdd = async () => {
    try {
      await api('/api/recipients', { method: 'POST', body: form });
      setAddOpen(false);
      setForm(EMPTY_RECIPIENT);
      toast('Recipient added', 'success');
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const onPickFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api('/api/recipients/import/preview', { method: 'POST', form: formData });
      pendingFile.current = file;
      setPreview(res);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  };

  const confirmImport = async () => {
    const file = pendingFile.current;
    if (!file) {
      toast('Please choose a file', 'error');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api('/api/recipients/import', { method: 'POST', form: formData });
      toast(`Imported ${res.added} recipients (${res.duplicates} duplicates, ${res.invalid} invalid)`, 'success');
      pendingFile.current = null;
      setPreview(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const toggle = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const bulkDelete = async () => {
    try {
      await api('/api/recipients/bulk-delete', { method: 'POST', body: { ids: selected } });
      toast(`Deleted ${selected.length} recipients`, 'success');
      setSelected([]);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/recipients/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Recipient removed', 'success');
      setConfirmDelete(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const openCompose = (r) => {
    const firstAccount =
      accounts.find((a) => a.is_default && a.status === 'connected') ||
      accounts.find((a) => a.status === 'connected');
    setCompose(r);
    setComposeForm({ email_account_id: firstAccount?.id || '', subject: '', body: '' });
  };

  const sendManual = async () => {
    if (!composeForm.email_account_id || !composeForm.subject || !composeForm.body) {
      toast('Pick an account and fill subject and body', 'error');
      return;
    }
    setComposeBusy(true);
    try {
      await api('/api/emails/manual', {
        method: 'POST',
        body: { recipient_id: compose.id, email_account_id: composeForm.email_account_id, subject: composeForm.subject, body: composeForm.body },
      });
      toast(`Email sent to ${compose.email}`, 'success');
      setCompose(null);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setComposeBusy(false);
    }
  };

  return (
    <Layout title="Recipients" breadcrumb={<span>Recipients</span>}>
      <div className="toolbar">
        <div className="flex" style={{ flex: 1, position: 'relative' }}>
          {Icons.search}
          <Input placeholder="Search recipients…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <input ref={fileRef} type="file" accept=".xlsx,.csv" style={{ display: 'none' }} onChange={onPickFile} />
        <Button variant="secondary" disabled={importing} onClick={() => fileRef.current?.click()}>
          {importing ? <Spinner /> : Icons.up} Import
        </Button>
        <Button onClick={() => setAddOpen(true)}>{Icons.plus} Add Recipient</Button>
        {selected.length > 0 && (
          <Button variant="danger" onClick={bulkDelete}>Delete {selected.length}</Button>
        )}
      </div>

      <Panel>
        {items === null ? (
          <Spinner />
        ) : items.length === 0 ? (
          <Empty message="No recipients yet. Import an Excel/CSV file or add one manually." />
        ) : (
          <table className="dense">
            <thead>
              <tr>
                <th style={{ width: 32 }}>
                  <input type="checkbox" onChange={(e) => setSelected(e.target.checked ? items.map((i) => i.id) : [])}
                    checked={selected.length === items.length && items.length > 0} />
                </th>
                <th>Email</th>
                <th>Company</th>
                <th>Industry</th>
                <th>Role</th>
                <th>Added</th>
                <th style={{ width: 60 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td><input type="checkbox" checked={selected.includes(r.id)} onChange={() => toggle(r.id)} /></td>
                  <td><b>{r.email}</b></td>
                  <td>{r.company_name || '—'}</td>
                  <td>{r.industry || '—'}</td>
                  <td>{r.job_role ? `${r.job_role}${r.position_level ? ` (${r.position_level})` : ''}` : '—'}</td>
                  <td className="muted">{fmtRel(r.created_at)}</td>
                  <td>
                    <div className="flex" style={{ gap: 6 }}>
                      <button className="btn ghost sm" onClick={() => openCompose(r)}>{Icons.send}</button>
                      <button className="btn ghost sm" onClick={() => setConfirmDelete(r)}>{Icons.trash}</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Modal open={addOpen} title="Add recipient" onClose={() => setAddOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button onClick={submitAdd}>Add</Button>
          </>
        }>
        <Field label="Email">
          <Input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="john@company.com" />
        </Field>
        <Field label="Company name">
          <Input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
        </Field>
        <Field label="Industry">
          <Input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} />
        </Field>
        <Field label="Company website">
          <Input value={form.company_website} onChange={(e) => setForm({ ...form, company_website: e.target.value })} />
        </Field>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Job role">
            <Input value={form.job_role} onChange={(e) => setForm({ ...form, job_role: e.target.value })} />
          </Field>
          <Field label="Position level">
            <Input value={form.position_level} onChange={(e) => setForm({ ...form, position_level: e.target.value })} />
          </Field>
        </div>
      </Modal>

      <Modal open={!!preview} title="Import preview" onClose={() => setPreview(null)}>
        {preview && (
          <>
            <p className="muted">
              {preview.valid} valid rows · {preview.duplicates} duplicates · {preview.invalid} invalid. Review before importing.
            </p>
            <div style={{ maxHeight: 320, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 6 }}>
              <table className="dense">
                <thead>
                  <tr><th>Email</th><th>Company</th><th>Industry</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {preview.rows.slice(0, 50).map((r, i) => (
                    <tr key={i}>
                      <td>{r.email}</td>
                      <td>{r.company_name || '—'}</td>
                      <td>{r.industry || '—'}</td>
                      <td>
                        {!r.valid ? <StatusBadge status="invalid" tone="red" />
                          : r.duplicate ? <StatusBadge status="duplicate" tone="amber" />
                          : <StatusBadge status="will import" tone="green" />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex mt-16" style={{ justifyContent: 'space-between' }}>
              <span className="muted">{preview.rows.length > 50 ? `Showing 50 of ${preview.rows.length} rows` : `${preview.rows.length} rows total`}</span>
              <Button onClick={confirmImport}>{Icons.check} Import {preview.valid - preview.duplicates} new</Button>
            </div>
          </>
        )}
      </Modal>

      <Modal open={!!compose} title={`Send email to ${compose?.email || ''}`} onClose={() => setCompose(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCompose(null)}>Cancel</Button>
            <Button disabled={composeBusy} onClick={sendManual}>{composeBusy ? 'Sending…' : 'Send'}</Button>
          </>
        }>
        <Field label="Send from" help="Manual emails are recorded in Email History.">
          <Select value={composeForm.email_account_id} onChange={(e) => setComposeForm({ ...composeForm, email_account_id: e.target.value })}>
            <option value="">Select an account…</option>
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.email} ({a.status}{a.is_default ? ' · default' : ''})</option>)}
          </Select>
        </Field>
        <Field label="Subject">
          <Input value={composeForm.subject} onChange={(e) => setComposeForm({ ...composeForm, subject: e.target.value })} placeholder="Quick question" />
        </Field>
        <Field label="Body">
          <TextArea rows={10} value={composeForm.body} onChange={(e) => setComposeForm({ ...composeForm, body: e.target.value })} placeholder="Hi…" />
        </Field>
      </Modal>

      <Confirm open={!!confirmDelete} title="Remove recipient" danger
        message={`Remove ${confirmDelete?.email}? This cannot be undone.`}
        confirmLabel="Remove" onCancel={() => setConfirmDelete(null)} onConfirm={doDelete} />
    </Layout>
  );
}