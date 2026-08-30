import Link from 'next/link';
import { useAuth } from '../lib/auth';
import ThemeToggle from '../components/ThemeToggle';

const FEATURES = [
  ['Gmail integration', 'Connect your own Gmail account via Google OAuth. We never ask for your password.'],
  ['Excel / CSV import', 'Import your recipient list with company, industry and role details for personalization.'],
  ['AI personalization', 'Each email is researched and written for the specific company and recipient.'],
  ['Multiple AI agents', 'Create dedicated agents — outreach, company research, follow-ups — each with its own model.'],
  ['Multiple AI models', 'Bring your own OpenAI, Anthropic or compatible model API keys, or use the managed model.'],
  ['Email preview & edit', 'Review, edit and approve every email before it is sent.'],
  ['Scheduling', 'Set send windows, active days, delays and daily limits. Manual sending is always available.'],
  ['Campaign tracking', 'Follow every campaign from draft to completion with clear status and history.'],
];

const FEATURE_ICONS = ['✉', '⇪', '✦', '♯', '⌬', '◉', '◷', '≋'];

const WORKFLOW = [
  'Import Recipients',
  'Configure AI Agent',
  'Research & Personalize',
  'Preview Emails',
  'Schedule / Send',
  'Track Results',
];

const N8N_NODES = [
  { icon: '👤', title: 'Your profile', sub: 'Resume · links · details' },
  { icon: '⚙', title: 'n8n workflow', sub: 'Ready-made automation', active: true },
  { icon: '🏢', title: 'Job portals', sub: 'Detects matching roles' },
  { icon: '✓', title: 'Auto-apply', sub: 'Submitted with your profile', done: true },
];

const PLANS = [
  {
    name: 'Free',
    price: '$0',
    tag: 'For trying the platform',
    featured: false,
    items: [
      'Connect your own Gmail',
      'Import recipients (Excel / CSV)',
      'Recipient management',
      'Use your own AI API key',
      'Email preview & manual editing',
      'Manual sending',
      'Basic campaigns',
    ],
  },
  {
    name: 'Pro',
    price: 'Paid',
    tag: 'For serious outreach',
    featured: true,
    items: [
      'Everything in Free',
      'Managed default AI model',
      'Multiple AI agents',
      'Advanced scheduling & rate control',
      'Higher AI usage',
      'Campaign analytics',
      'Advanced personalization',
      'Priority processing',
    ],
  },
];

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="landing-brand">
          <span className="logo">✉️</span>
          <span>PulseBoard</span>
          <span className="landing-brand-tag">COLD EMAIL AI</span>
        </div>
        <div className="landing-nav-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#n8n">n8n Auto-apply</a>
          <a href="#pricing">Pricing</a>
          <a href="#security">Security</a>
        </div>
        <div className="flex">
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

      <header className="landing-hero">
        <div className="landing-hero-eyebrow">Cold email automation · your Gmail · your AI</div>
        <h1>Automate personalized cold email<br />that sounds like <em>you</em></h1>
        <p className="landing-hero-sub">
          Import a spreadsheet, pick an AI agent, and PulseBoard researches each recipient, writes a
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

      <div className="landing-preview">
        <div className="landing-console">
          <div className="landing-console-bar">
            <span /><span /><span />
            <span className="landing-console-url">app.pulseboard.ai/dashboard</span>
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

      <section className="landing-section" id="features">
        <div className="landing-section-head">
          <div className="landing-kicker">Products &amp; features</div>
          <h2>Everything you need for serious outreach</h2>
          <p>A cloud-automation workspace, not a chat template. Your data stays per-account and encrypted.</p>
        </div>
        <div className="landing-grid">
          {FEATURES.map(([t, d], i) => (
            <div key={t} className="landing-card">
              <div className="landing-card-icon">{FEATURE_ICONS[i]}</div>
              <h4>{t}</h4>
              <p>{d}</p>
              <a className="landing-more" href="#how">Learn more →</a>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-alt" id="n8n">
        <div className="landing-section-head">
          <div className="landing-kicker"><span className="badge orange">Coming soon</span> &nbsp;·&nbsp; n8n workflow</div>
          <h2>Apply to job portals automatically — from your profile</h2>
          <p>A ready-made n8n workflow ships with your account. Drop in your profile, it applies to matching roles.</p>
        </div>
        <div className="n8n-pipeline" style={{ maxWidth: 960, margin: '0 auto' }}>
          {N8N_NODES.map((n, i) => [
            i > 0 ? <div className="n8n-flow" aria-hidden="true" key={`flow-${i}`} /> : null,
            (
              <div key={n.title} className={`n8n-node${n.active ? ' active' : ''}${n.done ? ' done' : ''}`}>
                <div className="n8n-node-icon">{n.icon}</div>
                <div className="n8n-node-title">{n.title}</div>
                <div className="n8n-node-sub">{n.sub}</div>
              </div>
            ),
          ])}
        </div>
        <p style={{ textAlign: 'center', color: 'var(--landing-muted)', fontSize: 13, marginTop: 18 }}>
          No manual form-filling. No missed deadlines. Watch this space.
        </p>
      </section>

      <section className="landing-section landing-alt" id="how">
        <div>
          <div className="landing-section-head">
            <div className="landing-kicker">How it works</div>
            <h2>From spreadsheet to personalized outreach</h2>
            <p>Six guided steps, from import to results.</p>
          </div>
          <div className="landing-steps">
            {WORKFLOW.map((step, i) => (
              <div key={step} className="landing-step">
                <div className="landing-step-num">{String(i + 1).padStart(2, '0')}</div>
                <h4>{step}</h4>
                <p>{i === 2 ? 'The platform researches each company and writes a tailored email.' : 'Guided, step by step, from the dashboard.'}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section" id="pricing">
        <div className="landing-section-head">
          <div className="landing-kicker">Pricing</div>
          <h2>Free to start. Pay only for more power</h2>
          <p>Bring your own Gmail account and AI API key — or upgrade to Pro for the managed model.</p>
        </div>
        <div className="pricing-grid">
          {PLANS.map((p) => (
            <div key={p.name} className={`pricing-card ${p.featured ? 'featured' : ''}`}>
              <h3>{p.name}</h3>
              <div className="price">{p.price} <small>{p.tag}</small></div>
              <ul>
                {p.items.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
              {user ? (
                <Link href="/billing" className="landing-cta">Manage Plan</Link>
              ) : (
                <Link href="/signup" className="landing-cta">
                  {p.name === 'Free' ? 'Start Free' : 'Upgrade'}
                </Link>
              )}
            </div>
          ))}
        </div>
        <div className="landing-note">
          <strong>Need recipient emails?</strong>
          <p>
            We don't provide lists for free. Recipient discovery is a separate paid service — bring your own
            list, or contact us about our recipient data service.
          </p>
        </div>
      </section>

      <section className="landing-section landing-alt" id="security">
        <div>
          <div className="landing-section-head">
            <div className="landing-kicker">Security</div>
            <h2>Credentials stay encrypted and out of the browser</h2>
            <p>OAuth and encrypted secrets, scoped per account.</p>
          </div>
          <div className="landing-grid">
            <div className="landing-card">
              <div className="landing-card-icon">⌁</div>
              <h4>Google OAuth, not passwords</h4>
              <p>Gmail access happens through Google's official authentication flow. We never ask for — or store — your Gmail password.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">◍</div>
              <h4>Encrypted secrets</h4>
              <p>OAuth tokens and AI API keys are encrypted at rest on the server and never sent to your browser.</p>
            </div>
            <div className="landing-card">
              <div className="landing-card-icon">⊘</div>
              <h4>Scoped access</h4>
              <p>We request only the minimum Gmail permission needed to send on your behalf. Your data is isolated per account.</p>
            </div>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-cols">
          <div>
            <h5>PulseBoard</h5>
            <div className="landing-brand"><span className="logo">✉️</span><span>PulseBoard</span></div>
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
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Contact</a>
          </div>
        </div>
        <div className="landing-footer-bottom">
          <span>© {new Date().getFullYear()} PulseBoard. All rights reserved.</span>
          <span>Made with your Gmail · Your data stays yours</span>
        </div>
      </footer>
    </div>
  );
}