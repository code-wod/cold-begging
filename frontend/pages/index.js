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
          <svg viewBox="0 0 120 120" style={{ height: 32, flexShrink: 0 }} role="img" aria-label="Codessy">
            <defs>
              <linearGradient id="lb-blue" x1="22" y1="0" x2="58" y2="36" gradientUnits="userSpaceOnUse">
                <stop stop-color="#35A7FF" /><stop offset="1" stop-color="#2875F0" />
              </linearGradient>
              <linearGradient id="lb-purple" x1="64" y1="0" x2="100" y2="36" gradientUnits="userSpaceOnUse">
                <stop stop-color="#9B5CFF" /><stop offset="1" stop-color="#7340E8" />
              </linearGradient>
              <linearGradient id="lb-green" x1="22" y1="50" x2="58" y2="76" gradientUnits="userSpaceOnUse">
                <stop stop-color="#22D3A6" /><stop offset="1" stop-color="#10B981" />
              </linearGradient>
              <linearGradient id="lb-coral" x1="64" y1="50" x2="100" y2="76" gradientUnits="userSpaceOnUse">
                <stop stop-color="#FF9A55" /><stop offset="1" stop-color="#F45F72" />
              </linearGradient>
            </defs>
            <rect width="120" height="120" rx="28" fill="#070B1F"/>
            <g transform="translate(-1 22)">
              <path d="M22 18C22 8.059 30.059 0 40 0h18v18c0 9.941-8.059 18-18 18H22V18Z" fill="url(#lb-blue)" />
              <circle cx="82" cy="18" r="18" fill="url(#lb-purple)" />
              <path d="M22 40h18c9.941 0 18 8.059 18 18v18H40c-9.941 0-18-8.059-18-18V40Z" fill="url(#lb-green)" />
              <path d="M64 40h18c9.941 0 18 8.059 18 18v18H82c-9.941 0-18-8.059-18-18V40Z" fill="url(#lb-coral)" />
            </g>
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.5px', color: '#fff' }}>Codessy</span>
            <span style={{ fontSize: 10, fontWeight: 500, letterSpacing: '2px', color: '#94a3b8' }}>BUILD. AUTOMATE. SCALE.</span>
          </div>
        </div>
        <div className="landing-nav-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#extension">Extension</a>
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

      <section className="landing-section landing-alt" id="extension">
        <div className="landing-section-head">
          <div className="landing-kicker">Browser Extension</div>
          <h2>Fill every job application instantly</h2>
          <p>Our Chrome extension detects application forms, maps your profile to fields, and fills them in one click. Works across Greenhouse, Workday, Lever, Ashby, and any custom career page.</p>
        </div>
        <div className="landing-grid">
          <div className="landing-card">
            <div className="landing-card-icon">⚡</div>
            <h4>Universal Form Detection</h4>
            <p>Automatically detects job application forms on any career page. No setup required per site.</p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon">🧠</div>
            <h4>AI-Powered Mapping</h4>
            <p>Smart field recognition understands "First Name", "Given Name", "Prenom" — and maps to your profile automatically.</p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon">✓</div>
            <h4>Review Before Fill</h4>
            <p>Confidence scoring shows what's auto-filled vs what needs your review. You're always in control.</p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon">🔒</div>
            <h4>Privacy First</h4>
            <p>Your profile data stays in your browser. Only syncs when you sign in. Never auto-submits.</p>
          </div>
        </div>
        <div style={{ textAlign: 'center', marginTop: 32 }}>
          <Link href="/extension/download" className="landing-cta" style={{ display: 'inline-block' }}>
            Install Chrome Extension
          </Link>
          <p style={{ fontSize: 13, color: '#999', marginTop: 12 }}>Free · Open source · Works with your Codessy account</p>
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
            <div className="landing-brand" style={{ marginBottom: 8 }}>
              <svg viewBox="0 0 120 120" style={{ height: 28, flexShrink: 0 }} role="img" aria-label="Codessy">
                <defs>
                  <linearGradient id="fb-blue" x1="22" y1="0" x2="58" y2="36" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#35A7FF" /><stop offset="1" stop-color="#2875F0" />
                  </linearGradient>
                  <linearGradient id="fb-purple" x1="64" y1="0" x2="100" y2="36" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#9B5CFF" /><stop offset="1" stop-color="#7340E8" />
                  </linearGradient>
                  <linearGradient id="fb-green" x1="22" y1="50" x2="58" y2="76" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#22D3A6" /><stop offset="1" stop-color="#10B981" />
                  </linearGradient>
                  <linearGradient id="fb-coral" x1="64" y1="50" x2="100" y2="76" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#FF9A55" /><stop offset="1" stop-color="#F45F72" />
                  </linearGradient>
                </defs>
                <rect width="120" height="120" rx="28" fill="#070B1F"/>
                <g transform="translate(-1 22)">
                  <path d="M22 18C22 8.059 30.059 0 40 0h18v18c0 9.941-8.059 18-18 18H22V18Z" fill="url(#fb-blue)" />
                  <circle cx="82" cy="18" r="18" fill="url(#fb-purple)" />
                  <path d="M22 40h18c9.941 0 18 8.059 18 18v18H40c-9.941 0-18-8.059-18-18V40Z" fill="url(#fb-green)" />
                  <path d="M64 40h18c9.941 0 18 8.059 18 18v18H82c-9.941 0-18-8.059-18-18V40Z" fill="url(#fb-coral)" />
                </g>
              </svg>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>Codessy</span>
            </div>
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
          <span>© {new Date().getFullYear()} Codessy. All rights reserved.</span>
          <span>Made with your Gmail · Your data stays yours</span>
        </div>
      </footer>
    </div>
  );
}
