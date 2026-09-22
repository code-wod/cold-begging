import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, useToast, Icons, Button, Field, Input } from '../components/ui';

export default function JobPortals() {
  const { user } = useAuth();
  const toast = useToast();
  const [portals, setPortals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState({});
  const [searching, setSearching] = useState({});

  useEffect(() => {
    fetchPortals();
  }, []);

  const fetchPortals = async () => {
    setLoading(true);
    try {
      const data = await api('/api/job-portals');
      setPortals(data);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (platform) => {
    setConnecting(prev => ({ ...prev, [platform]: true }));
    try {
      const result = await api(`/api/job-portals/${platform}/connect`, {
        method: 'POST',
        body: { headless: false }
      });
      if (result.status === 'connected') {
        toast(`Connected to ${platform}! Auto-search started.`, 'success');
      } else {
        toast(result.message || `Login required for ${platform}`, 'info');
      }
      fetchPortals();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setConnecting(prev => ({ ...prev, [platform]: false }));
    }
  };

  const handleSearch = async (platform) => {
    setSearching(prev => ({ ...prev, [platform]: true }));
    try {
      const data = await api('/api/agent/search-auto', { method: 'POST' });
      toast(data.message || `Search started on ${platform}`, 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSearching(prev => ({ ...prev, [platform]: false }));
    }
  };

  const handleVerify = async (platform) => {
    try {
      const result = await api(`/api/job-portals/${platform}/verify`, { method: 'POST' });
      toast(result.message || `Session ${result.status}`, result.status === 'valid' ? 'success' : 'info');
      fetchPortals();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const handleDisconnect = async (platform) => {
    if (!confirm(`Disconnect from ${platform}? This will clear your browser session.`)) return;
    try {
      const result = await api(`/api/job-portals/${platform}/disconnect`, { method: 'POST' });
      toast(result.message || `Disconnected from ${platform}`, 'success');
      fetchPortals();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'green';
      case 'login_required': return 'amber';
      case 'expired': return 'red';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const getCapabilities = (caps) => {
    const items = [];
    if (caps.job_search) items.push('Job Search');
    if (caps.easy_apply) items.push('Easy Apply');
    if (caps.one_click_apply) items.push('One-Click Apply');
    if (caps.multi_step_form) items.push('Multi-step Forms');
    if (caps.resume_upload) items.push('Resume Upload');
    if (caps.cover_letter) items.push('Cover Letter');
    if (caps.screening_questions) items.push('Screening Q&A');
    return items;
  };

  if (loading) {
    return <Layout title="Job Portals" breadcrumb={<Link href="/job-portals">Job Portals</Link>}><Spinner /></Layout>;
  }

  return (
    <Layout title="Job Portals" breadcrumb={<Link href="/job-portals">Job Portals</Link>}>
      <div className="page-head">
        <h1>Job Portal Connections</h1>
        <div className="muted">Connect to job platforms to enable automated job search and applications.</div>
      </div>

      <Panel title="Supported Platforms" bodyClassName="portals-grid">
        {portals.map((portal) => (
          <div key={portal.platform} className="portal-card panel">
            <div className="flex justify-between" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 16, textTransform: 'capitalize' }}>{portal.platform}</h3>
              <StatusBadge status={portal.status.replace('_', ' ')} tone={getStatusColor(portal.status)} />
            </div>

            <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
              {portal.capabilities ? getCapabilities(portal.capabilities).join(' · ') : 'Loading...'}
            </div>

            {portal.last_verified && (
              <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
                Last verified: {new Date(portal.last_verified).toLocaleString()}
              </div>
            )}

            <div className="flex justify-between mt-16" style={{ paddingTop: 12, borderTop: '1px solid var(--border)' }}>
              {portal.status === 'connected' ? (
                <>
                  <Button size="sm" onClick={() => handleSearch(portal.platform)} disabled={searching[portal.platform]}>
                    {searching[portal.platform] ? <Spinner /> : Icons.search} Search & Apply
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleVerify(portal.platform)}>
                    {Icons.refresh} Verify
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => handleDisconnect(portal.platform)}>
                    {Icons.unlink} Disconnect
                  </Button>
                </>
              ) : (
                <Button 
                  size="sm" 
                  onClick={() => handleConnect(portal.platform)}
                  disabled={connecting[portal.platform]}
                >
                  {connecting[portal.platform] ? <Spinner /> : 'Connect'}
                </Button>
              )}
            </div>
          </div>
        ))}
      </Panel>
    </Layout>
  );
}