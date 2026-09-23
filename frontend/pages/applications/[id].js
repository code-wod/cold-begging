import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, fmtDate, useToast, Icons, Button, Modal, Confirm, Field, TextArea } from '../../components/ui';

export default function ApplicationDetail() {
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [notes, setNotes] = useState('');

  const { id } = router.query;

  useEffect(() => {
    if (id) fetchApplication();
  }, [id]);

  const fetchApplication = async () => {
    setLoading(true);
    try {
      const data = await api(`/api/applications/${id}`);
      setApp(data);
      if (data.notes) setNotes(data.notes);
    } catch (e) {
      toast(e.message, 'error');
      router.push('/applications');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (type) => {
    if (!app) return;
    setActionLoading(true);
    try {
      if (type === 'approve') {
        await api(`/api/applications/${app.id}/approve`, { method: 'POST' });
        toast('Application approved!', 'success');
      } else if (type === 'open') {
        await api(`/api/applications/${app.id}/open`, { method: 'POST' });
        toast('Application opened!', 'success');
        if (app.application_url) {
          window.open(app.application_url, '_blank', 'noopener,noreferrer');
        }
      } else if (type === 'mark_applied') {
        await api(`/api/applications/${app.id}/mark-applied`, { method: 'POST', body: { notes: 'Applied via job board' } });
        toast('Marked as applied!', 'success');
      } else if (type === 'reject') {
        await api(`/api/applications/${app.id}/reject`, { method: 'POST', body: { reason: notes || 'Not a good fit' } });
        toast('Application rejected', 'success');
      } else if (type === 'withdraw') {
        await api(`/api/applications/${app.id}/withdraw`, { method: 'POST', body: { reason: notes || 'Withdrawn' } });
        toast('Application withdrawn', 'success');
      }
      fetchApplication();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (!score) return 'gray';
    if (score >= 80) return 'green';
    if (score >= 70) return 'teal';
    if (score >= 60) return 'amber';
    return 'red';
  };

  if (loading) {
    return <Layout title="Application" breadcrumb={<Link href="/applications">Applications</Link>}><Spinner /></Layout>;
  }

  if (!app) {
    return <Layout title="Application" breadcrumb={<Link href="/applications">Applications</Link>}><Empty message="Application not found" /></Layout>;
  }

  return (
    <Layout title={app.job?.title || 'Application'} breadcrumb={<><Link href="/applications">Applications</Link> / <span>{app.job?.title || 'Application'}</span></>}>
      <div className="page-head">
        <div>
          <h1>{app.job?.title || 'Unknown Position'}</h1>
          <div className="muted">{app.job?.company_name || 'Unknown Company'}</div>
        </div>
        <div className="flex" style={{ gap: 8, marginTop: 8 }}>
          {app.match_score !== null && (
            <div className="flex" style={{ alignItems: 'center', gap: 8 }}>
              <span className="muted">Match:</span>
              <div className="progress" style={{ width: 100 }}><div style={{ width: `${app.match_score}%`, background: `var(--${getScoreColor(app.match_score)})` }} /></div>
              <span className="badge" style={{ background: `var(--${getScoreColor(app.match_score)})` }}>{app.match_score}%</span>
            </div>
          )}
          <StatusBadge status={app.status.replace('_', ' ')} />
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 380px', gap: 16 }}>
        <div>
          {app.job && (
            <Panel title="Job Details">
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Company</div>
                <div>{app.job.company_name}</div>
                {app.job.company_url && <a href={app.job.company_url} target="_blank" rel="noopener" className="muted" style={{ fontSize: 13 }}>Website</a>}
              </div>
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Location</div>
                <div>{app.job.location || 'Not specified'}</div>
              </div>
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Remote Type</div>
                <div>{app.job.remote_type || 'Not specified'}</div>
              </div>
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Employment Type</div>
                <div>{app.job.employment_type || 'Not specified'}</div>
              </div>
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Experience Level</div>
                <div>{app.job.experience_level || 'Not specified'}</div>
              </div>
              {app.job.salary_min && app.job.salary_max && (
                <div className="field" style={{ marginBottom: 12 }}>
                  <div className="label">Salary Range</div>
                  <div>${app.job.salary_min.toLocaleString()} - ${app.job.salary_max.toLocaleString()} {app.job.currency}</div>
                </div>
              )}
              {app.job.application_url && (
                <div className="field">
                  <div className="label">Application URL</div>
                  <a href={app.job.application_url} target="_blank" rel="noopener noreferrer" className="btn">
                    {Icons.send} Open Application
                  </a>
                </div>
              )}
            </Panel>
          )}

          {app.cover_letter && (
            <Panel title="Cover Letter">
              <div className="prose" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, background: 'var(--surface)', padding: 16, borderRadius: 8 }}>
                {app.cover_letter}
              </div>
            </Panel>
          )}

          {app.recruiter_email && (
            <Panel title="Recruiter Email">
              <div className="prose" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, background: 'var(--surface)', padding: 16, borderRadius: 8 }}>
                {app.recruiter_email}
              </div>
            </Panel>
          )}

          {Object.keys(app.screening_answers || {}).length > 0 && (
            <Panel title="Screening Answers">
              {Object.entries(app.screening_answers).map(([question, answer]) => (
                <div key={question} style={{ marginBottom: 16 }}>
                  <div className="label" style={{ fontSize: 13, marginBottom: 4 }}>{question}</div>
                  <div className="prose" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, background: 'var(--surface)', padding: 12, borderRadius: 8 }}>
                    {answer}
                  </div>
                </div>
              ))}
            </Panel>
          )}

          {app.match_analysis && (
            <Panel title="Match Analysis">
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Reasoning</div>
                <div className="muted">{app.match_analysis.reasoning_summary}</div>
              </div>
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div>
                  <div className="label" style={{ fontSize: 12 }}>Matched Skills</div>
                  {app.match_analysis.matched_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-4">
                      {app.match_analysis.matched_skills.map(s => <span key={s} className="badge green" style={{ fontSize: 11 }}>{s}</span>)}
                    </div>
                  ) : <div className="muted" style={{ fontSize: 12 }}>None</div>}
                </div>
                <div>
                  <div className="label" style={{ fontSize: 12 }}>Missing Skills</div>
                  {app.match_analysis.missing_skills.length > 0 ? (
                    <div className="flex flex-wrap gap-4">
                      {app.match_analysis.missing_skills.map(s => <span key={s} className="badge red" style={{ fontSize: 11 }}>{s}</span>)}
                    </div>
                  ) : <div className="muted" style={{ fontSize: 12 }}>None</div>}
                </div>
              </div>
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Risk Factors</div>
                {app.match_analysis.risk_factors.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {app.match_analysis.risk_factors.map((r, i) => <li key={i} className="muted" style={{ fontSize: 12 }}>{r}</li>)}
                  </ul>
                ) : <div className="muted" style={{ fontSize: 12 }}>None</div>}
              </div>
            </Panel>
          )}
        </div>

        <div>
          <Panel title="Actions">
            <div className="flex" style={{ flexDirection: 'column', gap: 8 }}>
              {app.status === 'ready' && (
                <>
                  <Button onClick={() => handleAction('approve')} disabled={actionLoading}>
                    {Icons.check} Approve for Application
                  </Button>
                  <Button variant="danger" onClick={() => handleAction('reject')} disabled={actionLoading}>
                    {Icons.x} Reject
                  </Button>
                </>
              )}
              {app.status === 'approved' && (
                <>
                  <Button onClick={() => handleAction('open')} disabled={actionLoading}>
                    {Icons.send} Open Application
                  </Button>
                  <Button variant="danger" onClick={() => handleAction('reject')} disabled={actionLoading}>
                    {Icons.x} Reject
                  </Button>
                </>
              )}
              {app.status === 'application_opened' && (
                <>
                  <Button onClick={() => handleAction('mark_applied')} disabled={actionLoading}>
                    {Icons.check} Mark as Applied
                  </Button>
                  <Button variant="danger" onClick={() => handleAction('reject')} disabled={actionLoading}>
                    {Icons.x} Reject
                  </Button>
                </>
              )}
              {app.status === 'applied' && (
                <>
                  <Button variant="secondary" onClick={() => handleAction('reject')} disabled={actionLoading}>
                    {Icons.x} Reject
                  </Button>
                  <Button variant="secondary" onClick={() => handleAction('withdraw')} disabled={actionLoading}>
                    {Icons.refresh} Withdraw
                  </Button>
                </>
              )}
              {['screening', 'interview', 'offer'].includes(app.status) && (
                <Button variant="secondary" onClick={() => handleAction('withdraw')} disabled={actionLoading}>
                  {Icons.refresh} Withdraw
                </Button>
              )}
              {app.status === 'offer' && (
                <Button onClick={() => handleAction('mark_applied')} disabled={actionLoading}>
                  {Icons.check} Accept Offer
                </Button>
              )}
            </div>

            <div className="field mt-16">
              <div className="label">Notes</div>
              <TextArea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this application..."
                rows={3}
              />
              <Button size="sm" onClick={async () => {
                try {
                  await api(`/api/applications/${app.id}`, { method: 'PATCH', body: { notes } });
                  toast('Notes updated', 'success');
                } catch (e) {
                  toast(e.message, 'error');
                }
              }} disabled={actionLoading}>
                Save Notes
              </Button>
            </div>
          </Panel>

          <Panel title="Timeline">
            <div className="timeline" style={{ borderLeft: '2px solid var(--border)', paddingLeft: 16 }}>
              <div className="timeline-item" style={{ position: 'relative', marginBottom: 16, paddingLeft: 12 }}>
                <div className="timeline-dot" style={{ position: 'absolute', left: -22, top: 4, width: 12, height: 12, borderRadius: '50%', background: 'var(--primary)' }} />
                <div className="muted" style={{ fontSize: 12 }}>{fmtDate(app.created_at)}</div>
                <div><strong>Application Created</strong></div>
                <div className="muted" style={{ fontSize: 13 }}>Status: {app.status.replace('_', ' ')}</div>
              </div>
              {app.applied_at && (
                <div className="timeline-item" style={{ position: 'relative', marginBottom: 16, paddingLeft: 12 }}>
                  <div className="timeline-dot" style={{ position: 'absolute', left: -22, top: 4, width: 12, height: 12, borderRadius: '50%', background: 'var(--green)' }} />
                  <div className="muted" style={{ fontSize: 12 }}>{fmtDate(app.applied_at)}</div>
                  <div><strong>Marked as Applied</strong></div>
                </div>
              )}
              {app.updated_at !== app.created_at && app.updated_at !== app.applied_at && (
                <div className="timeline-item" style={{ position: 'relative', paddingLeft: 12 }}>
                  <div className="timeline-dot" style={{ position: 'absolute', left: -22, top: 4, width: 12, height: 12, borderRadius: '50%', background: 'var(--amber)' }} />
                  <div className="muted" style={{ fontSize: 12 }}>{fmtDate(app.updated_at)}</div>
                  <div><strong>Last Updated</strong></div>
                </div>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </Layout>
  );
}