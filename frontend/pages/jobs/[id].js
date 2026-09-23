import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, fmtDate, useToast, Icons, Progress, Button, Modal, Confirm } from '../../components/ui';

export default function JobDetail() {
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [matchResult, setMatchResult] = useState(null);
  const [matchLoading, setMatchLoading] = useState(false);
  const [prepareLoading, setPrepareLoading] = useState(false);
  const [application, setApplication] = useState(null);
  const [appLoading, setAppLoading] = useState(false);

  const { id } = router.query;

  useEffect(() => {
    if (id) {
      fetchJob();
      checkApplication();
    }
  }, [id]);

  const fetchJob = async () => {
    setLoading(true);
    try {
      const data = await api(`/api/jobs/${id}`);
      setJob(data);
    } catch (e) {
      toast(e.message, 'error');
      router.push('/jobs');
    } finally {
      setLoading(false);
    }
  };

  const checkApplication = async () => {
    try {
      const data = await api(`/api/applications?status=ready&page=1&page_size=100`);
      const existing = data.items.find(a => a.job_id === parseInt(id));
      if (existing) setApplication(existing);
    } catch (e) {
      console.error('Failed to check application', e);
    }
  };

  const handleMatch = async () => {
    if (!job) return;
    setMatchLoading(true);
    try {
      const result = await api(`/api/jobs/${job.id}/match`, { method: 'POST' });
      setMatchResult(result);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setMatchLoading(false);
    }
  };

  const handlePrepare = async () => {
    if (!job) return;
    setPrepareLoading(true);
    try {
      const result = await api(`/api/jobs/${job.id}/prepare`, { method: 'POST' });
      toast('Application prepared! Check Applications queue.', 'success');
      checkApplication();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setPrepareLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 70) return 'teal';
    if (score >= 60) return 'amber';
    return 'red';
  };

  if (loading) {
    return <Layout title="Job Detail" breadcrumb={<Link href="/jobs">Jobs</Link>}><Spinner /></Layout>;
  }

  if (!job) {
    return <Layout title="Job Detail" breadcrumb={<Link href="/jobs">Jobs</Link>}><Empty message="Job not found" /></Layout>;
  }

  return (
    <Layout title={job.title} breadcrumb={<><Link href="/jobs">Jobs</Link> / <span>{job.title}</span></>}>
      <div className="page-head">
        <div>
          <h1>{job.title}</h1>
          <div className="muted">{job.company_name} · {job.location || 'Location not specified'}</div>
        </div>
        <div className="flex" style={{ gap: 8, marginTop: 8 }}>
          <span className="badge gray">{job.source}</span>
          {job.remote_type && <span className="badge blue">{job.remote_type}</span>}
          {job.employment_type && <span className="badge teal">{job.employment_type}</span>}
          {job.experience_level && <span className="badge amber">{job.experience_level}</span>}
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 380px', gap: 16 }}>
        <div>
          <Panel title="Description">
            <div className="prose" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
              {job.description}
            </div>
          </Panel>

          {job.requirements && (
            <Panel title="Requirements">
              <div className="prose" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {job.requirements}
              </div>
            </Panel>
          )}

          {job.skills.length > 0 && (
            <Panel title="Required Skills">
              <div className="flex flex-wrap gap-4">
                {job.skills.map((skill) => (
                  <span key={skill} className="badge gray">{skill}</span>
                ))}
              </div>
            </Panel>
          )}

          {job.application_url && (
            <Panel title="Application">
              <div className="muted" style={{ marginBottom: 8 }}>Apply directly on the company's site:</div>
              <a href={job.application_url} target="_blank" rel="noopener noreferrer" className="btn">
                {Icons.send} Open Application
              </a>
            </Panel>
          )}
        </div>

        <div>
          <Panel title="Job Details">
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Company</div>
              <div>{job.company_name}</div>
              {job.company_url && <a href={job.company_url} target="_blank" rel="noopener" className="muted" style={{ fontSize: 13 }}>Website</a>}
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Location</div>
              <div>{job.location || 'Not specified'}</div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Remote Type</div>
              <div>{job.remote_type || 'Not specified'}</div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Employment Type</div>
              <div>{job.employment_type || 'Not specified'}</div>
            </div>
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Experience Level</div>
              <div>{job.experience_level || 'Not specified'}</div>
            </div>
            {job.salary_min && job.salary_max && (
              <div className="field" style={{ marginBottom: 12 }}>
                <div className="label">Salary Range</div>
                <div>${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()} {job.currency}</div>
              </div>
            )}
            <div className="field" style={{ marginBottom: 12 }}>
              <div className="label">Posted</div>
              <div>{job.posted_at ? fmtDate(job.posted_at) : 'Not specified'}</div>
            </div>
            <div className="field">
              <div className="label">Discovered</div>
              <div>{fmtDate(job.discovered_at)}</div>
            </div>
          </Panel>

          <Panel title="AI Match Analysis" actions={
            <Button size="sm" onClick={handleMatch} disabled={matchLoading || !job}>
              {matchLoading ? <Spinner /> : Icons.refresh} Run Match
            </Button>
          }>
            {matchResult ? (
              <div>
                <div className="flex justify-between mb-16">
                  <div>
                    <StatusBadge status={matchResult.recommendation.replace('_', ' ')} tone={getScoreColor(matchResult.match_score)} />
                  </div>
                  <div className="flex" style={{ alignItems: 'center', gap: 8 }}>
                    <Progress percent={matchResult.match_score} style={{ width: 100 }} />
                    <span className="badge" style={{ background: `var(--${getScoreColor(matchResult.match_score)})`, fontSize: 14 }}>{matchResult.match_score}%</span>
                  </div>
                </div>
                <div className="field" style={{ marginBottom: 12 }}>
                  <div className="label">Recommendation</div>
                  <div className="muted">{matchResult.recommendation.replace('_', ' ')}</div>
                </div>
                <div className="field" style={{ marginBottom: 12 }}>
                  <div className="label">Reasoning</div>
                  <div className="muted">{matchResult.reasoning_summary}</div>
                </div>
                <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                  <div>
                    <div className="label" style={{ fontSize: 12 }}>Matched Skills</div>
                    {matchResult.matched_skills.length > 0 ? (
                      <div className="flex flex-wrap gap-4">
                        {matchResult.matched_skills.map(s => <span key={s} className="badge green" style={{ fontSize: 11 }}>{s}</span>)}
                      </div>
                    ) : <div className="muted" style={{ fontSize: 12 }}>None</div>}
                  </div>
                  <div>
                    <div className="label" style={{ fontSize: 12 }}>Missing Skills</div>
                    {matchResult.missing_skills.length > 0 ? (
                      <div className="flex flex-wrap gap-4">
                        {matchResult.missing_skills.map(s => <span key={s} className="badge red" style={{ fontSize: 11 }}>{s}</span>)}
                      </div>
                    ) : <div className="muted" style={{ fontSize: 12 }}>None</div>}
                  </div>
                </div>
                <div className="field" style={{ marginBottom: 12 }}>
                  <div className="label" style={{ fontSize: 12 }}>Risk Factors</div>
                  {matchResult.risk_factors.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {matchResult.risk_factors.map((r, i) => <li key={i} className="muted" style={{ fontSize: 12 }}>{r}</li>)}
                    </ul>
                  ) : <div className="muted" style={{ fontSize: 12 }}>None</div>}
                </div>
                <div className="mt-16 flex justify-between">
                  {application ? (
                    <Link href={`/applications/${application.id}`} className="btn secondary">
                      View Application
                    </Link>
                  ) : (
                    <Button onClick={handlePrepare} disabled={prepareLoading || matchResult.match_score < 70}>
                      {prepareLoading ? <Spinner /> : 'Prepare Application'}
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="empty" style={{ padding: 16 }}>Click "Run Match" to analyze this job against your profile.</div>
            )}
          </Panel>
        </div>
      </div>
    </Layout>
  );
}