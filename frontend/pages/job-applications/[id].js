import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import {
  Button, Empty, Field, Icons, Input, Panel, Spinner, StatusBadge, TextArea, fmtRel, useToast, Progress, Confirm,
} from '../../components/ui';

const STATUS_TONES = {
  preparing: 'gray', analyzing: 'blue', filling: 'blue',
  needs_review: 'amber', ready: 'green', submitting: 'teal',
  submitted: 'green', failed: 'red', cancelled: 'gray',
};

export default function ApplicationDetail() {
  const { user } = useAuth();
  const router = useRouter();
  const { id } = router.query;
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingField, setEditingField] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user && id) loadData();
  }, [user, id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [appData, fieldsData] = await Promise.all([
        api(`/api/job-applications/${id}`),
        api(`/api/job-applications/${id}/fields`),
      ]);
      setApp(appData);
      setFields(fieldsData);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const startAutofill = async () => {
    try {
      await api(`/api/job-applications/${id}/start`, { method: 'POST' });
      toast('Autofill started', 'success');
      loadData();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const updateField = async (fieldId, userValue, skipped = false) => {
    try {
      const updated = await api(`/api/job-applications/${id}/fields/${fieldId}`, {
        method: 'PATCH',
        body: { user_value: userValue, skipped },
      });
      setFields(fields.map(f => f.id === fieldId ? { ...f, ...updated } : f));
      setEditingField(null);
      toast('Field updated', 'success');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const submitApplication = async () => {
    setSubmitting(true);
    try {
      await api(`/api/job-applications/${id}/submit`, {
        method: 'POST',
        body: { confirmed: true },
      });
      toast('Application submitted!', 'success');
      setConfirmSubmit(false);
      loadData();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const cancelApplication = async () => {
    try {
      await api(`/api/job-applications/${id}/cancel`, { method: 'POST' });
      toast('Application cancelled', 'success');
      loadData();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const getFieldValue = (f) => f.user_value || f.mapped_value || '';
  const progress = app ? (app.total_fields > 0 ? ((app.auto_filled + app.needs_review) / app.total_fields * 100) : 0) : 0;

  if (loading) return <Layout title="Application"><Spinner /></Layout>;
  if (!app) return <Layout title="Application"><Empty message="Application not found." /></Layout>;

  const statusActions = {
    preparing: <Button onClick={startAutofill}>{Icons.play} Start Analysis</Button>,
    needs_review: <Button onClick={() => setConfirmSubmit(true)}>{Icons.check} Review & Submit</Button>,
    ready: <Button onClick={() => setConfirmSubmit(true)}>{Icons.check} Submit Application</Button>,
    failed: <Button onClick={startAutofill}>{Icons.refresh} Retry</Button>,
  };

  return (
    <Layout title={`${app.company_name || 'Application'} — ${app.role_title || ''}`} breadcrumb={
      <><Link href="/job-applications">Applications</Link> <span>/</span> <span>#{app.id}</span></>
    }>
      {/* Header */}
      <Panel>
        <div className="flex justify-between" style={{ alignItems: 'flex-start' }}>
          <div>
            <div className="flex" style={{ gap: 8, marginBottom: 8 }}>
              <StatusBadge status={app.status} tone={STATUS_TONES[app.status] || 'gray'} />
              <span className="badge gray">{app.ats_platform || 'unknown'}</span>
            </div>
            <h2 style={{ margin: 0, fontSize: 18 }}>{app.role_title || 'Unknown Role'}</h2>
            <div className="muted" style={{ marginTop: 4 }}>{app.company_name || 'Unknown Company'}</div>
            <a href={app.job_url} target="_blank" rel="noopener" className="muted" style={{ fontSize: 12, wordBreak: 'break-all' }}>
              {app.job_url}
            </a>
          </div>
          <div className="flex" style={{ gap: 8 }}>
            {statusActions[app.status]}
            {app.status !== 'submitted' && app.status !== 'cancelled' && (
              <Button variant="danger" size="sm" onClick={cancelApplication}>Cancel</Button>
            )}
          </div>
        </div>

        {app.error_message && (
          <div style={{ marginTop: 12, padding: 12, background: 'var(--danger-bg)', borderRadius: 6, fontSize: 13 }}>
            <b>Error:</b> {app.error_message}
            {app.requires_user_action && <div style={{ marginTop: 4 }}>Action required: {app.requires_user_action}</div>}
          </div>
        )}
      </Panel>

      {/* Stats */}
      {app.total_fields > 0 && (
        <Panel title="Progress">
          <div className="grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: 24, fontWeight: 600 }}>{app.total_fields}</div>
              <div className="muted" style={{ fontSize: 12 }}>Total Fields</div>
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 600, color: 'var(--success)' }}>{app.auto_filled}</div>
              <div className="muted" style={{ fontSize: 12 }}>Auto-Filled</div>
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 600, color: 'var(--warning)' }}>{app.needs_review}</div>
              <div className="muted" style={{ fontSize: 12 }}>Needs Review</div>
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 600, color: 'var(--muted)' }}>{app.unanswered}</div>
              <div className="muted" style={{ fontSize: 12 }}>Unanswered</div>
            </div>
          </div>
          <Progress percent={Math.round(progress)} style={{ marginTop: 16 }} />
        </Panel>
      )}

      {/* Screenshot */}
      {app.screenshot_path && (
        <Panel title="Page Preview">
          <div style={{ textAlign: 'center' }}>
            <img
              src={`/api/job-applications/${id}/screenshot`}
              alt="Application page preview"
              style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid var(--border)' }}
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          </div>
        </Panel>
      )}

      {/* Fields */}
      <Panel title={`Application Fields (${fields.length})`}>
        {fields.length === 0 ? (
          <Empty message={app.status === 'preparing' ? 'Click "Start Analysis" to begin.' : 'No fields extracted yet.'} />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {fields.map((f) => {
              const val = getFieldValue(f);
              const isEditing = editingField === f.id;
              return (
                <div key={f.id} className="flex" style={{
                  padding: '10px 12px', borderRadius: 4, gap: 12, alignItems: 'flex-start',
                  background: f.requires_review ? 'var(--warning-bg)' : 'transparent',
                  borderLeft: `3px solid ${f.skipped ? 'var(--muted)' : f.requires_review ? 'var(--warning)' : val ? 'var(--success)' : 'var(--border)'}`,
                }}>
                  {/* Status icon */}
                  <div style={{ minWidth: 20, paddingTop: 2 }}>
                    {f.skipped ? <span className="muted">—</span>
                      : val ? <span style={{ color: 'var(--success)' }}>{Icons.check}</span>
                      : <span className="muted">?</span>}
                  </div>

                  {/* Field info */}
                  <div style={{ flex: 1 }}>
                    <div className="flex" style={{ gap: 8, alignItems: 'center', marginBottom: 2 }}>
                      <b style={{ fontSize: 13 }}>{f.field_label || f.field_name || f.field_id || `Field ${f.id}`}</b>
                      <span className="badge gray" style={{ fontSize: 10 }}>{f.field_type}</span>
                      {f.confidence > 0 && (
                        <span className="muted" style={{ fontSize: 11 }}>
                          {Math.round(f.confidence * 100)}% match
                        </span>
                      )}
                      {f.section && <span className="muted" style={{ fontSize: 11 }}>{f.section}</span>}
                    </div>

                    {isEditing ? (
                      <div className="flex" style={{ gap: 6, marginTop: 4 }}>
                        {f.field_type === 'select' && f.options?.length > 0 ? (
                          <select className="select" value={editValue} onChange={(e) => setEditValue(e.target.value)}
                            style={{ flex: 1, fontSize: 13 }}>
                            <option value="">Select...</option>
                            {f.options.map((o, i) => (
                              <option key={i} value={o.value || o.label}>{o.label || o.value}</option>
                            ))}
                          </select>
                        ) : f.field_type === 'textarea' ? (
                          <TextArea rows={2} value={editValue} onChange={(e) => setEditValue(e.target.value)} style={{ flex: 1, fontSize: 13 }} />
                        ) : (
                          <Input value={editValue} onChange={(e) => setEditValue(e.target.value)} style={{ flex: 1, fontSize: 13 }} />
                        )}
                        <Button size="sm" onClick={() => updateField(f.id, editValue)}>Save</Button>
                        <Button size="sm" variant="secondary" onClick={() => setEditingField(null)}>Cancel</Button>
                      </div>
                    ) : (
                      <div className="muted" style={{ fontSize: 13 }}>
                        {val || <em>No value</em>}
                      </div>
                    )}

                    {f.mapping_reasoning && (
                      <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                        {f.mapping_reasoning}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  {!isEditing && (
                    <div className="flex" style={{ gap: 4 }}>
                      <button className="btn ghost sm" title="Edit" onClick={() => { setEditingField(f.id); setEditValue(val); }}>
                        {Icons.edit}
                      </button>
                      {!f.skipped && (
                        <button className="btn ghost sm" title="Skip" onClick={() => updateField(f.id, '', true)}>
                          {Icons.x}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {/* Submit confirmation */}
      <Confirm open={confirmSubmit} title="Submit Application"
        message={`Submit this application to ${app.company_name || 'the company'}? This will fill and submit the form on your behalf.`}
        confirmLabel={submitting ? 'Submitting...' : 'Submit Application'}
        onCancel={() => setConfirmSubmit(false)}
        onConfirm={submitApplication} />
    </Layout>
  );
}
