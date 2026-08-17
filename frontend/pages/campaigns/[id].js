import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { api } from '../../lib/api';
import {
  Button, Confirm, Empty, Icons, Modal, Panel, Progress, Spinner, StatusBadge, TextArea, fmtDate, useToast,
} from '../../components/ui';

export default function CampaignDetail() {
  const router = useRouter();
  const { id } = router.query;
  const toast = useToast();
  const [campaign, setCampaign] = useState(null);
  const [emails, setEmails] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [preview, setPreview] = useState(null);
  const [draft, setDraft] = useState({ subject: '', body: '' });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = () => {
    if (!id) return;
    api(`/api/campaigns/${id}`).then(setCampaign).catch((e) => toast(e.message, 'error'));
    api(`/api/campaigns/${id}/emails`).then(setEmails).catch((e) => toast(e.message, 'error'));
    api('/api/email-accounts').then(setAccounts).catch(() => {});
  };
  useEffect(load, [id]);

  const act = async (path, msg, then) => {
    try {
      const res = await api(path, { method: 'POST' });
      if (msg) toast(msg, 'success');
      if (res?.dry_run) toast(res.message || 'Dry run — nothing sent', 'info');
      load();
      if (then) then(res);
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const openPreview = (e) => {
    setPreview(e);
    setDraft({ subject: e.subject, body: e.body });
  };

  const saveEdit = async () => {
    try {
      await api(`/api/emails/${preview.id}`, { method: 'PATCH', body: draft });
      toast('Email updated', 'success');
      load();
      setPreview({ ...preview, ...draft });
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const sendOne = async (e) => {
    await act(`/api/emails/${e.id}/send`, null, (res) => {
      if (res.status === 'sent') toast(`Sent to ${e.recipient_email}`, 'success');
      else if (res.status === 'failed') toast(`Failed: ${res.error}`, 'error');
    });
  };

  const doDelete = async () => {
    try {
      await api(`/api/campaigns/${id}`, { method: 'DELETE' });
      toast('Campaign deleted', 'success');
      router.push('/campaigns');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  if (!campaign) {
    return (
      <Layout title="Campaign">
        <Spinner />
      </Layout>
    );
  }

  const done = campaign.sent_count + campaign.failed_count;
  const total = campaign.generated_count || 1;
  const progress = Math.round((done / total) * 100);

  return (
    <Layout title={campaign.name} breadcrumb={<><Link href="/campaigns">Campaigns</Link> / {campaign.name}</>}>
      <div className="justify-between mb-16">
        <div className="flex">
          <StatusBadge status={campaign.status} />
          {campaign.dry_run && <span className="badge amber">dry run</span>}
          <span className="muted">Created {fmtDate(campaign.created_at)}</span>
        </div>
        <div className="flex">
          {['draft', 'review_required'].includes(campaign.status) && (
            <Button variant="secondary" disabled={busy} onClick={() => { setBusy(true); act(`/api/campaigns/${id}/test`, 'Generating (dry run)…', () => setBusy(false)); }}>
              {Icons.eye} Test / Generate
            </Button>
          )}
          {campaign.status === 'review_required' && (
            <Button onClick={() => act(`/api/campaigns/${id}/launch`, 'Campaign scheduled')}>{Icons.play} Launch</Button>
          )}
{['scheduled', 'running'].includes(campaign.status) && (
            <Button variant="secondary" onClick={() => act(`/api/campaigns/${id}/pause`, 'Sending stopped — campaign paused')}><Icons.pause /> Stop</Button>
          )}
          {campaign.status === 'paused' && (
            <Button onClick={() => act(`/api/campaigns/${id}/resume`, 'Campaign resumed')}>{Icons.play} Resume</Button>
          )}
          {['scheduled', 'running', 'paused', 'review_required'].includes(campaign.status) && (
            <Button variant="secondary" onClick={() => setConfirmCancel(true)}>{Icons.x} Cancel</Button>
          )}
          <Button variant="secondary" onClick={() => act(`/api/campaigns/${id}/duplicate`, 'Campaign duplicated')}>{Icons.duplicate} Duplicate</Button>
          <Button variant="danger" onClick={() => setConfirmDelete(true)}>{Icons.trash}</Button>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <Panel title="Progress">
          <div className="flex" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
            <b>{progress}%</b>
            <span className="muted">{done} / {total} processed</span>
          </div>
          <Progress percent={progress} />
          <div className="grid mt-16" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
            <div><div className="stat-label">Sent</div><b className="muted">{campaign.sent_count}</b></div>
            <div><div className="stat-label">Pending</div><b className="muted">{campaign.pending_count}</b></div>
            <div><div className="stat-label">Failed</div><b className="muted">{campaign.failed_count}</b></div>
            <div><div className="stat-label">Cancelled</div><b className="muted">{campaign.cancelled_count || 0}</b></div>
            <div><div className="stat-label">{campaign.max_sends ? `Cap (of ${campaign.max_sends})` : 'Recipients'}</div><b className="muted">{campaign.max_sends ? campaign.sent_count : campaign.recipient_count}</b></div>
          </div>
        </Panel>
        <Panel title="Schedule">
          <table className="dense">
            <tbody>
              <tr><td className="muted">Window</td><td>{campaign.send_start_time} – {campaign.send_end_time}</td></tr>
              <tr><td className="muted">Days</td><td>{campaign.active_days.map((d) => ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d]).join(', ')}</td></tr>
              <tr><td className="muted">Speed</td><td>{campaign.emails_per_hour}/hr (~1 per {Math.max(1, Math.round(3600 / (campaign.emails_per_hour || 10)))}s)</td></tr>
              {campaign.daily_limit > 0 && <tr><td className="muted">Daily cap</td><td>{campaign.daily_limit}</td></tr>}
              {campaign.max_sends > 0 && (
                <tr><td className="muted">Auto-stop</td><td>after {campaign.max_sends} sends {campaign.sent_count >= campaign.max_sends ? '(reached)' : ''}</td></tr>
              )}
              <tr><td className="muted">Agent</td><td>{campaign.agent_id ? `#${campaign.agent_id}` : 'Default'}</td></tr>
              <tr><td className="muted">Sending account</td><td>{accounts.find((a) => a.id === campaign.email_account_id)?.email || <span className="muted">Not set</span>}</td></tr>
            </tbody>
          </table>
        </Panel>
      </div>

      <div className="mt-16">
        <Panel title={`Emails (${emails?.length || 0})`}
          actions={
            emails && emails.length > 0 ? (
              <div className="flex">
                <Button variant="secondary" sm onClick={() => act(`/api/campaigns/${id}/approve-all`, 'All pending emails approved')}>{Icons.check} Approve all</Button>
                <Button variant="secondary" sm onClick={() => act(`/api/campaigns/${id}/send-pending`, null, (r) => toast(`Sent ${r.sent} of ${r.total}`, 'success'))}>
                  {Icons.send} Send pending
                </Button>
              </div>
            ) : null
          }>
          {emails === null ? (
            <Spinner />
          ) : emails.length === 0 ? (
            <Empty message="No emails generated yet. Click Test / Generate above to create drafts." />
          ) : (
            <table className="dense">
              <thead>
                <tr><th>Recipient</th><th>Subject</th><th>Status</th><th>Generated</th><th style={{ width: 200 }}>Actions</th></tr>
              </thead>
              <tbody>
                {emails.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <b>{e.recipient_email}</b>
                      {e.recipient_name && <div className="muted" style={{ fontSize: 12 }}>{e.recipient_name}</div>}
                    </td>
                    <td style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {e.subject || '—'}
                      {e.error && <div className="muted" style={{ color: 'var(--danger)', fontSize: 12 }}>{e.error.slice(0, 80)}</div>}
                    </td>
                    <td><StatusBadge status={e.status} /></td>
                    <td className="muted">{fmtDate(e.generated_at)}</td>
                    <td>
                      <div className="flex">
                        <Button variant="secondary" sm onClick={() => openPreview(e)}>{Icons.eye} View</Button>
                        {e.status === 'generated' && (
                          <Button variant="secondary" sm onClick={() => act(`/api/emails/${e.id}/approve`, 'Approved')}>{Icons.check}</Button>
                        )}
                        {e.status !== 'sent' && (
                          <Button variant="secondary" sm onClick={() => act(`/api/emails/${e.id}/regenerate`, 'Regenerated')}>{Icons.refresh}</Button>
                        )}
                        {['generated', 'approved'].includes(e.status) && !campaign.dry_run && (
                          <Button variant="secondary" sm onClick={() => sendOne(e)}>{Icons.send}</Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      </div>

      <Modal open={!!preview} title="Email preview" onClose={() => setPreview(null)}
        footer={
          <div className="flex" style={{ justifyContent: 'space-between', width: '100%' }}>
            <div className="flex">
              <Button variant="secondary" onClick={saveEdit}>{Icons.check} Save edit</Button>
              <Button variant="secondary" onClick={() => act(`/api/emails/${preview.id}/regenerate`, 'Regenerated', () => load())}>{Icons.refresh} Regenerate</Button>
            </div>
            <div className="flex">
              {preview && preview.status !== 'sent' && (
                <Button variant="secondary" onClick={() => act(`/api/emails/${preview.id}/approve`, 'Approved', () => load())}>
                  {Icons.check} Approve
                </Button>
              )}
              {preview && !campaign.dry_run && ['generated', 'approved'].includes(preview.status) && (
                <Button onClick={() => sendOne(preview)}>{Icons.send} Send</Button>
              )}
            </div>
          </div>
        }>
        {preview && (
          <div>
            <div className="field">
              <div className="label">To:</div>
              <div className="muted">{preview.recipient_email}</div>
            </div>
            <div className="field">
              <div className="label">Subject:</div>
              <TextArea rows={1} value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })} />
            </div>
            <div className="field">
              <div className="label">Body:</div>
              <TextArea rows={14} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} />
            </div>
          </div>
        )}
      </Modal>

      <Confirm open={confirmDelete} title="Delete campaign" danger
        message={`Delete "${campaign.name}"? This removes generated emails and history for this campaign.`}
        confirmLabel="Delete" onCancel={() => setConfirmDelete(false)} onConfirm={doDelete} />

      <Confirm open={confirmCancel} title="Cancel campaign" danger
        message={`Cancel "${campaign.name}"? Pending emails will be marked cancelled and sending will stop. Already-sent emails are kept.`}
        confirmLabel="Cancel campaign" onCancel={() => setConfirmCancel(false)}
        onConfirm={async () => { setConfirmCancel(false); await act(`/api/campaigns/${id}/cancel`, 'Campaign cancelled'); }} />
    </Layout>
  );
}