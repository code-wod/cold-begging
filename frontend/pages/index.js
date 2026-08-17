import Link from 'next/link';
import { useAuth } from '../lib/auth';

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

const WORKFLOW = [
  'Import Recipients',
  'Configure AI Agent',
  'Research & Personalize',
  'Preview Emails',
  'Schedule / Send',
  'Track Results',
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
        <div style={{ fontWeight: 800, fontSize: 18 }}>
          ✉️ PulseBoard <span style={{ color: '#2563eb' }}>Cold Email AI</span>
        </div>
        <div className="flex">
          {user ? (
            <Link href="/dashboard" className="btn">Open Dashboard</Link>
          ) : (
            <>
              <Link href="/login" className="btn ghost">Login</Link>
              <Link href="/signup" className="btn">Get Started Free</Link>
            </>
          )}
        </div>
      </nav>

      <header className="landing-hero">
        <h1>AI-Powered Personalized<br />Cold Email Automation</h1>
        <p>
          Turn your recipient list into personalized outreach campaigns using your own
          Gmail account and the AI model of your choice.
        </p>
        <div className="flex" style={{ justifyContent: 'center' }}>
          {user ? (
            <Link href="/dashboard" className="btn" style={{ padding: '12px 24px', fontSize: 15 }}>Open Dashboard</Link>
          ) : (
            <>
              <Link href="/signup" className="btn" style={{ padding: '12px 24px', fontSize: 15 }}>Get Started Free</Link>
              <a href="#how" className="btn secondary" style={{ padding: '12px 24px', fontSize: 15 }}>See How It Works</a>
            </>
          )}
        </div>
      </header>

      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '0 40px' }}>
        <div className="panel" style={{ boxShadow: '0 20px 60px rgba(16,24,40,0.12)' }}>
          <img
            src="https://placehold.co/1080x520/eef1f6/667085?text=PulseBoard+—+Campaign+Dashboard"
            alt="PulseBoard dashboard preview"
            style={{ width: '100%', display: 'block', borderRadius: 'var(--radius)' }}
          />
        </div>
      </div>

      <section className="landing-section" id="how">
        <h2>How it works</h2>
        <p className="sub">From spreadsheet to personalized outreach in minutes.</p>
        <div className="landing-grid">
          {WORKFLOW.map((step, i) => (
            <div key={step} className="feature-card">
              <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>STEP {i + 1}</div>
              <h4 style={{ margin: '6px 0' }}>{step}</h4>
              <p>{i === 2 ? 'The platform researches each company and writes a tailored email.' : 'Guided, step by step, from the dashboard.'}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <h2>Key features</h2>
        <p className="sub">A serious cloud-automation workspace, not a chat template.</p>
        <div className="landing-grid">
          {FEATURES.map(([t, d]) => (
            <div key={t} className="feature-card">
              <h4>{t}</h4>
              <p>{d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <h2>Free setup</h2>
        <p className="sub">
          Start free by connecting your own Google account. You bring the Gmail account; we bring the automation.
          Bring your own AI API key or upgrade for the managed model.
        </p>
        <div className="landing-grid">
          <div className="feature-card">
            <h4>1 · Create account</h4>
            <p>Sign up in seconds. No credit card required.</p>
          </div>
          <div className="feature-card">
            <h4>2 · Connect Gmail</h4>
            <p>One-click Google OAuth. We only request the permission needed to send on your behalf.</p>
          </div>
          <div className="feature-card">
            <h4>3 · Import & go</h4>
            <p>Upload your recipients, pick an AI agent, and launch your first campaign.</p>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <h2>Pricing</h2>
        <p className="sub">Free to start. Pay only when you need more power.</p>
        <div className="landing-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
          {PLANS.map((p) => (
            <div key={p.name} className={`pricing-card ${p.featured ? 'featured' : ''}`}>
              <h3>{p.name}</h3>
              <div className="price">{p.price}</div>
              <p className="muted" style={{ marginTop: -8 }}>{p.tag}</p>
              <ul>
                {p.items.map((i) => (
                  <li key={i}>✓ {i}</li>
                ))}
              </ul>
              {user ? (
                <Link href="/billing" className="btn" style={{ justifyContent: 'center' }}>Manage Plan</Link>
              ) : (
                <Link href="/signup" className="btn" style={{ justifyContent: 'center' }}>
                  {p.name === 'Free' ? 'Start Free' : 'Upgrade'}
                </Link>
              )}
            </div>
          ))}
        </div>
        <div className="panel mt-16" style={{ padding: 18 }}>
          <strong>Need recipient emails?</strong>
          <p className="muted mb-0" style={{ marginTop: 4 }}>
            We don't provide lists for free. Recipient discovery is a separate paid service — bring your own
            list, or contact us about our recipient data service.
          </p>
        </div>
      </section>

      <section className="landing-section">
        <h2>Security</h2>
        <p className="sub">Your credentials stay encrypted and out of the browser.</p>
        <div className="landing-grid">
          <div className="feature-card">
            <h4>Google OAuth, not passwords</h4>
            <p>Gmail access happens through Google's official authentication flow. We never ask for — or store — your Gmail password.</p>
          </div>
          <div className="feature-card">
            <h4>Encrypted secrets</h4>
            <p>OAuth tokens and AI API keys are encrypted at rest on the server and never sent to your browser.</p>
          </div>
          <div className="feature-card">
            <h4>Scoped access</h4>
            <p>We request only the minimum Gmail permission needed to send on your behalf. Your data is isolated per account.</p>
          </div>
        </div>
      </section>

      <footer className="footer">
        <Link href="#how">Documentation</Link>
        <Link href="#pricing">Pricing</Link>
        <a href="#">Privacy</a>
        <a href="#">Terms</a>
        <a href="#">Contact</a>
        <Link href="/login">Login</Link>
        <Link href="/signup">Sign Up</Link>
      </footer>
    </div>
  );
}