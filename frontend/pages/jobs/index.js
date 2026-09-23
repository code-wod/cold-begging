import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, fmtDate, useToast, Icons, Progress, Button, Field, Input, Select, TextArea, Modal, Confirm } from '../../components/ui';

export default function Jobs() {
  const { user } = useAuth();
  const toast = useToast();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [filters, setFilters] = useState({
    source: '',
    location: '',
    remote_type: '',
    employment_type: '',
    experience_level: '',
    company: '',
    min_salary: '',
    search: '',
    status: 'active'
  });
  const [sources, setSources] = useState([]);
  const [importModal, setImportModal] = useState(false);
  const [importUrl, setImportUrl] = useState('');
  const [importLoading, setImportLoading] = useState(false);
  const [matchModal, setMatchModal] = useState(false);
  const [matchJob, setMatchJob] = useState(null);
  const [matchResult, setMatchResult] = useState(null);
  const [matchLoading, setMatchLoading] = useState(false);

  useEffect(() => {
    fetchJobs();
    fetchSources();
  }, [page, filters]);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
      Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v); });
      const data = await api(`/api/jobs?${params}`);
      setJobs(data.items);
      setTotal(data.total);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchSources = async () => {
    try {
      const data = await api('/api/jobs/sources');
      setSources(data);
    } catch (e) {
      console.error('Failed to fetch sources', e);
    }
  };

  const handleImport = async () => {
    if (!importUrl.trim()) return;
    setImportLoading(true);
    try {
      const result = await api('/api/jobs/import', { method: 'POST', body: { url: importUrl } });
      toast(`Job imported! Match score: ${result.match_score}%`, 'success');
      setImportModal(false);
      setImportUrl('');
      fetchJobs();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setImportLoading(false);
    }
  };

  const handleMatch = async (job) => {
    setMatchJob(job);
    setMatchLoading(true);
    try {
      const result = await api(`/api/jobs/${job.id}/match`, { method: 'POST' });
      setMatchResult(result);
      setMatchModal(true);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setMatchLoading(false);
    }
  };

  const handlePrepare = async (job) => {
    try {
      const result = await api(`/api/jobs/${job.id}/prepare`, { method: 'POST' });
      toast('Application prepared! Check Applications queue.', 'success');
      fetchJobs();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 70) return 'teal';
    if (score >= 60) return 'amber';
    return 'red';
  };

  return (
    <Layout title="Jobs" breadcrumb={<Link href="/jobs">Jobs</Link>}>
      <div className="page-head">
        <h1>Job Discovery</h1>
        <div className="muted">Discover, analyze, and prepare applications for job opportunities.</div>
      </div>

      <div className="flex" style={{ gap: 16, marginBottom: 16 }}>
        <Button onClick={() => setImportModal(true)} style={{ flex: '0 0 auto' }}>
          {Icons.plus} Import Job URL
        </Button>
      </div>

      {/* Filters Panel */}
      <Panel title="Filters" bodyClassName="filters-panel">
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <Field label="Search">
            <Input
              placeholder="Title, company, skills..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Source">
            <Select
              options={['', ...sources.map(s => s.name)]}
              value={filters.source}
              onChange={(e) => setFilters({ ...filters, source: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Location">
            <Input
              placeholder="City, state, country..."
              value={filters.location}
              onChange={(e) => setFilters({ ...filters, location: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Remote Type">
            <Select
              options={['', 'remote', 'hybrid', 'onsite']}
              value={filters.remote_type}
              onChange={(e) => setFilters({ ...filters, remote_type: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Employment Type">
            <Select
              options={['', 'full_time', 'part_time', 'contract', 'internship']}
              value={filters.employment_type}
              onChange={(e) => setFilters({ ...filters, employment_type: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Experience Level">
            <Select
              options={['', 'entry', 'junior', 'mid', 'senior', 'lead', 'principal']}
              value={filters.experience_level}
              onChange={(e) => setFilters({ ...filters, experience_level: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Company">
            <Input
              placeholder="Company name..."
              value={filters.company}
              onChange={(e) => setFilters({ ...filters, company: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Min Salary">
            <Input
              type="number"
              placeholder="100000"
              value={filters.min_salary}
              onChange={(e) => setFilters({ ...filters, min_salary: e.target.value, page: 1 })}
            />
          </Field>
          <Field label="Status">
            <Select
              options={['active', 'expired', 'filled', 'archived']}
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value, page: 1 })}
            />
          </Field>
        </div>
      </Panel>

      {/* Jobs List */}
      <Panel title={`Jobs (${total})`} actions={
        total > 0 && (
          <div className="flex" style={{ gap: 8 }}>
            <Button variant="secondary" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
              {Icons.up} Prev
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= total}>
              Next {Icons.up}
            </Button>
          </div>
        )
      }>
        {loading ? (
          <Spinner />
        ) : jobs.length === 0 ? (
          <Empty message="No jobs found. Import a job URL to get started." />
        ) : (
          <div className="jobs-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 16 }}>
            {jobs.map((job) => (
              <div key={job.id} className="panel job-card" style={{ flexDirection: 'column', height: '100%' }}>
                <div className="flex justify-between" style={{ marginBottom: 8 }}>
                  <div>
                    <span className="badge gray">{job.source}</span>
                    {job.remote_type && <span className="badge blue" style={{ marginLeft: 8 }}>{job.remote_type}</span>}
                    {job.employment_type && <span className="badge teal" style={{ marginLeft: 8 }}>{job.employment_type}</span>}
                    {job.experience_level && <span className="badge amber" style={{ marginLeft: 8 }}>{job.experience_level}</span>}
                  </div>
                </div>
                <h3 style={{ fontSize: 16, marginBottom: 4 }}>{job.title}</h3>
                <div className="muted" style={{ fontSize: 14, marginBottom: 8 }}>{job.company_name}</div>
                {job.location && <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>{Icons.search} {job.location}</div>}
                {job.salary_min && job.salary_max && (
                  <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>
                    ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()} {job.currency}
                  </div>
                )}
                {job.skills.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {job.skills.slice(0, 6).map((skill) => (
                      <span key={skill} className="badge gray" style={{ fontSize: 11 }}>{skill}</span>
                    ))}
                    {job.skills.length > 6 && <span className="badge gray" style={{ fontSize: 11 }}>+{job.skills.length - 6} more</span>}
                  </div>
                )}
                <div className="flex justify-between mt-16" style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <Link href={`/jobs/${job.id}`} className="btn sm secondary">View Details</Link>
                  <div className="flex" style={{ gap: 8 }}>
                    <Button size="sm" variant="secondary" onClick={() => handleMatch(job)} disabled={matchLoading}>
                      {Icons.refresh} Match
                    </Button>
                    <Button size="sm" onClick={() => handlePrepare(job)}>
                      {Icons.send} Prepare
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {/* Import Modal */}
      <Modal open={importModal} title="Import Job from URL" onClose={() => setImportModal(false)}>
        <Field label="Job URL">
          <Input
            type="url"
            placeholder="https://example.com/jobs/backend-engineer"
            value={importUrl}
            onChange={(e) => setImportUrl(e.target.value)}
          />
          <div className="help">Supports Greenhouse, Lever, Ashby, company career pages, LinkedIn, Naukri, Wellfound, and generic URLs.</div>
        </Field>
        <div className="mt-16 flex justify-between">
          <Button variant="secondary" onClick={() => setImportModal(false)}>Cancel</Button>
          <Button onClick={handleImport} disabled={importLoading}>{importLoading ? <Spinner /> : 'Import'}</Button>
        </div>
      </Modal>

      {/* Match Result Modal */}
      <Modal open={matchModal} title={`Match Analysis: ${matchJob?.title}`} onClose={() => { setMatchModal(false); setMatchResult(null); }}>
        {matchResult && (
          <div>
            <div className="flex justify-between mb-16">
              <div>
                <StatusBadge status={matchResult.recommendation.replace('_', ' ')} tone={getScoreColor(matchResult.match_score)} />
              </div>
              <div className="flex" style={{ alignItems: 'center', gap: 16 }}>
                <div className="flex" style={{ alignItems: 'center', gap: 8 }}>
                  <span>Match Score:</span>
                  <Progress percent={matchResult.match_score} style={{ width: 120 }} />
                  <span className="badge" style={{ background: `var(--${getScoreColor(matchResult.match_score)})` }}>{matchResult.match_score}%</span>
                </div>
              </div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Reasoning</div>
              <div className="muted">{matchResult.reasoning_summary}</div>
            </div>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              <div>
                <div className="label">Matched Skills</div>
                {matchResult.matched_skills.length > 0 ? (
                  <div className="flex flex-wrap gap-4">
                    {matchResult.matched_skills.map(s => <span key={s} className="badge green">{s}</span>)}
                  </div>
                ) : <div className="muted">None</div>}
              </div>
              <div>
                <div className="label">Missing Skills</div>
                {matchResult.missing_skills.length > 0 ? (
                  <div className="flex flex-wrap gap-4">
                    {matchResult.missing_skills.map(s => <span key={s} className="badge red">{s}</span>)}
                  </div>
                ) : <div className="muted">None</div>}
              </div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Risk Factors</div>
              {matchResult.risk_factors.length > 0 ? (
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {matchResult.risk_factors.map((r, i) => <li key={i} className="muted" style={{ fontSize: 13 }}>{r}</li>)}
                </ul>
              ) : <div className="muted">None identified</div>}
            </div>
            <div className="mt-16 flex justify-between">
              <Button variant="secondary" onClick={() => { setMatchModal(false); setMatchResult(null); }}>Close</Button>
              <Button onClick={() => handlePrepare(matchJob)}>Prepare Application</Button>
            </div>
          </div>
        )}
        {!matchResult && !matchLoading && <div className="empty">No match data</div>}
        {matchLoading && <Spinner />}
      </Modal>
    </Layout>
  );
}