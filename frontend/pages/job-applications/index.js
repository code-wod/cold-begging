import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import {
  Button, Empty, Field, Icons, Input, Modal, Panel, Spinner, StatusBadge, fmtDate, fmtRel, useToast,
} from '../../components/ui';

const STATUS_TONES = {
  preparing: 'gray', analyzing: 'blue', filling: 'blue',
  needs_review: 'amber', ready: 'green', submitting: 'teal',
  submitted: 'green', failed: 'red', cancelled: 'gray',
};

export default function JobApplications() {
  const { user } = useAuth();
  const toast = useToast();
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [urlInput, setUrlInput] = useState('');
  const [creating, setCreating] = useState(false);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (user) fetchApplications();
  }, [user, filter]);

  const fetchApplications = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '50' });
      if (filter) params.append('status', filter);
      const data = await api(`/api/job-applications?${params}`);
      setApplications(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!urlInput.trim()) return;
    setCreating(true);
    try {
      const result = await api('/api/job-applications', {
        method: 'POST',
        body: { job_url: urlInput.trim() },
      });
      toast('Application created. Starting autofill...', 'success');
      setUrlInput('');

      // Auto-start the autofill
      try {
        await api(`/api/job-applications/${result.id}/start`, { method: 'POST' });
        toast('Autofill task queued', 'success');
      } catch (e) {
        toast('Created but could not start autofill: ' + e.message, 'error');
      }

      fetchApplications();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setCreating(false);
    }
  };

  return (
    <Layout title="Job Applications" breadcrumb={<Link href="/job-applications">Job Applications</Link>}>
      <div className="page-head">
        <h1>Job Application Autofill</h1>
        <div className="muted">Paste a job URL and we'll analyze and fill the application for you.</div>
      </div>

      {/* Apply Section */}
      <Panel title="Apply to a Job">
        <div className="flex" style={{ gap: 8 }}>
          <div style={{ flex: 1 }}>
            <Input
              type="url"
              placeholder="https://boards.greenhouse.io/company/jobs/123"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreate(); }}
            />
          </div>
          <Button onClick={handleCreate} disabled={creating || !urlInput.trim()}>
            {creating ? <Spinner /> : Icons.play} Prepare Application
          </Button>
        </div>
        <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
          Supported: Greenhouse, Lever, Ashby, Workday, and more.
          Make sure you have a <Link href="/job-profile">Job Profile</Link> set up first.
        </div>
      </Panel>

      {/* Recent Applications */}
      <Panel title={`Recent Applications (${total})`} actions={
        <div className="flex" style={{ gap: 6 }}>
          <Button size="sm" variant={filter === '' ? 'primary' : 'secondary'} onClick={() => setFilter('')}>All</Button>
          <Button size="sm" variant={filter === 'needs_review' ? 'primary' : 'secondary'} onClick={() => setFilter('needs_review')}>Needs Review</Button>
          <Button size="sm" variant={filter === 'submitted' ? 'primary' : 'secondary'} onClick={() => setFilter('submitted')}>Submitted</Button>
        </div>
      }>
        {loading ? <Spinner /> : applications.length === 0 ? (
          <Empty message="No applications yet. Paste a job URL above to get started." />
        ) : (
          <table className="dense">
            <thead>
              <tr>
                <th>Company</th>
                <th>Role</th>
                <th>ATS</th>
                <th>Status</th>
                <th>Fields</th>
                <th>Created</th>
                <th style={{ width: 60 }}></th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app) => (
                <tr key={app.id}>
                  <td><b>{app.company_name || '—'}</b></td>
                  <td>{app.role_title || '—'}</td>
                  <td><span className="badge gray">{app.ats_platform || 'unknown'}</span></td>
                  <td><StatusBadge status={app.status} tone={STATUS_TONES[app.status] || 'gray'} /></td>
                  <td>
                    {app.total_fields > 0 ? (
                      <span className="muted" style={{ fontSize: 12 }}>
                        {app.auto_filled}/{app.total_fields} filled
                        {app.needs_review > 0 && ` · ${app.needs_review} review`}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="muted">{fmtRel(app.created_at)}</td>
                  <td>
                    <Link href={`/job-applications/${app.id}`} className="btn ghost sm">
                      {Icons.eye}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </Layout>
  );
}
