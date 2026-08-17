import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { Panel, Spinner, useToast } from '../components/ui';

export default function Analytics() {
  const toast = useToast();
  const [data, setData] = useState(null);

  useEffect(() => {
    api('/api/analytics').then(setData).catch((e) => toast(e.message, 'error'));
  }, []);

  if (!data) {
    return (
      <Layout title="Analytics">
        <Spinner />
      </Layout>
    );
  }

  const max = Math.max(1, ...data.daily.map((d) => d.sent));

  const cards = [
    ['Emails Generated', data.emails_generated],
    ['Emails Scheduled', data.emails_scheduled],
    ['Emails Sent', data.emails_sent],
    ['Emails Failed', data.emails_failed],
    ['Emails Cancelled', data.emails_cancelled],
    ['Delivery Rate', `${data.delivery_rate}%`],
    ['Campaigns', data.campaigns],
    ['Recipients', data.recipients],
    ['Open Rate', 'Not yet implemented'],
    ['Reply Rate', 'Not yet implemented'],
  ];

  return (
    <Layout title="Analytics" breadcrumb={<span>Analytics</span>}>
      <div className="grid stats">
        {cards.map(([label, value]) => (
          <div key={label} className="panel stat-card">
            <div className="stat-label">{label}</div>
            <div className="stat-value">{value}</div>
          </div>
        ))}
      </div>

      <Panel title="Emails sent — last 14 days" className="mt-16">
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 180 }}>
          {data.daily.map((d) => (
            <div key={d.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div title={`${d.date}: ${d.sent}`}
                style={{ width: '70%', background: d.sent ? 'var(--primary)' : '#e7eaf0', borderRadius: '3px 3px 0 0', height: `${Math.max(2, (d.sent / max) * 160)}px` }} />
              <span className="muted" style={{ fontSize: 10, transform: 'rotate(-40deg)', whiteSpace: 'nowrap' }}>
                {d.date.slice(5)}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <div className="panel mt-16" style={{ padding: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 6 }}>About tracking</h3>
        <p className="muted" style={{ margin: 0 }}>
          The pipeline tracks <b>generated</b>, <b>scheduled</b>, <b>sent</b>, <b>failed</b> and <b>cancelled</b> emails from
          the sending layer. Open, click and reply tracking are <b>not yet implemented</b> — shown as "Not yet implemented"
          above, and no open/reply rates are claimed. Once a tracking layer is added, those rates will appear here.
        </p>
      </div>
    </Layout>
  );
}