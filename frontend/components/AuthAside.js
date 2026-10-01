import Logo from './Logo';

const FEATURES = [
  { icon: '✉️', title: 'Send from your own Gmail', desc: 'OAuth-connected. Your domain, your reputation.' },
  { icon: '✦', title: 'AI that researches first', desc: 'Studies the company and recipient before writing.' },
  { icon: '👁️', title: 'Preview before send', desc: 'Edit or reject any draft. You stay in control.' },
  { icon: '📈', title: 'Campaign analytics', desc: 'Reply rates, delivery, and failures in real time.' },
];

const STATS = [
  { value: '2M+', label: 'Emails generated' },
  { value: '18.4%', label: 'Avg reply rate' },
  { value: '96.2%', label: 'Delivery rate' },
];

export default function AuthAside({ kicker, title, titleAccent, sub }) {
  return (
    <aside className="auth-aside">
      <div className="auth-aside-brand">
        <Logo size={34} showText color="#fff" />
      </div>
      <div className="auth-aside-kicker">{kicker}</div>
      <h2>{title} <em>{titleAccent}</em></h2>
      <p className="auth-aside-sub">{sub}</p>
      <ul className="auth-features">
        {FEATURES.map((f) => (
          <li key={f.title}>
            <div className="af-icon">{f.icon}</div>
            <div>
              <b>{f.title}</b>
              <br />
              <span>{f.desc}</span>
            </div>
          </li>
        ))}
      </ul>
      <div className="auth-stats">
        {STATS.map((s) => (
          <div key={s.label} className="auth-stat">
            <b>{s.value}</b>
            <span>{s.label}</span>
          </div>
        ))}
      </div>
      <div className="auth-quote">
        <p>&ldquo;Sent 200 personalized emails in a week. Got 18 replies and 4 interviews. The AI research is scarily accurate.&rdquo;</p>
        <div className="auth-quote-author">
          <div className="auth-quote-avatar">AM</div>
          <div>
            <div className="auth-quote-name">Aditya M.</div>
            <div className="auth-quote-role">Founding Engineer</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
