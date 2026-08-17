import { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import { Button, Confirm, Empty, Icons, Panel, Spinner, StatusBadge, fmtDate, Progress, useToast } from '../../components/ui';

export default function Campaigns() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = () => api('/api/campaigns').then(setItems).catch((e) => toast(e.message, 'error'));
  useEffect(() => { load(); }, []);

  const act = async (path, msg) => {
    try {
      await api(path, { method: 'POST' });
      toast(msg, 'success');
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const doDelete = async () => {
    try {
      await api(`/api/campaigns/${confirmDelete.id}`, { method: 'DELETE' });
      toast('Campaign deleted', 'success');
      setConfirmDelete(null);
      load();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  return (
    <Layout title="Campaigns" breadcrumb={<span>Campaigns</span>}>
      <div className="toolbar">
        <Link href="/campaigns/new" className="btn">{Icons.plus} Create Campaign</Link>
      </div>

      <Panel>
        {items === null ? (
          <Spinner />
        ) : items.length === 0 ? (
          <Empty message="No campaigns yet. Create your first campaign to generate personalized outreach." />
        ) : (
          <table className="dense">
            <thead>
              <tr>
                <th>Campaign</th><th>Status</th><th>Progress</th>
                <th>Sent</th><th>Failed</th><th>Pending</th><th>Created</th><th style={{ width: 120 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => {
                const done = c.sent_count + c.failed_count;
                const total = c.generated_count || c.recipient_count;
                return (
                  <tr key={c.id}>
                    <td>
                      <Link href={`/campaigns/${c.id}`} style={{ fontWeight: 600 }}>{c.name}</Link>
                      {c.dry_run && <span className="badge amber" style={{ marginLeft: 8 }}>dry run</span>}
                    </td>
                    <td><StatusBadge status={c.status} /></td>
                    <td style={{ minWidth: 180 }}>
                      <div className="flex">
                        <div className="progress" style={{ flex: 1 }}><div style={{ width: total ? `${(done / total) * 100}%` : 0 }} /></div>
                        <span className="muted">{done}/{total}</span>
                      </div>
                    </td>
                    <td>{c.sent_count}</td>
                    <td>{c.failed_count || '—'}</td>
                    <td>{c.pending_count}</td>
                    <td className="muted">{fmtDate(c.created_at)}</td>
                    <td>
                      <div className="flex">
                        {['scheduled', 'running'].includes(c.status) ? (
                          <Button variant="secondary" sm onClick={() => act(`/api/campaigns/${c.id}/pause`, 'Sending stopped — campaign paused')}>{Icons.pause} Stop</Button>
                        ) : c.status === 'paused' ? (
                          <Button variant="secondary" sm onClick={() => act(`/api/campaigns/${c.id}/resume`, 'Campaign resumed')}>{Icons.play} Resume</Button>
                        ) : null}
                        <Button variant="secondary" sm onClick={() => act(`/api/campaigns/${c.id}/duplicate`, 'Campaign duplicated')}>{Icons.duplicate}</Button>
                        <Button variant="secondary" sm onClick={() => setConfirmDelete(c)}>{Icons.trash}</Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Panel>

      <Confirm open={!!confirmDelete} title="Delete campaign" danger
        message={`Delete "${confirmDelete?.name}"? Generated emails and history for this campaign will be removed.`}
        confirmLabel="Delete" onCancel={() => setConfirmDelete(null)} onConfirm={doDelete} />
    </Layout>
  );
}