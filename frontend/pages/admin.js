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
  const [recipients, setRecipients] = useState(null);
  const [groups, setGroups] = useState(null);
  const [categories, setCategories] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_MODEL);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [recipientsSearch, setRecipientsSearch] = useState('');
  const [groupName, setGroupName] = useState('');
  const [groupSlug, setGroupSlug] = useState('');
  const [groupDesc, setGroupDesc] = useState('');
  const [groupPrice, setGroupPrice] = useState(0);
  const [groupIsFree, setGroupIsFree] = useState(false);
  const [groupRequiredSub, setGroupRequiredSub] = useState('free');
  const [catName, setCatName] = useState('');
  const [catSlug, setCatSlug] = useState('');
  const [editingCat, setEditingCat] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  const TABS = [
    { key: 'models', label: 'AI Models' },
    { key: 'users', label: 'Users' },
    { key: 'recipients', label: 'Recipients' },
    { key: 'groups', label: 'Groups' },
    { key: 'categories', label: 'Categories' },
  ];

  useEffect(() => {
    if (user && !user.is_admin) router.replace('/dashboard');
  }, [user]);

  const loadModels = () => {
    api('/api/admin/models').then(setModels).catch((e) => toast(e.message, 'error'));
  };
  const loadUsers = () => {
    api('/api/admin/users').then(setUsers).catch((e) => toast(e.message, 'error'));
  };
  const loadRecipients = () => {
    let url = '/api/admin/recipients?limit=500';
    if (recipientsSearch) url += '&search=' + encodeURIComponent(recipientsSearch);
    api(url).then(setRecipients).catch((e) => toast(e.message, 'error'));
  };
  const loadGroups = () => {
    api('/api/recipient-groups/admin/all').then(setGroups).catch((e) => toast(e.message, 'error'));
  };
  const loadCategories = () => {
    api('/api/categories?active_only=false').then(setCategories).catch((e) => toast(e.message, 'error'));
  };
  useEffect(() => {
    loadModels();
    loadUsers();
    loadGroups();
    loadCategories();
  }, []);

  if (!user || !user.is_admin) return null;

  const openCreate = () => { setEditing(null); setForm(EMPTY_MODEL); setModalOpen(true); };
  const openEdit = (m) => {
    setEditing(m);
    setForm({ ...EMPTY_MODEL, ...m, api_key: '' });
    setModalOpen(true);
  };

  const openGroupModal = (g = null) => {
    setEditingGroup(g);
    if (g) {
      setGroupName(g.name);
      setGroupSlug(g.slug);
      setGroupDesc(g.description);
      setGroupPrice(g.price);
      setGroupIsFree(g.is_free);
      setGroupRequiredSub(g.required_subscription);
    } else {
      setGroupName('');
      setGroupSlug('');
      setGroupDesc('');
      setGroupPrice(0);
      setGroupIsFree(false);
      setGroupRequiredSub('free');
    }
  };

  const saveGroup = async () => {
    const payload = {
      name: groupName, slug: groupSlug || groupName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''),
      description: groupDesc, price: groupPrice, is_free: groupIsFree,
      required_subscription: groupRequiredSub,
    };
    try {
      if (editingGroup) {
        await api('/api/recipient-groups/' + editingGroup.id, { method: 'PATCH', body: payload });
        toast('Group updated', 'success');
      } else {
        await api('/api/recipient-groups', { method: 'POST', body: payload });
        toast('Group created', 'success');
      }
      setEditingGroup(null);
      loadGroups();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const deleteGroup = async (g) => {
    if (!confirm('Delete group "' + g.name + '"? This removes the group (not recipients).')) return;
    try {
      await api('/api/recipient-groups/' + g.id, { method: 'DELETE' });
      toast('Group deleted', 'success');
      loadGroups();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const openCategoryModal = (c = null) => {
    setEditingCat(c);
    setCatName(c ? c.name : '');
    setCatSlug(c ? c.slug : '');
  };

  const saveCategory = async () => {
    if (!catName || !catSlug) {
      toast('Name and slug are required', 'error');
      return;
    }
    try {
      if (editingCat) {
        await api('/api/categories/' + editingCat.id, { method: 'PATCH', body: { name: catName, slug: catSlug } });
        toast('Category updated', 'success');
      } else {
        await api('/api/categories', { method: 'POST', body: { name: catName, slug: catSlug } });
        toast('Category created', 'success');
      }
      setEditingCat(null);
      loadCategories();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const openEditRecipient = (r) => {
    // For now, just show a toast with recipient info. Could expand to full editor.
    toast('Recipient id=' + r.id + ' (' + r.email + '). Admin recipient editing coming soon.', 'info');
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
        {TABS.map((t) => (
          <Button key={t.key} variant={tab === t.key ? 'primary' : 'secondary'} onClick={() => setTab(t.key)}>
            {t.label}
          </Button>
        ))}
        {tab === 'models' && <Button onClick={openCreate}>{Icons.plus} Add platform model</Button>}
        {tab === 'groups' && <Button onClick={openGroupModal}>{Icons.plus} New group</Button>}
        {tab === 'categories' && <Button onClick={openCategoryModal}>{Icons.plus} New category</Button>}
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

      {tab === 'recipients' && (
        <Panel title="All Recipients">
          <div className="flex" style={{ marginBottom: 12 }}>
            <input type="checkbox" style={{ width: 16 }} onChange={() => {}} />
            <Input
              placeholder="Search recipients…"
              value={recipientsSearch}
              onChange={(e) => { setRecipientsSearch(e.target.value); setTimeout(loadRecipients, 300); }}
              style={{ flex: 1 }}
            />
          </div>
          {recipients === null ? (
            <Spinner />
          ) : recipients.length === 0 ? (
            <Empty message="No recipients found." />
          ) : (
            <table className="dense">
              <thead>
                <tr>
                  <th></th>
                  <th>Email</th>
                  <th>Category</th>
                  <th>Owner</th>
                  <th>Free</th>
                  <th>Status</th>
                  <th>Added</th>
                  <th style={{ width: 120 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recipients.map((r) => (
                  <tr key={r.id}>
                    <td><input type="checkbox" onChange={() => {}} /></td>
                    <td><b>{r.email}</b></td>
                    <td>{_categoryName(categories, r.category_id) || '—'}</td>
                    <td>{r.added_by}</td>
                    <td>{r.is_free ? <StatusBadge status="Free" tone="green" /> : <StatusBadge status="Paid" tone="blue" />}</td>
                    <td>{r.status}</td>
                    <td className="muted">{r.created_at ? fmtDate(r.created_at) : '—'}</td>
                    <td>
                      <Button variant="ghost" sm onClick={() => openEditRecipient(r)}>{Icons.edit}</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      )}

      {tab === 'groups' && (
        <Panel title="Recipient Groups">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span className="muted">Manage catalog groups and pricing</span>
          </div>
          {groups === null ? (
            <Spinner />
          ) : groups.length === 0 ? (
            <Empty message="No groups yet. Create one to start selling recipient bundles." />
          ) : (
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
              {groups.map((g) => (
                <Panel key={g.id} title={g.name} actions={
                  <StatusBadge status={g.is_free ? 'Free' : 'Paid'} tone={g.is_free ? 'green' : 'blue'} />
                }>
                  <table className="dense" style={{ margin: '6px 0' }}>
                    <tbody>
                      <tr><td className="muted">Category</td><td>{_categoryName(categories, g.category_id) || '—'}</td></tr>
                      <tr><td className="muted">Contacts</td><td><b>{g.recipient_count}</b></td></tr>
                      <tr><td className="muted">Price</td><td>${g.price.toFixed(2)}</td></tr>
                      <tr><td className="muted">Required</td><td>{g.required_subscription}</td></tr>
                      <tr><td className="muted">Status</td><td>{g.status}</td></tr>
                    </tbody>
                  </table>
                  <div className="flex" style={{ gap: 8, marginTop: 8 }}>
                    <Button variant="secondary" sm onClick={() => openEditGroup(g)}>{Icons.edit} Edit</Button>
                    <Button variant="danger" sm onClick={() => deleteGroup(g)}>{Icons.trash} Delete</Button>
                  </div>
                </Panel>
              ))}
            </div>
          )}
        </Panel>
      )}

      {tab === 'categories' && (
        <Panel title="Categories">
          {categories === null ? (
            <Spinner />
          ) : categories.length === 0 ? (
            <Empty message="No categories yet." />
          ) : (
            <table className="dense">
              <thead>
                <tr><th>Name</th><th>Slug</th><th>Active</th><th>Order</th><th style={{ width: 100 }}></th></tr>
              </thead>
              <tbody>
                {categories.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.slug}</td>
                    <td>{c.is_active ? '✅' : '❌'}</td>
                    <td>{c.sort_order}</td>
                    <td>
                      <Button variant="ghost" sm onClick={() => openCategoryModal(c)}>{Icons.edit}</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
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

      <Modal open={!!editingGroup} title={editingGroup ? 'Edit Group' : 'New Group'} onClose={() => setEditingGroup(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditingGroup(null)}>Cancel</Button>
            <Button onClick={saveGroup}>Save</Button>
          </>
        }>
        <Field label="Name">
          <Input value={groupName} onChange={(e) => setGroupName(e.target.value)} placeholder="Software Developers" />
        </Field>
        <Field label="Slug">
          <Input value={groupSlug} onChange={(e) => setGroupSlug(e.target.value)} />
        </Field>
        <Field label="Description">
          <Input value={groupDesc} onChange={(e) => setGroupDesc(e.target.value)} />
        </Field>
        <label className="flex" style={{ fontSize: 13.5 }}>
          <input type="checkbox" checked={groupIsFree} onChange={(e) => setGroupIsFree(e.target.checked)} />
          Free group (accessible to all users)
        </label>
        {!groupIsFree && (
          <>
            <Field label="Price (USD)">
              <Input type="number" min="0" step="0.01" value={groupPrice} onChange={(e) => setGroupPrice(Number(e.target.value))} />
            </Field>
            <Field label="Required subscription">
              <select className="select" value={groupRequiredSub} onChange={(e) => setGroupRequiredSub(e.target.value)}>
                <option value="free">Free</option>
                <option value="pro">Pro</option>
                <option value="max">Max</option>
              </select>
            </Field>
          </>
        )}
      </Modal>

      <Modal open={!!editingCat} title={editingCat ? 'Edit Category' : 'New Category'} onClose={() => setEditingCat(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditingCat(null)}>Cancel</Button>
            <Button onClick={saveCategory}>Save</Button>
          </>
        }>
        <Field label="Name">
          <Input value={catName} onChange={(e) => setCatName(e.target.value)} />
        </Field>
        <Field label="Slug">
          <Input value={catSlug} onChange={(e) => setCatSlug(e.target.value)} />
        </Field>
      </Modal>
    </Layout>
  );
}

function _categoryName(categories, id) {
  if (!id || !categories) return '';
  const cat = categories.find((c) => c.id === id);
  return cat ? cat.name : '';
}