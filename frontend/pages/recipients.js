import { useEffect, useRef, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import {
  Button, Confirm, Empty, Field, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, TextArea, fmtRel, useToast,
} from '../components/ui';

const PAGE_SIZE = 50;
const EMPTY_RECIPIENT = {
  email: '', company_name: '', industry: '', company_website: '', job_role: '', position_level: '',
};

function GroupPicker({ groups, mode, setMode, value, setValue }) {
  return (
    <div className="panel" style={{ padding: 12 }}>
      <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>RECIPIENT GROUP</div>
      <div className="flex" style={{ gap: 16, marginBottom: 8 }}>
        <label className="flex" style={{ fontSize: 13.5 }}>
          <input type="radio" name="picker_mode" checked={mode === 'existing'} onChange={() => { setMode('existing'); setValue(''); }} />
          Existing group
        </label>
        <label className="flex" style={{ fontSize: 13.5 }}>
          <input type="radio" name="picker_mode" checked={mode === 'new'} onChange={() => { setMode('new'); setValue(''); }} />
          Create new group
        </label>
      </div>
      {mode === 'existing' ? (
        <Select value={value || ''} onChange={(e) => setValue(e.target.value)}>
          <option value="">Select an existing group…</option>
          {groups.map((g) => (
            <option key={g.id} value={g.id}>{g.name} ({g.recipient_count})</option>
          ))}
        </Select>
      ) : (
        <Input placeholder="New group name" value={value} onChange={(e) => setValue(e.target.value)} />
      )}
    </div>
  );
}

function groupPayload(mode, groupId, groupName) {
  if (mode === 'existing') {
    if (!groupId) return { error: 'Select a recipient group' };
    return { group_id: Number(groupId) };
  }
  if (!groupName?.trim()) return { error: 'Enter a name for the new group' };
  return { group_name: groupName.trim() };
}

export default function Recipients() {
  const toast = useToast();
  const [accountGroups, setAccountGroups] = useState(null);
  const [view, setView] = useState('groups'); // groups | detail
  const [activeGroup, setActiveGroup] = useState(null);
  const [page, setPage] = useState(1);
  const [pageData, setPageData] = useState(null);

  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_RECIPIENT);
  const [addMode, setAddMode] = useState('existing');
  const [addGroupId, setAddGroupId] = useState('');
  const [addGroupName, setAddGroupName] = useState('');
  const [addBusy, setAddBusy] = useState(false);

  const [newGroupOpen, setNewGroupOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupBusy, setNewGroupBusy] = useState(false);

  const [importing, setImporting] = useState(false);
  const [preview, setPreview] = useState(null);
  const [impMode, setImpMode] = useState('existing');
  const [impGroupId, setImpGroupId] = useState('');
  const [impGroupName, setImpGroupName] = useState('');
  const [importBusy, setImportBusy] = useState(false);
  const fileRef = useRef(null);
  const pendingFile = useRef(null);

  const [editRecipient, setEditRecipient] = useState(null);
  const [editForm, setEditForm] = useState(EMPTY_RECIPIENT);
  const [editBusy, setEditBusy] = useState(false);

  const [confirmDelete, setConfirmDelete] = useState(null);
  const [confirmDeleteGroup, setConfirmDeleteGroup] = useState(null);
  const [renameGroup, setRenameGroup] = useState(null);
  const [renameValue, setRenameValue] = useState('');

  const [accounts, setAccounts] = useState([]);
  const [compose, setCompose] = useState(null);
  const [composeForm, setComposeForm] = useState({ email_account_id: '', subject: '', body: '' });
  const [composeBusy, setComposeBusy] = useState(false);

  const loadGroups = () => {
    api('/api/recipient-groups')
      .then(setAccountGroups)
      .catch((e) => toast(e.message, 'error'));
  };

  useEffect(() => {
    loadGroups();
    api('/api/email-accounts').then(setAccounts).catch(() => {});
  }, []);

  const loadRecipients = (p, group) => {
    const g = group || activeGroup;
    if (!g) return;
    api(`/api/recipient-groups/${g.id}/recipients?page=${p}&page_size=${PAGE_SIZE}`)
      .then((res) => {
        setPageData(res);
        setPage(p);
      })
      .catch((e) => { toast(e.message, 'error'); setPageData(null); });
  };

  useEffect(() => {
    if (view === 'detail' && activeGroup) loadRecipients(page, activeGroup);
  }, [view]);

  const openGroup = (g) => {
    setActiveGroup(g);
    setPage(1);
    setView('detail');
    setPageData(null);
  };

  const goGroups = () => {
    setView('groups');
    setActiveGroup(null);
    setPageData(null);
    loadGroups();
  };

  const openAdd = () => {
    setForm(EMPTY_RECIPIENT);
    if (activeGroup) {
      setAddMode('existing');
      setAddGroupId(activeGroup.id);
      setAddGroupName('');
    } else {
      setAddMode('new');
      setAddGroupId('');
      setAddGroupName('');
    }
    setAddOpen(true);
  };

  const submitAdd = async () => {
    const group = groupPayload(addMode, addGroupId, addGroupName);
    if (group.error) return toast(group.error, 'error');
    setAddBusy(true);
    try {
      const body = { ...form, ...group };
      await api('/api/recipients', { method: 'POST', body });
      setAddOpen(false);
      setForm(EMPTY_RECIPIENT);
      toast('Recipient added', 'success');
      loadGroups();
      if (view === 'detail') loadRecipients(page, activeGroup);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setAddBusy(false);
    }
  };

  const createGroup = async () => {
    if (!newGroupName.trim()) return toast('Enter a group name', 'error');
    setNewGroupBusy(true);
    try {
      const g = await api('/api/recipient-groups', { method: 'POST', body: { name: newGroupName.trim() } });
      toast(`Group "${g.name}" created`, 'success');
      setNewGroupOpen(false);
      setNewGroupName('');
      loadGroups();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setNewGroupBusy(false);
    }
  };

  const openImport = () => {
    if (activeGroup) {
      setImpMode('existing');
      setImpGroupId(activeGroup.id);
      setImpGroupName('');
    } else {
      setImpMode('new');
      setImpGroupId('');
      setImpGroupName('');
    }
    fileRef.current?.click();
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
    const group = groupPayload(impMode, impGroupId, impGroupName);
    if (group.error) return toast(group.error, 'error');
    const file = pendingFile.current;
    if (!file) return toast('Please choose a file', 'error');
    setImportBusy(true);
    const formData = new FormData();
    formData.append('file', file);
    if (group.group_id) formData.append('group_id', group.group_id);
    if (group.group_name) formData.append('group_name', group.group_name);
    try {
      const res = await api('/api/recipients/import', { method: 'POST', form: formData });
      toast(`Imported ${res.added} recipients (${res.duplicates} duplicates, ${res.invalid} invalid)`, 'success');
      pendingFile.current = null;
      setPreview(null);
      loadGroups();
      if (view === 'detail') loadRecipients(page, activeGroup);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setImportBusy(false);
    }
  };

  const openEdit = (r) => {
    setEditRecipient(r);
    setEditForm({
      email: r.email, company_name: r.company_name || '', industry: r.industry || '',
      company_website: r.company_website || '', job_role: r.job_role || '', position_level: r.position_level || '',
    });
  };

  const submitEdit = async () => {
    setEditBusy(true);
    try {
      const body = {
        email: editForm.email, company_name: editForm.company_name, industry: editForm.industry,
        company_website: editForm.company_website, job_role: editForm.job_role, position_level: editForm.position_level,
      };
      await api(`/api/recipients/${editRecipient.id}`, { method: 'PATCH', body });
      toast('Recipient updated', 'success');
      setEditRecipient(null);
      loadGroups();
      loadRecipients(page, activeGroup);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setEditBusy(false);
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/recipients/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Recipient removed', 'success');
      setConfirmDelete(null);
      loadGroups();
      loadRecipients(page, activeGroup);
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doRename = async () => {
    if (!renameValue.trim()) return toast('Enter a group name', 'error');
    try {
      const g = await api(`/api/recipient-groups/${renameGroup.id}`, { method: 'PATCH', body: { name: renameValue.trim() } });
      toast('Group renamed', 'success');
      setRenameGroup(null);
      loadGroups();
      if (activeGroup?.id === g.id) setActiveGroup({ ...activeGroup, name: g.name });
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDeleteGroup = async () => {
    try {
      const res = await api(`/api/recipient-groups/${confirmDeleteGroup.id}`, { method: 'DELETE' });
      toast(`Group deleted. ${res.moved} recipient${res.moved === 1 ? '' : 's'} moved to Uncategorized.`, 'success');
      setConfirmDeleteGroup(null);
      goGroups();
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

  const items = pageData?.items || [];
  const totalPages = Math.max(1, pageData?.total_pages || 1);

  return (
    <Layout title="Recipients" breadcrumb={<span>Recipients</span>}>
      <div className="toolbar">
        <div className="flex" style={{ flex: 1 }}>
          {view === 'detail' ? (
            <Button variant="ghost" onClick={goGroups}>{Icons.up} All groups</Button>
          ) : (
            <span className="muted" style={{ fontSize: 13 }}>{accountGroups === null ? 'Loading groups…' : `${accountGroups.length} recipient group${accountGroups.length === 1 ? '' : 's'}`}</span>
          )}
        </div>
        <input ref={fileRef} type="file" accept=".xlsx,.csv" style={{ display: 'none' }} onChange={onPickFile} />
        <Button variant="secondary" disabled={importing} onClick={openImport}>
          {importing ? <Spinner /> : Icons.up} Import
        </Button>
        {view === 'groups' && (
          <Button variant="secondary" onClick={() => setNewGroupOpen(true)}>{Icons.plus} New group</Button>
        )}
        <Button onClick={openAdd}>{Icons.plus} Add Recipient</Button>
      </div>

      {view === 'groups' ? (
        <Panel title="Recipient Groups">
          {accountGroups === null ? (
            <Spinner />
          ) : accountGroups.length === 0 ? (
            <Empty message="No recipient groups yet. Create a group, then add or import recipients." />
          ) : (
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
              {accountGroups.map((g) => (
                <div key={g.id} className="panel" style={{ padding: 16, cursor: 'pointer' }} onClick={() => openGroup(g)}>
                  <div className="flex" style={{ justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                    <b>{g.name}</b>
                    <div className="flex" style={{ gap: 4 }} onClick={(e) => e.stopPropagation()}>
                      <button className="btn ghost sm" title="Rename" onClick={() => { setRenameGroup(g); setRenameValue(g.name); }}>{Icons.edit}</button>
                      <button className="btn ghost sm" title="Delete" onClick={() => setConfirmDeleteGroup(g)}>{Icons.trash}</button>
                    </div>
                  </div>
                  <div className="stat-label" style={{ marginTop: 8 }}>{g.recipient_count} recipient{g.recipient_count === 1 ? '' : 's'}</div>
                  <div className="muted" style={{ fontSize: 12 }}>Created {fmtRel(g.created_at)}</div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      ) : (
        <Panel
          title={<>{activeGroup?.name} <span className="muted" style={{ fontWeight: 400, fontSize: 13 }}>· {pageData?.total ?? '*' } recipients</span></>}
        >
          {pageData === null ? (
            <Spinner />
          ) : items.length === 0 ? (
            <Empty message="No recipients in this group yet. Use Add Recipient or Import." />
          ) : (
            <>
              <table className="dense">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Company</th>
                    <th>Industry</th>
                    <th>Role</th>
                    <th>Added</th>
                    <th style={{ width: 92 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((r) => (
                    <tr key={r.id}>
                      <td><b>{r.email}</b></td>
                      <td>{r.company_name || '—'}</td>
                      <td>{r.industry || '—'}</td>
                      <td>{r.job_role ? `${r.job_role}${r.position_level ? ` (${r.position_level})` : ''}` : '—'}</td>
                      <td className="muted">{fmtRel(r.created_at)}</td>
                      <td>
                        <div className="flex" style={{ gap: 6 }}>
                          <button className="btn ghost sm" title="Edit" onClick={() => openEdit(r)}>{Icons.edit}</button>
                          <button className="btn ghost sm" title="Send email" onClick={() => openCompose(r)}>{Icons.send}</button>
                          <button className="btn ghost sm" title="Delete" onClick={() => setConfirmDelete(r)}>{Icons.trash}</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex mt-16" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Button variant="secondary" className="sm" disabled={page <= 1} onClick={() => loadRecipients(page - 1)}>{Icons.up} Previous</Button>
                <span className="muted">Page {pageData.page} of {totalPages} · {pageData.total} total</span>
                <Button variant="secondary" className="sm" disabled={page >= totalPages} onClick={() => loadRecipients(page + 1)}>Next {Icons.up}</Button>
              </div>
            </>
          )}
        </Panel>
      )}

      <Modal open={addOpen} title="Add recipient" onClose={() => setAddOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button disabled={addBusy} onClick={submitAdd}>{addBusy ? 'Adding…' : 'Add'}</Button>
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
        <Field label="">
          <GroupPicker groups={accountGroups || []} mode={addMode} setMode={setAddMode}
            value={addMode === 'existing' ? addGroupId : addGroupName}
            setValue={addMode === 'existing' ? setAddGroupId : setAddGroupName} />
        </Field>
      </Modal>

      <Modal open={newGroupOpen} title="Create recipient group" onClose={() => setNewGroupOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setNewGroupOpen(false)}>Cancel</Button>
            <Button disabled={newGroupBusy} onClick={createGroup}>{newGroupBusy ? 'Creating…' : 'Create'}</Button>
          </>
        }>
        <Field label="Group name">
          <Input value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} placeholder="e.g. Startup Leads" />
        </Field>
      </Modal>

      <Modal open={!!preview} title="Import preview" onClose={() => setPreview(null)}>
        {preview && (
          <>
            <p className="muted">
              {preview.valid} valid rows · {preview.duplicates} duplicates · {preview.invalid} invalid. Review before importing.
            </p>
            <GroupPicker groups={accountGroups || []} mode={impMode} setMode={setImpMode}
              value={impMode === 'existing' ? impGroupId : impGroupName}
              setValue={impMode === 'existing' ? setImpGroupId : setImpGroupName} />
            <div style={{ maxHeight: 260, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 6 }}>
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
              <Button disabled={importBusy} onClick={confirmImport}>{importBusy ? <Spinner /> : Icons.check} Import {preview.valid - preview.duplicates} new</Button>
            </div>
          </>
        )}
      </Modal>

      <Modal open={!!editRecipient} title={`Edit ${editRecipient?.email || ''}`} onClose={() => setEditRecipient(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditRecipient(null)}>Cancel</Button>
            <Button disabled={editBusy} onClick={submitEdit}>{editBusy ? 'Saving…' : 'Save'}</Button>
          </>
        }>
        <Field label="Email">
          <Input type="email" required value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
        </Field>
        <Field label="Company name">
          <Input value={editForm.company_name} onChange={(e) => setEditForm({ ...editForm, company_name: e.target.value })} />
        </Field>
        <Field label="Industry">
          <Input value={editForm.industry} onChange={(e) => setEditForm({ ...editForm, industry: e.target.value })} />
        </Field>
        <Field label="Company website">
          <Input value={editForm.company_website} onChange={(e) => setEditForm({ ...editForm, company_website: e.target.value })} />
        </Field>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Job role">
            <Input value={editForm.job_role} onChange={(e) => setEditForm({ ...editForm, job_role: e.target.value })} />
          </Field>
          <Field label="Position level">
            <Input value={editForm.position_level} onChange={(e) => setEditForm({ ...editForm, position_level: e.target.value })} />
          </Field>
        </div>
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

      <Modal open={!!renameGroup} title={`Rename group`} onClose={() => setRenameGroup(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRenameGroup(null)}>Cancel</Button>
            <Button onClick={doRename}>Save</Button>
          </>
        }>
        <Field label="Group name">
          <Input value={renameValue} onChange={(e) => setRenameValue(e.target.value)} />
        </Field>
      </Modal>

      <Confirm open={!!confirmDelete} title="Remove recipient" danger
        message={`Remove ${confirmDelete?.email}? This cannot be undone.`}
        confirmLabel="Remove" onCancel={() => setConfirmDelete(null)} onConfirm={doDelete} />

      <Confirm open={!!confirmDeleteGroup} title="Delete group" danger
        message={`Delete "${confirmDeleteGroup?.name}"? Its ${confirmDeleteGroup?.recipient_count || 0} recipient${confirmDeleteGroup?.recipient_count === 1 ? '' : 's'} will be moved to "Uncategorized".`}
        confirmLabel="Delete" onCancel={() => setConfirmDeleteGroup(null)} onConfirm={doDeleteGroup} />
    </Layout>
  );
}