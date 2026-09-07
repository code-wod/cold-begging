import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Empty, Panel, Spinner, StatusBadge, useToast, Icons, Button, Modal, Field, Input } from '../components/ui';

export default function JobPortals() {
  const { user } = useAuth();
  const toast = useToast();
  const [portals, setPortals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState({});
  const [modal, setModal] = useState(null);

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
      toast(`Connecting to ${platform}...`, 'info');
      setModal({ platform, taskId: result.id, type: 'connect' });
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setConnecting(prev => ({ ...prev, [platform]: false }));
    }
  };

  const handleVerify = async (platform) => {
    try {
      const result = await api(`/api/job-portals/${platform}/verify`, { method: 'POST' });
      toast('Verifying session...', 'info');
      setModal({ platform, taskId: result.id, type: 'verify' });
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const handleDisconnect = async (platform) => {
    if (!confirm(`Disconnect from ${platform}? This will clear your browser session.`)) return;
    try {
      const result = await api(`/api/job-portals/${platform}/disconnect`, { method: 'POST' });
      toast(`Disconnecting from ${platform}...`, 'info');
      setModal({ platform, taskId: result.id, type: 'disconnect' });
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const handleOpen = async (platform) => {
    try {
      const result = await api(`/api/job-portals/${platform}/open`, { method: 'GET' });
      window.open(result.url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const checkTaskStatus = async (taskId) => {
    try {
      const result = await api(`/api/agent/tasks/${taskId}`);
      return result;
    } catch (e) {
      return null;
    }
  };

  useEffect(() => {
    if (!modal) return;
    
    const interval = setInterval(async () => {
      const status = await checkTaskStatus(modal.taskId);
      if (status && status.status !== 'pending' && status.status !== 'running') {
        if (status.status === 'completed') {
          toast(`${modal.platform}: ${modal.type} completed`, 'success');
          fetchPortals();
        } else if (status.status === 'failed') {
          toast(`${modal.platform}: ${modal.type} failed - ${status.error}`, 'error');
        }
        setModal(null);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [modal, toast]);

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
                  <Button size="sm" variant="secondary" onClick={() => handleVerify(portal.platform)}>
                    {Icons.refresh} Verify
                  </Button>
                  <Button size="sm" onClick={() => handleOpen(portal.platform)}>
                    {Icons.send} Open Browser
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

      {/* Task Progress Modal */}
      {modal && (
        <Modal open={true} title={`${modal.type} ${modal.platform}`} onClose={() => setModal(null)}>
          <div className="flex flex-col items-center" style={{ padding: 24 }}>
            <Spinner style={{ width: 32, height: 32 }} />
            <div className="muted mt-16" style={{ textAlign: 'center' }}>
              {modal.type} in progress...
            </div>
            <div className="mt-8" style={{ fontSize: 12, color: 'var(--muted)' }}>
              Task ID: {modal.taskId}
            </div>
          </div>
        </Modal>
      )}
    </Layout>
  );
}