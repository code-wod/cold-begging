import Link from 'next/link';
import { useAuth } from '../lib/auth';
import ThemeToggle from '../components/ThemeToggle';
import Logo from '../components/Logo';

const FEATURES = [
  { icon: '✉️', title: 'Gmail-native sending', desc: 'Connect your Gmail via OAuth. Emails send from your account, your reputation, your domain.' },
  { icon: '📊', title: 'Excel / CSV import', desc: 'Drop in a spreadsheet. Company, role, industry — we map every column for personalization.' },
  { icon: '✦', title: 'AI that researches first', desc: 'Before writing a word, the agent studies the company, role, and recipient. Then writes like a human.' },
  { icon: '🤖', title: 'Swappable AI agents', desc: 'Outreach agent, research agent, follow-up agent. Each with its own model, prompt, and temperature.' },
  { icon: '👁️', title: 'Preview before send', desc: 'Every email is reviewed and editable. Nothing goes out without your approval.' },
  { icon: '⏱️', title: 'Smart scheduling', desc: 'Send windows, timezone-aware delays, hourly rate limits, daily caps. Full control.' },
  { icon: '📈', title: 'Campaign analytics', desc: 'Track generated, sent, failed, and delivery rate per campaign. Know what is working.' },
  { icon: '🔒', title: 'Encrypted credentials', desc: 'OAuth tokens and API keys encrypted at rest. We never see your password.' },
];

const STEPS = [
  { num: '01', title: 'Import your list', desc: 'Upload an Excel or CSV file. We detect columns automatically.' },
  { num: '02', title: 'Pick an AI agent', desc: 'Choose a preset or create your own. Set the tone, model, and constraints.' },
  { num: '03', title: 'Generate emails', desc: 'The agent researches each recipient and writes a personalized draft.' },
  { num: '04', title: 'Review & approve', desc: 'Scan through drafts. Edit what you want. Approve the ones you like.' },
  { num: '05', title: 'Schedule or send now', desc: 'Set a send window or fire immediately. Rate limits keep your account safe.' },
  { num: '06', title: 'Track results', desc: 'Dashboard shows delivery rate, failures, and campaign progress in real time.' },
];

const TESTIMONIALS = [
  { name: 'Aditya M.', role: 'Founding Engineer', text: 'Sent 200 personalized emails in a week. Got 18 replies and 4 interviews. The AI research is scarily accurate.' },
  { name: 'Priya S.', role: 'Growth Lead', text: 'We replaced our entire outreach stack with Codessy. Same Gmail, 10x the personalization, fraction of the cost.' },
  { name: 'Karthik R.', role: 'Independent Consultant', text: 'I was spending 3 hours a day writing cold emails. Now it takes 10 minutes to review and approve. Game changer.' },
];

const STATS = [
  { value: '2M+', label: 'Emails generated' },
  { value: '18.4%', label: 'Avg reply rate' },
  { value: '96.2%', label: 'Delivery rate' },
  { value: '4.9/5', label: 'User rating' },
];

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="landing">
      {/* ── Nav ──────────────────────────────────────────────── */}
      <nav className="landing-nav">
        <Logo size={32} showText={true} color="#fff" />
        <div className="landing-nav-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#pricing">Pricing</a>
          <a href="#security">Security</a>
        </div>
        <div className="flex" style={{ alignItems: 'center', gap: 8 }}>
          <ThemeToggle variant="dark" />
          {user ? (
            <Link href="/dashboard" className="landing-cta">Open Dashboard</Link>
          ) : (
            <>
              <Link href="/login" className="landing-nav-link">Sign in</Link>
              <Link href="/signup" className="landing-cta">Get Started Free</Link>
            </>
          )}
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────── */}
      <header className="landing-hero">
        <div className="landing-hero-eyebrow">Cold email automation · your Gmail · your AI</div>
        <h1>Automate cold outreach<br />that actually gets replies</h1>
        <p className="landing-hero-sub">
          Import a spreadsheet, pick an AI agent, and Codessy researches each recipient, writes a
          tailored email, and schedules the send — from your own Gmail account.
        </p>
        <div className="landing-hero-ctas">
          {user ? (
            <Link href="/dashboard" className="landing-cta landing-cta-lg">Open Dashboard</Link>
          ) : (
            <>
              <Link href="/signup" className="landing-cta landing-cta-lg">Get Started Free</Link>
              <a href="#how" className="landing-cta-ghost landing-cta-ghost-lg">See how it works</a>
            </>
          )}
        </div>
        <div className="landing-hero-foot">No credit card required · Free plan · Send from your own Gmail</div>
      </header>

      {/* ── Stats bar ────────────────────────────────────────── */}
      <div className="landing-stats-bar">
        {STATS.map((s) => (
          <div key={s.label} className="landing-stat-item">
            <div className="landing-stat-value">{s.value}</div>
            <div className="landing-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Console preview ──────────────────────────────────── */}
      <div className="landing-preview">
        <div className="landing-console">
          <div className="landing-console-bar">
            <span /><span /><span />
            <span className="landing-console-url">app.codessy.site/dashboard</span>
          </div>
          <div className="landing-console-body">
            <div className="landing-console-sidebar">
              <div className="landing-console-item active" />
              <div className="landing-console-item" />
              <div className="landing-console-item" />
              <div className="landing-console-item" />
              <div className="landing-console-item" />
            </div>
            <div className="landing-console-main">
              <div className="landing-console-stat"><b>1,240</b><span>Emails generated</span></div>
              <div className="landing-console-stat"><b>380</b><span>Emails sent</span></div>
              <div className="landing-console-stat"><b>96.2%</b><span>Delivery rate</span></div>
              <div className="landing-console-stat"><b>18.4%</b><span>Reply rate</span></div>
              <div className="landing-console-stat"><b>3</b><span>Active campaigns</span></div>
              <div className="landing-console-stat"><b>12</b><span>AI agents</span></div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Features ─────────────────────────────────────────── */}
      <section className="landing-section" id="features">
        <div className="landing-section-head">
          <div className="landing-kicker">Features</div>
          <h2>Built for people who send a lot of cold email</h2>
          <p>Not another email template tool. A full outreach platform that runs on your Gmail.</p>
        </div>
        <div className="landing-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className="landing-card">
              <div className="landing-card-icon">{f.icon}</div>
              <h4>{f.title}</h4>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────── */}
      <section className="landing-section landing-alt" id="how">
        <div className="landing-section-head">
          <div className="landing-kicker">How it works</div>
          <h2>From spreadsheet to sent — in six steps</h2>
          <p>No complex setup. No learning curve. Import, configure, send.</p>
        </div>
        <div className="landing-steps">
          {STEPS.map((s) => (
            <div key={s.num} className="landing-step">
              <div className="landing-step-num">{s.num}</div>
              <h4>{s.title}</h4>
              <p>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Testimonials ─────────────────────────────────────── */}
      <section className="landing-section" id="testimonials">
        <div className="landing-section-head">
          <div className="landing-kicker">What users say</div>
          <h2>Trusted by founders and growth teams</h2>
        </div>
        <div className="landing-grid" style={{ maxWidth: 960, margin: '0 auto' }}>
          {TESTIMONIALS.map((t) => (
            <div key={t.name} className="landing-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <p style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 16 }}>&ldquo;{t.text}&rdquo;</p>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{t.name}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.role}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────── */}
      <section className="landing-section landing-alt" id="pricing">
        <div className="landing-section-head">
          <div className="landing-kicker">Pricing</div>
          <h2>Start free. Scale when ready.</h2>
          <p>Bring your own Gmail and AI API key. Upgrade for managed models and higher limits.</p>
        </div>
        <div className="pricing-grid">
          <div className="pricing-card">
            <h3>Free</h3>
            <div className="price">$0 <small>forever</small></div>
            <ul>
              <li>Connect your Gmail</li>
              <li>Import recipients (Excel / CSV)</li>
              <li>Use your own AI API key</li>
              <li>Email preview & editing</li>
              <li>Manual sending</li>
              <li>Basic campaigns</li>
            </ul>
            <Link href="/signup" className="landing-cta">Start Free</Link>
          </div>
          <div className="pricing-card featured">
            <div className="pricing-popular">Most popular</div>
            <h3>Pro</h3>
            <div className="price">₹99 <small>/month</small></div>
            <ul>
              <li>Everything in Free</li>
              <li>Managed AI model included</li>
              <li>Multiple AI agents</li>
              <li>Advanced scheduling & rate control</li>
              <li>Campaign analytics</li>
              <li>Priority processing</li>
            </ul>
            <Link href="/signup" className="landing-cta">Upgrade to Pro</Link>
          </div>
          <div className="pricing-card">
            <div className="pricing-popular" style={{ background: 'var(--badge-teal-bg)', color: 'var(--badge-teal-fg)' }}>One-time</div>
            <h3>Starter</h3>
            <div className="price">₹49 <small>one-time</small></div>
            <ul>
              <li>200 email credits</li>
              <li>No expiry</li>
              <li>Good for testing the platform</li>
              <li>All Free features included</li>
            </ul>
            <Link href="/signup" className="landing-cta">Get Starter</Link>
          </div>
        </div>
      </section>

      {/* ── Security ─────────────────────────────────────────── */}
      <section className="landing-section" id="security">
        <div className="landing-section-head">
          <div className="landing-kicker">Security</div>
          <h2>Your credentials never touch our UI</h2>
          <p>OAuth flows, encrypted storage, scoped permissions. Built for trust.</p>
        </div>
        <div className="landing-grid" style={{ maxWidth: 800, margin: '0 auto' }}>
          <div className="landing-card">
            <div className="landing-card-icon">🔑</div>
            <h4>Google OAuth</h4>
            <p>Gmail access through Google&apos;s official auth flow. We never see or store your password.</p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon">🔐</div>
            <h4>Encrypted at rest</h4>
            <p>OAuth tokens and API keys encrypted with Fernet. Decrypted only at send time.</p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon">🛡️</div>
            <h4>Scoped access</h4>
            <p>Only the minimum Gmail permission needed. Your data is isolated per account.</p>
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────── */}
      <section className="landing-section landing-cta-section">
        <h2>Ready to send outreach that gets replies?</h2>
        <p>Free plan. No credit card. Send from your own Gmail.</p>
        <Link href="/signup" className="landing-cta landing-cta-lg">Get Started Free</Link>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="landing-footer">
        <div className="landing-footer-cols">
          <div>
            <Logo size={28} showText={true} color="#fff" style={{ marginBottom: 8 }} />
            <p style={{ fontSize: 13, margin: '12px 0 0' }}>AI-personalized cold email, sent from your own Gmail.</p>
          </div>
          <div>
            <h5>Product</h5>
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <a href="#pricing">Pricing</a>
            <a href="#security">Security</a>
          </div>
          <div>
            <h5>Account</h5>
            <Link href="/login">Sign in</Link>
            <Link href="/signup">Sign up</Link>
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/billing">Billing</Link>
          </div>
          <div>
            <h5>Legal</h5>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
            <Link href="mailto:support@codessy.site">Contact</Link>
          </div>
        </div>
        <div className="landing-footer-bottom">
          <span>&copy; {new Date().getFullYear()} Codessy. All rights reserved.</span>
          <span>Made with your Gmail · Your data stays yours</span>
        </div>
      </footer>
    </div>
  );
}
