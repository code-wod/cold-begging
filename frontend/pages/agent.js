import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, useToast, Icons, Button, Progress, Field, Input } from '../components/ui';

export default function AgentDashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [searchParams, setSearchParams] = useState({
    platforms: [],
    keywords: [],
    locations: [],
    experience_min: '',
    experience_max: '',
    remote: false,
    job_types: [],
    salary_min: '',
    max_results: 50
  });
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await api('/api/agent/status');
      setStatus(data);
    } catch (e) {
      // Ignore errors for now
    } finally {
      setLoading(false);
    }
  };

  const handleControl = async (action) => {
    setActionLoading(true);
    try {
      await api('/api/agent/control', { method: 'POST', body: { action } });
      toast(`Agent ${action} requested`, 'success');
      fetchStatus();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSearch = async () => {
    if (searchParams.keywords.length === 0) {
      toast('Please add at least one keyword', 'error');
      return;
    }
    setSearchLoading(true);
    try {
      const data = await api('/api/agent/search', { method: 'POST', body: searchParams });
      setSearchResults(data);
      toast('Search queued for connected platforms', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSearchLoading(false);
    }
  };

  const addKeyword = () => {
    const keyword = prompt('Enter keyword (e.g., "Backend Engineer"):');
    if (keyword && keyword.trim()) {
      setSearchParams(prev => ({
        ...prev,
        keywords: [...new Set([...prev.keywords, keyword.trim()])]
      }));
    }
  };

  const removeKeyword = (keyword) => {
    setSearchParams(prev => ({
      ...prev,
      keywords: prev.keywords.filter(k => k !== keyword)
    }));
  };

  const addLocation = () => {
    const location = prompt('Enter location (e.g., "Remote", "San Francisco"):');
    if (location && location.trim()) {
      setSearchParams(prev => ({
        ...prev,
        locations: [...new Set([...prev.locations, location.trim()])]
      }));
    }
  };

  const removeLocation = (location) => {
    setSearchParams(prev => ({
      ...prev,
      locations: prev.locations.filter(l => l !== location)
    }));
  };

  if (loading) {
    return <Layout title="Agent Control" breadcrumb={<Link href="/agent">Agent Control</Link>}><Spinner /></Layout>;
  }

  return (
    <Layout title="Agent Control" breadcrumb={<Link href="/agent">Agent Control</Link>}>
      <div className="page-head">
        <h1>Job Application Agent</h1>
        <div className="muted">Configure and monitor your automated job application agent.</div>
      </div>

      {/* Status Overview */}
      <div className="grid stats" style={{ marginBottom: 16 }}>
        <div className="panel stat-card">
          <div className="stat-label">Daily Limit</div>
          <div className="stat-value">{status?.daily_limit || 15}</div>
          <div className="muted" style={{ fontSize: 12 }}>Used: {status?.daily_used || 0}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Min Match Score</div>
          <div className="stat-value">{status?.min_match_score || 80}%</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Mode</div>
          <div className="stat-value">{status?.dry_run ? 'Dry Run' : 'Live'}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Workers</div>
          <div className="stat-value">{status?.workers || 0}</div>
        </div>
      </div>

      {/* Control Panel */}
      <Panel title="Agent Control" actions={
        <div className="flex" style={{ gap: 8 }}>
          <Button 
            variant={status?.running ? 'secondary' : 'primary'} 
            onClick={() => handleControl('start')}
            disabled={actionLoading || status?.running}
          >
            {Icons.play} Start
          </Button>
          <Button 
            variant={status?.running ? 'primary' : 'secondary'} 
            onClick={() => handleControl('pause')}
            disabled={actionLoading || !status?.running}
          >
            {Icons.pause} Pause
          </Button>
          <Button 
            variant="danger" 
            onClick={() => handleControl('stop')}
            disabled={actionLoading || !status?.running}
          >
            {Icons.stop} Stop
          </Button>
        </div>
      }>
        <div className="flex justify-between mb-16">
          <StatusBadge status={status?.running ? 'Running' : 'Stopped'} tone={status?.running ? 'green' : 'gray'} />
          <div className="muted">
            Dry Run: {status?.dry_run ? 'Enabled' : 'Disabled'}
          </div>
        </div>

        <div className="field" style={{ marginBottom: 12 }}>
          <div className="label">Daily Application Limit</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input 
              type="number" 
              min="1" 
              max="100"
              defaultValue={status?.daily_limit || 15}
              style={{ width: 80, padding: 8 }}
            />
            <Progress percent={((status?.daily_used || 0) / (status?.daily_limit || 15)) * 100} style={{ flex: 1 }} />
            <span className="muted">{status?.daily_used || 0} / {status?.daily_limit || 15}</span>
          </div>
        </div>

        <div className="field">
          <div className="label">Minimum Match Score</div>
          <input 
            type="range" 
            min="50" 
            max="100"
            defaultValue={status?.min_match_score || 80}
            style={{ width: '100%' }}
          />
          <div className="muted" style={{ fontSize: 12 }}>Applications below this score will be skipped</div>
        </div>
      </Panel>

      {/* Job Search */}
      <Panel title="Search Jobs" bodyClassName="search-form">
        <div className="field" style={{ marginBottom: 12 }}>
          <div className="label">Keywords <button type="button" onClick={addKeyword} style={{ marginLeft: 8, fontSize: 12 }}>+ Add</button></div>
          <div className="flex flex-wrap gap-4">
            {searchParams.keywords.map(k => (
              <span key={k} className="badge blue" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                {k}
                <button onClick={() => removeKeyword(k)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, fontSize: 14, lineHeight: 1 }}>
                  {Icons.x}
                </button>
              </span>
            ))}
            {searchParams.keywords.length === 0 && <span className="muted">No keywords added</span>}
          </div>
        </div>

        <div className="field" style={{ marginBottom: 12 }}>
          <div className="label">Locations <button type="button" onClick={addLocation} style={{ marginLeft: 8, fontSize: 12 }}>+ Add</button></div>
          <div className="flex flex-wrap gap-4">
            {searchParams.locations.map(l => (
              <span key={l} className="badge teal" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                {l}
                <button onClick={() => removeLocation(l)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, fontSize: 14, lineHeight: 1 }}>
                  {Icons.x}
                </button>
              </span>
            ))}
            {searchParams.locations.length === 0 && <span className="muted">No locations added</span>}
          </div>
        </div>

        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
          <Field label="Experience (Min)">
            <Input
              type="number"
              min="0"
              max="20"
              placeholder="0"
              value={searchParams.experience_min}
              onChange={(e) => setSearchParams({ ...searchParams, experience_min: e.target.value })}
            />
          </Field>
          <Field label="Experience (Max)">
            <Input
              type="number"
              min="0"
              max="20"
              placeholder="20"
              value={searchParams.experience_max}
              onChange={(e) => setSearchParams({ ...searchParams, experience_max: e.target.value })}
            />
          </Field>
          <Field label="Min Salary">
            <Input
              type="number"
              placeholder="100000"
              value={searchParams.salary_min}
              onChange={(e) => setSearchParams({ ...searchParams, salary_min: e.target.value })}
            />
          </Field>
          <Field label="Max Results">
            <Input
              type="number"
              min="1"
              max="200"
              value={searchParams.max_results}
              onChange={(e) => setSearchParams({ ...searchParams, max_results: e.target.value })}
            />
          </Field>
        </div>

        <div className="field">
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={searchParams.remote}
              onChange={(e) => setSearchParams({ ...searchParams, remote: e.target.checked })}
            />
            <span>Remote only</span>
          </label>
        </div>

        <Button onClick={handleSearch} disabled={searchLoading || searchParams.keywords.length === 0}>
          {searchLoading ? <Spinner /> : Icons.search} Search Jobs
        </Button>

        {searchResults && (
          <div className="mt-16">
            <div className="label">Search Results</div>
            <pre style={{ background: 'var(--surface)', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto' }}>
              {JSON.stringify(searchResults, null, 2)}
            </pre>
          </div>
        )}
      </Panel>

      {/* Queue Stats */}
      <Panel title="Task Queue">
        <div className="flex" style={{ gap: 16, flexWrap: 'wrap' }}>
          <div className="panel stat-card">
            <div className="stat-label">Pending</div>
            <div className="stat-value">{status?.queue_stats?.pending || 0}</div>
          </div>
          <div className="panel stat-card">
            <div className="stat-label">Processing</div>
            <div className="stat-value">{status?.queue_stats?.processing || 0}</div>
          </div>
          <div className="panel stat-card">
            <div className="stat-label">Completed</div>
            <div className="stat-value">{status?.queue_stats?.completed || 0}</div>
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={async () => {
          try {
            const result = await api('/api/agent/queue/cleanup', { method: 'POST' });
            toast(`Cleaned up ${result.cleaned} stale tasks`, 'success');
          } catch (e) {
            toast(e.message, 'error');
          }
        }}>
          Clean Stale Tasks
        </Button>
      </Panel>
    </Layout>
  );
}