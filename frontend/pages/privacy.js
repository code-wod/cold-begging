import Link from 'next/link';
import Logo from '../components/Logo';
import ThemeToggle from '../components/ThemeToggle';

const NAV = [
  ['#collect', 'Data we collect'],
  ['#use', 'How we use it'],
  ['#interviews', 'Interview Rooms'],
  ['#security', 'Security'],
  ['#rights', 'Your rights'],
];

export default function Privacy() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <Link href="/"><Logo size={30} showText color="#fff" /></Link>
        <div className="landing-nav-links">
          {NAV.map(([href, label]) => <a key={href} href={href}>{label}</a>)}
        </div>
        <div className="flex" style={{ alignItems: 'center', gap: 8 }}>
          <ThemeToggle variant="dark" />
          <Link href="/login" className="landing-nav-link">Sign in</Link>
          <Link href="/signup" className="landing-cta">Get Started</Link>
        </div>
      </nav>

      <article className="legal-body">
        <header className="legal-head">
          <div className="legal-kicker">Legal · Codessy</div>
          <h1>Privacy Policy</h1>
          <p className="legal-updated">Last updated: 30 September 2026 · Effective immediately</p>
          <p className="legal-intro">
            This Privacy Policy explains how <b>Codessy</b> (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;) — the cold-email
            automation platform, Chrome browser extension, job-application agent, and our upcoming{' '}
            <b>Interview Rooms</b> product — collects, uses, stores, and protects your information.
            By creating an account or using any Codessy service, you agree to this policy.
          </p>
        </header>

        <section>
          <h2>1. What Codessy does</h2>
          <p>Codessy is a multi-tenant SaaS that helps you:</p>
          <ul>
            <li><b>Send AI-personalized cold email</b> — import Excel/CSV recipients, connect your own Gmail via OAuth or SMTP, generate drafts with AI agents, review them, and schedule sends from your account.</li>
            <li><b>Hunt jobs automatically</b> — set preferences, upload resumes, connect job portals (LinkedIn, Naukri, Indeed, Wellfound, Hirist, Instahyre), search listings, score matches with AI, and submit applications through browser automation.</li>
            <li><b>Score resumes</b> — upload a PDF resume and receive an AI-generated score with section breakdowns, strengths, and missing keywords.</li>
            <li><b>Run interview practice sessions</b> (upcoming) — join one-to-one or panel Interview Rooms with live video, screen share, interviewer notes, and resume panels. Details in Section 7.</li>
          </ul>
        </section>

        <section id="collect">
          <h2>2. Information we collect</h2>
          <h3>2.1 Account information</h3>
          <p>When you sign up we collect your name, email address, phone number, and a bcrypt password hash. We never store or can recover your plaintext password.</p>

          <h3>2.2 Campaign and recipient data</h3>
          <p>If you import spreadsheets or add recipients, we store what you provide (names, company details, email addresses, job roles, industry, websites) solely to run your campaigns on your behalf. This data is tenant-isolated per account and is never sold or shared with other users.</p>

          <h3>2.3 Email credentials</h3>
          <p>When you connect Gmail via Google OAuth, we store an <b>encrypted refresh token</b> (Fernet encryption) so campaigns can send from your account. We do not receive or store your Google password. SMTP account passwords are encrypted at rest the same way.</p>

          <h3>2.4 AI model keys</h3>
          <p>If you configure your own AI provider (Anthropic, OpenAI, Gemini, etc.) or use admin-provisioned platform models, API keys are encrypted at rest and used only to generate content for your campaigns, agents, chatbot, matching, and interview features.</p>

          <h3>2.5 Job-hunting data</h3>
          <p>Resumes you upload (PDF text is extracted with pypdf), job preferences, applications, cover letters, screening answers, and job-portal session state are used to run job search and application features. Portal credentials are <b>never stored in our database</b> — login state lives in encrypted Playwright browser-profile storage on our server, scoped per user/platform.</p>

          <h3>2.6 Chrome extension data</h3>
          <p>The Codessy Chrome extension reads job postings you view (Greenhouse, Workday, Lever, Ashby, SmartRecruiters, and others) when you click &ldquo;Save Job&rdquo; or request a match score. Only the job fields shown in the side panel (title, company, location, description snippet) and your saved preferences are sent to your Codessy account. Browsing history is not collected.</p>

          <h3>2.7 Payments</h3>
          <p>Payments are processed by <b>Razorpay</b>. We receive payment status, order/subscription references, and limited billing metadata (plan, amount, currency). Full card numbers, CVV, and banking credentials never touch our servers.</p>

          <h3>2.8 Interview Rooms data (upcoming)</h3>
          <p>When Interview Rooms launch, the following additional data categories will apply. We will notify you before launch if this section changes materially:</p>
          <ul>
            <li><b>Session media</b> — audio/video streams and shared-screen content during a live interview. Streams are peer-to-peer/WebRTC where possible; if relayed through our servers they are processed in real time and <b>not stored</b> unless you explicitly opt into recording.</li>
            <li><b>Recordings</b> — if a session is recorded (Pro feature, opt-in per session), the recording is stored encrypted, visible only to room participants, and deletable at any time by the room host or candidate.</li>
            <li><b>Resumes in rooms</b> — the candidate&rsquo;s resume (already uploaded to their profile) is rendered in the interviewer panel. It is shown only to participants of that room and is not shared outside it.</li>
            <li><b>Interviewer notes &amp; chat</b> — notes typed by interviewers and in-room chat messages are stored per session to power post-session feedback. They are visible only to room participants.</li>
            <li><b>Scoring &amp; feedback</b> — interviewer ratings and AI-generated feedback reports are stored on your account so you can track improvement over time.</li>
            <li><b>Credits ledger</b> — a transaction log of interview credits earned (by interviewing others) and spent (by taking interviews), used for fraud prevention and balance integrity.</li>
          </ul>

          <h3>2.9 Usage data</h3>
          <p>We collect standard technical logs (IP address, browser type, pages visited, API request metadata, rate-limit events) for security, abuse prevention, and product improvement.</p>
        </section>

        <section id="use">
          <h2>3. How we use your information</h2>
          <ul>
            <li>To provide, operate, and maintain Codessy — sending emails, generating content, scoring resumes, searching and applying to jobs, and hosting interview sessions as instructed by you.</li>
            <li>To authenticate you and secure your account (JWT sessions, rate limiting, spam and abuse detection).</li>
            <li>To process payments and manage plans/credits via Razorpay.</li>
            <li>To provide customer support and respond to your requests.</li>
            <li>To send service-related notices (verification emails, security alerts, billing receipts, interview confirmations).</li>
            <li>To generate AI feedback on your interviews and applications, only within your own account.</li>
            <li>To improve the product (aggregated, de-identified analytics where feasible).</li>
          </ul>
          <p><b>We do not sell your personal data. We do not use your email content, resumes, interview media, or application data to train third-party AI models.</b> Prompts sent to AI providers include only what is needed for generation and are governed by each provider&rsquo;s data-handling terms.</p>
        </section>

        <section id="legal-basis">
          <h2>4. Legal basis (GDPR / DPDP Act 2023)</h2>
          <p>Where applicable, we process personal data on the basis of: (a) <b>performance of a contract</b> (providing the Service you signed up for, including hosting your interview sessions); (b) <b>legitimate interests</b> (securing the platform, preventing spam and fraud); (c) <b>consent</b> (recorded interviews, optional cookies, marketing emails); and (d) <b>legal obligation</b> (tax and accounting records).</p>
        </section>

        <section id="sharing">
          <h2>5. Sharing and disclosure</h2>
          <p>We share data only with:</p>
          <ul>
            <li><b>Infrastructure providers</b> — hosting, database, and storage (e.g. AWS) under confidentiality agreements.</li>
            <li><b>Payment provider</b> — Razorpay processes payments; we receive only payment status and references.</li>
            <li><b>AI providers</b> — only the minimal prompt content required for generation, under their API data policies.</li>
            <li><b>Google / OAuth providers</b> — when you explicitly connect an account.</li>
            <li><b>Job portals</b> — your own credentials and sessions are used to act on your behalf on platforms you connect (applying to jobs, saving listings).</li>
            <li><b>Other interview participants</b> — within an Interview Room, participants can see the candidate&rsquo;s video, shared screen, resume panel, and chat/notes as designed by the room layout. Nothing else is visible outside the room.</li>
            <li><b>Law enforcement</b> — when required by law or to protect rights, safety, and security.</li>
          </ul>
        </section>

        <section id="retention">
          <h2>6. Data retention</h2>
          <ul>
            <li>Account and campaign data are retained while your account is active.</li>
            <li>Job-portal browser sessions are deleted when you disconnect a portal or delete your account.</li>
            <li><b>Interview recordings</b> (if you opt in) are retained until you delete them or delete your account; transcripts and notes follow the same rule.</li>
            <li>Payment records are retained as required by Indian tax law.</li>
            <li>You may delete your account at any time from Settings; upon deletion we remove personal data within 30 days, except where retention is required for legal, tax, or dispute-resolution purposes. Encrypted OAuth tokens are destroyed with the account.</li>
          </ul>
        </section>

        <section id="cookies">
          <h2>7. Cookies and local storage</h2>
          <p>We use a strictly necessary auth token (stored in your browser&rsquo;s localStorage) to keep you signed in, and a theme preference key. We do not use third-party advertising cookies. The Chrome extension stores job-page data locally in your browser and only sends it to your Codessy account when you save a job or request a match score.</p>
        </section>

        <section id="interviews">
          <h2>8. Interview Rooms — special provisions (upcoming)</h2>
          <p>Our upcoming Interview Rooms feature lets you practice interviews in realistic settings. The following provisions specifically govern that feature:</p>
          <ul>
            <li><b>Participants consent by joining.</b> When you join a room you are informed who else is in the session. Audio/video capture happens only while you are an active participant; you can mute/stop your camera at any time.</li>
            <li><b>Recording requires explicit consent.</b> Recording is off by default. When enabled, all participants see a recording indicator. In jurisdictions requiring two-party consent, we will require every participant to acknowledge before recording starts.</li>
            <li><b>Credits, not cash, for peer interviews.</b> The free tier lets you earn interview credits by interviewing others and spend them to be interviewed. We keep a ledger of these transactions; this is anti-abuse data, not financial advice or employment services.</li>
            <li><b>No employment promises.</b> Codessy does not act as a recruiter, employer, or placement agency. Interview Rooms are practice/mock sessions between users (and, on paid tiers, potentially with experienced interviewer communities we onboard). Outcomes of interviews — real or mock — are never guaranteed.</li>
            <li><b>Conduct.</b> Recording, sharing, or republishing another user&rsquo;s interview media, resume, or notes without their permission is prohibited and may result in account termination.</li>
            <li><b>Deletion rights.</b> You may delete your recordings, notes, and feedback reports from your session history at any time. Room hosts can end sessions and delete room-level artifacts.</li>
          </ul>
        </section>

        <section id="security">
          <h2>9. Security</h2>
          <ul>
            <li>TLS encryption in transit for all API traffic.</li>
            <li>Fernet (AES-128-CBC) encryption at rest for OAuth tokens, SMTP passwords, and AI keys.</li>
            <li>bcrypt password hashing with per-user salts.</li>
            <li>Per-user tenant isolation — every query is scoped to your user ID.</li>
            <li>Least-privilege Gmail scopes (send only; we never request broad Gmail read permissions).</li>
            <li>Encrypted, per-user browser profiles for job-portal sessions; job-portal credentials are never written to our database.</li>
            <li>Interview media encrypted in transit (DTLS/SRTP for WebRTC); recordings encrypted at rest.</li>
          </ul>
          <p>No system is 100% secure. If we become aware of a breach affecting your data, we will notify you and regulators as required by applicable law.</p>
        </section>

        <section id="rights">
          <h2>10. Your rights</h2>
          <p>Depending on your jurisdiction (GDPR, DPDP Act 2023, CCPA), you may have the right to:</p>
          <ul>
            <li>Access the personal data we hold about you (including interview recordings and notes you participated in).</li>
            <li>Correct inaccurate data.</li>
            <li>Export your data in a portable format (recipient lists, resumes, campaign history, interview feedback).</li>
            <li>Delete your account and associated data, including recordings.</li>
            <li>Object to or restrict certain processing.</li>
            <li>Withdraw consent where processing is consent-based (e.g. opt out of recording).</li>
            <li>Lodge a complaint with a supervisory authority.</li>
          </ul>
          <p>To exercise any right, email <a href="mailto:support@codessy.site">support@codessy.site</a>. We respond within 30 days.</p>
        </section>

        <section id="children">
          <h2>11. Children&rsquo;s privacy</h2>
          <p>The Service is not directed at individuals under 18. Interview Rooms are intended for adult job seekers and professionals. We do not knowingly collect data from minors. If you believe a minor has provided us data, contact us and we will delete it.</p>
        </section>

        <section id="international">
          <h2>12. International transfers</h2>
          <p>Your data may be processed in countries other than your own (e.g. where our cloud infrastructure is located). We rely on appropriate safeguards — standard contractual clauses or equivalent mechanisms — for cross-border transfers. Interview streams may transit global CDN/WebRTC relay networks solely to deliver real-time media.</p>
        </section>

        <section id="changes">
          <h2>13. Changes to this policy</h2>
          <p>We may update this Privacy Policy from time to time. Material changes — including changes triggered by the launch of Interview Rooms or new data categories — will be announced in-app or by email before they take effect. Continued use of the Service after the effective date constitutes acceptance.</p>
        </section>

        <section id="contact">
          <h2>14. Contact</h2>
          <p>Questions about this policy or your data:</p>
          <ul>
            <li>Email: <a href="mailto:support@codessy.site">support@codessy.site</a></li>
            <li>Website: <a href="https://codessy.site">codessy.site</a></li>
          </ul>
        </section>
      </article>

      <footer className="landing-footer">
        <div className="landing-footer-bottom" style={{ marginTop: 0, paddingTop: 0, borderTop: 'none' }}>
          <span>&copy; {new Date().getFullYear()} Codessy. All rights reserved.</span>
          <span><Link href="/terms">Terms of Service</Link> · <Link href="/privacy">Privacy Policy</Link></span>
        </div>
      </footer>
    </div>
  );
}
