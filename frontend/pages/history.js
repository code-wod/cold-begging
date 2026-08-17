import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { Button, Empty, Icons, Input, Modal, Panel, Select, Spinner, StatusBadge, fmtDate, useToast } from '../components/ui';

const STATUS_OPTIONS = [
  ['', 'All statuses'],
  ['generated', 'Generated'],
  ['scheduled', 'Scheduled'],
  ['sending', 'Sending'],
  ['sent', 'Sent'],
  ['failed', 'Failed'],
  ['cancelled', 'Cancelled'],
];

export default function History() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [agents, setAgents] = useState([]);
  const [filters, setFilters] = useState({ campaign_id: '', status: '', search: '', sender: '', agent_id: '', date_from: '', date_to: '' });
  const [detail, setDetail] = useState(null);
  const [sending, setSending] = useState(false);

  const load = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
    params.set('limit', 200);
    api(`/api/emails/history?${params.toString()}`).then(setData).catch((e) => toast(e.message, 'error'));
  };
  useEffect(load, [filters]);

  useEffect(() => {
    api('/api/campaigns').then(setCampaigns).catch(() => {});
    api('/api/ai-agents').then(setAgents).catch(() => {});
  }, []);

  const openDetail = async (id) => {
    try {
      const row = await api(`/api/emails/history/${id}`);
      setDetail(row);
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const retry = async (id) => {
    setSending(true);
    try {
      const res = await api(`/api/emails/history/${id}/retry`, { method: 'POST' });
      toast(res.status === 'sent' ? 'Email sent successfully' : `Failed: ${res.error}`, res.status === 'sent' ? 'success' : 'error');
      setDetail(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSending(false);
    }
  };

  const clearFilters = () =>
    setFilters({ campaign_id: '', status: '', search: '', sender: '', agent_id: '', date_from: '', date_to: '' });

  return (
    <Layout title="Email History" breadcrumb={<span>Email History</span>}>
      <div className="toolbar wrap">
        <div className="flex" style={{ flex: 1, minWidth: 220, position: 'relative' }}>
          {Icons.search}
          <Input placeholder="Search recipient email…" value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
        </div>
        <Select value={filters.campaign_id} onChange={(e) => setFilters({ ...filters, campaign_id: e.target.value })}>
          <option value="">All campaigns</option>
          {campaigns.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
        <Select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
          {STATUS_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select>
        <Select value={filters.sender} onChange={(e) => setFilters({ ...filters, sender: e.target.value })}>
          <option value="">All senders</option>
          {(data?.items || []).map((h) => h.sender_email).filter(Boolean)
            .filter((v, i, a) => a.indexOf(v) === i).map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
        <Select value={filters.agent_id} onChange={(e) => setFilters({ ...filters, agent_id: e.target.value })}>
          <option value="">All AI agents</option>
          {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </Select>
        <Input type="date" value={filters.date_from} title="From date"
          onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
        <Input type="date" value={filters.date_to} title="To date"
          onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
        {(filters.search || filters.status || filters.sender || filters.agent_id || filters.date_from || filters.date_to || filters.campaign_id) && (
          <Button variant="ghost" onClick={clearFilters}>Clear</Button>
        )}
      </div>

      <Panel>
        {data === null ? (
          <Spinner />
        ) : data.items.length === 0 ? (
          <Empty message="No email activity matching these filters." />
        ) : (
          <table className="dense">
            <thead>
              <tr><th>Recipient</th><th>Sender</th><th>Campaign</th><th>Subject</th><th>Status</th><th>Created</th><th /></tr>
            </thead>
            <tbody>
              {data.items.map((h) => (
                <tr key={h.id} className="clickable" onClick={() => openDetail(h.id)}>
                  <td><b>{h.recipient || '—'}</b></td>
                  <td className="muted">{h.sender_email || '—'}</td>
                  <td>{h.campaign || '—'}</td>
                  <td style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {h.subject || '—'}
                    {h.error && <div className="muted" style={{ color: 'var(--danger)', fontSize: 12 }}>{h.error.slice(0, 80)}</div>}
                  </td>
                  <td><StatusBadge status={h.status} /></td>
                  <td className="muted">{fmtDate(h.created_at)}</td>
                  <td>
                    {(h.status === 'failed' || h.status === 'cancelled') && (
                      <Button variant="ghost" className="sm" onClick={(e) => { e.stopPropagation(); retry(h.id); }}>
                        {Icons.refresh} Retry
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Modal open={!!detail} title="Email Details" onClose={() => setDetail(null)} footer={
        detail && (detail.status === 'failed' || detail.status === 'cancelled') ? (
          <Button onClick={() => retry(detail.id)} disabled={sending}>
            {Icons.refresh} {sending ? 'Sending…' : 'Retry'}
          </Button>
        ) : null
      }>
        {detail && (
          <div className="stack">
            <div className="grid-2">
              <div><label>From</label><div><b>{detail.sender_email || '—'}</b></div></div>
              <div><label>To</label><div><b>{detail.recipient_email || '—'}</b></div></div>
              <div><label>Status</label><div><StatusBadge status={detail.status} /></div></div>
              <div><label>Execution</label><div className="muted">{detail.execution_type === 'manual' ? 'Manual' : 'Scheduled campaign'}</div></div>
              <div><label>AI Agent</label><div className="muted">{detail.ai_model ? `${detail.ai_model}${detail.ai_agent_id ? ' · agent' : ''}` : '—'}</div></div>
              <div><label>Campaign</label><div className="muted">{detail.campaign || '—'}</div></div>
              <div><label>Generated</label><div className="muted">{fmtDate(detail.generated_at)}</div></div>
              <div><label>Scheduled</label><div className="muted">{fmtDate(detail.scheduled_at)}</div></div>
              <div><label>Sent</label><div className="muted">{fmtDate(detail.sent_at)}</div></div>
              {detail.failed_at && <div><label>Failed</label><div className="muted">{fmtDate(detail.failed_at)}</div></div>}
            </div>
            {detail.error && (
              <div className="alert danger" role="alert">
                <b>{detail.error_code || 'Error'}:</b> {detail.error}
              </div>
            )}
            <div><label>Subject</label><div className="muted" style={{ whiteSpace: 'pre-wrap' }}>{detail.subject || '—'}</div></div>
            <div><label>Body</label><div style={{ whiteSpace: 'pre-wrap' }} className="muted">{detail.body || '—'}</div></div>
          </div>
        )}
      </Modal>
    </Layout>
  );
}