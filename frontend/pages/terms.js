import Link from 'next/link';
import Logo from '../components/Logo';
import ThemeToggle from '../components/ThemeToggle';

const NAV = [
  ['#acceptable', 'Acceptable use'],
  ['#interviews', 'Interview Rooms'],
  ['#billing', 'Billing'],
  ['#ai', 'AI content'],
  ['#liability', 'Liability'],
];

export default function Terms() {
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
          <h1>Terms of Service</h1>
          <p className="legal-updated">Last updated: 30 September 2026 · Effective immediately</p>
          <p className="legal-intro">
            These Terms of Service (&ldquo;Terms&rdquo;) govern your access to and use of <b>Codessy</b> — including the
            website, APIs, Chrome browser extension, job-application agent, cold-email automation platform, and
            our upcoming <b>Interview Rooms</b> product (together, the &ldquo;Service&rdquo;). By creating an account or
            using the Service, you agree to these Terms. If you do not agree, do not use the Service.
          </p>
        </header>

        <section id="eligibility">
          <h2>1. Eligibility &amp; accounts</h2>
          <ul>
            <li>You must be at least 18 years old and capable of entering a binding contract.</li>
            <li>You must provide accurate registration information and keep it up to date.</li>
            <li>You are responsible for all activity under your account, including your API keys, connected email accounts, connected job portals, and interview sessions you host or join.</li>
            <li>One person may not maintain multiple free accounts to circumvent plan limits (including free email credits, free resume-score checks, and free interview credits). We may suspend accounts that do.</li>
            <li>Notify us immediately at <a href="mailto:support@codessy.site">support@codessy.site</a> if you suspect unauthorized access to your account.</li>
          </ul>
        </section>

        <section id="the-service">
          <h2>2. The Service</h2>
          <p>Codessy provides tools for:</p>
          <ul>
            <li><b>Cold-email outreach</b> — import recipients (Excel/CSV), configure AI agents, generate personalized emails, review/approve drafts, and schedule or send emails via your own connected Gmail (OAuth) or SMTP account.</li>
            <li><b>Job-search automation</b> — set preferences, upload resumes, connect job portals (LinkedIn, Naukri, Indeed, Wellfound, Hirist, Instahyre), search listings, score job matches with AI, generate cover letters and screening answers, and submit applications through browser automation on your behalf.</li>
            <li><b>Resume scoring</b> — upload a PDF resume and receive AI-generated scores, section breakdowns, and improvement suggestions, subject to plan-based check limits.</li>
            <li><b>Chrome extension</b> — save job postings from ATS sites into your Codessy account and view AI match scores for your saved preferences.</li>
            <li><b>Interview Rooms (upcoming)</b> — live one-to-one and panel mock-interview sessions with video, screen share, resume panels, interviewer notes, chat, optional recordings, and AI feedback reports. Section 5 provides additional terms for this feature.</li>
          </ul>
          <p>Features may vary by plan. We may modify, add, or remove features at any time; we will not materially reduce paid-plan features without notice. &ldquo;DRY RUN&rdquo; mode may be enabled by default for job applications — in that mode the agent fills forms but does not click final submit until you disable dry-run.</p>
        </section>

        <section id="acceptable">
          <h2>3. Acceptable use — anti-spam &amp; platform integrity</h2>
          <p>You agree <b>not</b> to use the Service to:</p>
          <ul>
            <li>Send unsolicited bulk email in violation of the CAN-SPAM Act, India&rsquo;s DPDP Act &amp; IT Rules, CASL, GDPR e-privacy rules, or any other applicable anti-spam law.</li>
            <li>Send to purchased, harvested, or scraped lists of addresses you did not obtain with a lawful basis for contacting.</li>
            <li>Mislead recipients about who you are — send only from an account you control, with accurate identifying information and a working opt-out path. You must honor opt-out requests promptly.</li>
            <li>Deceive, harass, defraud, or impersonate any person or organization.</li>
            <li>Distribute malware, phishing content, or links to harmful material.</li>
            <li>Probe, scan, or test the vulnerability of our systems, or circumvent authentication/authorization controls.</li>
            <li>Reverse engineer the Service except to the extent such restriction is prohibited by law.</li>
            <li>Resell or white-label the Service without a written agreement with us.</li>
            <li>Use the Service to violate the terms of any third-party platform you integrate (Gmail, LinkedIn, Naukri, Indeed, Wellfound, Hirist, Instahyre, Greenhouse, Lever, Ashby, etc.).</li>
            <li>Automate job applications in a way that violates a portal&rsquo;s terms, or apply to jobs at a volume that harms the platform — you are responsible for every application submitted from your connected accounts.</li>
            <li>Use AI-generated emails or applications to deceive hiring managers or recruiters about your qualifications, work history, or availability.</li>
          </ul>
          <p>We may suspend or terminate accounts that send spam, create recipient complaints, trigger provider blocks (e.g. Gmail rate limits or domain reputation damage), or abuse job-portal automation. You own your sending reputation; we provide rate limits and controls, but you remain responsible for how the Service is used.</p>
        </section>

        <section id="customer-data">
          <h2>4. Your data &amp; connected accounts</h2>
          <ul>
            <li>You retain all rights to the content you import, create, or store in Codessy (recipient lists, email drafts, resumes, job data, interview recordings you made).</li>
            <li>You grant us a limited, non-exclusive license to process this data solely to provide the Service to you (storing, generating, sending, streaming as you instruct).</li>
            <li>You are responsible for the accuracy and legality of recipient data you upload and for obtaining any consents required to contact those individuals.</li>
            <li>You are responsible for complying with the terms of any email provider or job portal you connect, and for securing access to those accounts.</li>
            <li>Job-portal browser sessions are stored locally in per-user browser profiles on our server. Do not share your Codessy account credentials — anyone with your session can act on your connected portals.</li>
          </ul>
        </section>

        <section id="interviews">
          <h2>5. Interview Rooms — additional terms (upcoming)</h2>
          <p>Interview Rooms are live practice sessions between users. The following terms apply in addition to the rest of this agreement:</p>
          <h3>5.1 Nature of the service</h3>
          <ul>
            <li>Codessy is <b>not</b> a recruiter, employer, staffing agency, or placement service. Interview Rooms are mock/practice sessions. Participation does not create any employment relationship, interview invitation, or hiring commitment with Codessy or any other participant.</li>
            <li>On free tiers, you earn <b>interview credits</b> by interviewing other users and spend credits to be interviewed. Credits have no cash value, are non-transferable between accounts, and may expire per plan rules.</li>
            <li>On paid tiers (Pro), you may access panel rooms (2–3 interviewers), live screen share, interviewer notes, AI feedback reports, and session recordings.</li>
          </ul>
          <h3>5.2 Consent, recording &amp; conduct</h3>
          <ul>
            <li>By joining a room you consent to being seen/heard by other room participants for the duration of the session.</li>
            <li>Recording is <b>off by default</b>. When a host enables recording, all participants see a recording indicator and must acknowledge before recording starts where required by law (e.g. two-party consent jurisdictions).</li>
            <li>You may not record, screenshot, stream, or republish another user&rsquo;s interview media, resume, notes, or chat without their explicit permission. Violations will result in immediate suspension and may incur legal liability.</li>
            <li>Be professional. Harassment, discrimination, hate speech, sexual content, or any abusive behavior in a room will result in removal and account termination.</li>
            <li>Resumes shown in the room panel are visible only to room participants and must be used solely for the purpose of that interview session.</li>
          </ul>
          <h3>5.3 Feedback &amp; AI reports</h3>
          <ul>
            <li>Interviewer ratings and AI-generated feedback are opinions/advisory content, not professional career counseling or guarantees of interview performance.</li>
            <li>You can delete your recordings, notes, and feedback from session history at any time. Room hosts can end sessions and delete room-level artifacts.</li>
          </ul>
        </section>

        <section id="ai">
          <h2>6. AI-generated content</h2>
          <ul>
            <li>Content generated by AI (email drafts, cover letters, screening answers, match scores, interview feedback) may be inaccurate or unsuitable. <b>Review and approve everything before it is sent, submitted, or relied upon.</b></li>
            <li>AI features rely on third-party model providers (e.g. Anthropic, OpenAI, Google). Availability and output quality may vary; managed platform models may be changed or retired.</li>
            <li>You are responsible for the lawful use of AI-generated content, including compliance with advertising, employment, privacy, and anti-discrimination laws.</li>
            <li>Free plans require you to bring your own AI API key for generation. Managed (platform) AI models are a paid-plan feature.</li>
            <li>Platform-provided AI models are for use within Codessy only; you may not scrape, resell, or build competing products on our managed model access.</li>
          </ul>
        </section>

        <section id="billing">
          <h2>7. Plans, credits &amp; payments</h2>
          <ul>
            <li><b>Free plan:</b> limited features and monthly caps (e.g. hourly send rate ≤10, limited resume-score checks, limited interview credits). We may change free-plan limits over time.</li>
            <li><b>Starter (₹49 one-time):</b> grants a fixed pool of email credits (currently 200) with no expiry, plus increased resume-score checks.</li>
            <li><b>Pro (₹99/month):</b> auto-renews monthly until cancelled. Includes managed AI model, higher send rates (up to 50/hour), unlimited resume-score checks, unlimited panel Interview Rooms, recordings, and AI feedback. Cancel anytime from Billing — access continues through the paid period; no partial refunds.</li>
            <li><b>Credits</b> (email credits, resume-score checks, interview credits) are non-transferable, non-refundable once used, and have no cash value.</li>
            <li>Payments are processed by <b>Razorpay</b>. Your purchase is also governed by Razorpay&rsquo;s terms. We may use Razorpay webhooks to confirm payment status.</li>
            <li>Prices include applicable taxes unless stated otherwise. We may change prices with at least 30 days&rsquo; notice for renewing subscriptions.</li>
            <li>Refunds: if a payment was taken in error, contact us within 14 days and we will refund it. Otherwise, fees are non-refundable to the extent permitted by law.</li>
            <li>Failure to pay may result in suspension of paid features until the account is brought current.</li>
            <li>Per-campaign send caps (max emails per campaign) and hourly/daily rate limits are enforced server-side as abuse protection; they are not separately purchasable features.</li>
          </ul>
        </section>

        <section id="third-party">
          <h2>8. Third-party services</h2>
          <p>The Service integrates with third parties (Google OAuth/Gmail, Razorpay, AI model providers, job portals such as LinkedIn, Naukri, Indeed, Wellfound, Hirist, Instahyre, and ATS platforms like Greenhouse, Lever, Ashby). Your use of those services is governed by their own terms. We are not responsible for third-party outages, policy changes, captchas, or actions taken by those platforms against your accounts (including bans or rate limits from automation).</p>
        </section>

        <section id="ip">
          <h2>9. Intellectual property</h2>
          <ul>
            <li>Codessy owns the Service, including software, branding, design, and documentation. These Terms do not grant you any ownership of the Service.</li>
            <li>You own your content (data you import or generate for your own use).</li>
            <li>Feedback you provide may be used to improve the Service without obligation to you.</li>
          </ul>
        </section>

        <section id="termination">
          <h2>10. Suspension &amp; termination</h2>
          <ul>
            <li>You may delete your account at any time from Settings.</li>
            <li>We may suspend or terminate access for breach of these Terms, abusive or illegal use, anti-spam violations, non-payment, or risk to the platform or other users.</li>
            <li>Where possible and lawful, we will give notice before termination for non-urgent causes.</li>
            <li>Upon termination, your right to use the Service ceases, including access to interview recordings and campaign data (subject to our retention schedule in the Privacy Policy). Provisions that by nature should survive (payment obligations, disclaimers, liability limits, IP, conduct obligations) will survive.</li>
          </ul>
        </section>

        <section id="disclaimer">
          <h2>11. Disclaimers</h2>
          <p>THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. WE DO NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED, ERROR-FREE, OR SECURE; THAT EMAILS WILL ALWAYS BE DELIVERED; THAT AI OUTPUT WILL BE ACCURATE; THAT JOB APPLICATIONS WILL RESULT IN INTERVIEWS OR OFFERS; OR THAT INTERVIEW ROOM SESSIONS WILL BE FREE OF DISRUPTIONS. DELIVERABILITY, REPLY RATES, AND JOB OUTCOMES DEPEND ON MANY FACTORS OUTSIDE OUR CONTROL.</p>
        </section>

        <section id="liability">
          <h2>12. Limitation of liability</h2>
          <p>TO THE MAXIMUM EXTENT PERMITTED BY LAW, CODESSY AND ITS OFFICERS, EMPLOYEES, AND AFFILIATES WILL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, DATA, GOODWILL, OR REPUTATION, ARISING FROM YOUR USE OF (OR INABILITY TO USE) THE SERVICE, EVEN IF ADVISED OF THE POSSIBILITY. OUR TOTAL AGGREGATE LIABILITY FOR ALL CLAIMS RELATING TO THE SERVICE WILL NOT EXCEED THE GREATER OF (A) THE AMOUNT YOU PAID TO US IN THE 12 MONTHS BEFORE THE CLAIM OR (B) ₹5,000 (FIVE THOUSAND RUPEES). NOTHING IN THESE TERMS LIMITS LIABILITY THAT CANNOT BE LIMITED BY LAW.</p>
        </section>

        <section id="indemnity">
          <h2>13. Indemnity</h2>
          <p>You agree to indemnify and hold Codessy harmless from claims, damages, and expenses (including reasonable legal fees) arising from: (a) your content or recipient data; (b) your use of the Service in breach of these Terms or applicable law, including spam complaints or job-portal violations; (c) your connected email accounts or job-portal actions; (d) your conduct or content in Interview Rooms, including unauthorized recording or republishing of another user&rsquo;s media; or (e) your infringement of any third-party rights.</p>
        </section>

        <section id="changes">
          <h2>14. Changes to these Terms</h2>
          <p>We may update these Terms from time to time. Material changes — including changes triggered by the launch of Interview Rooms or new paid features — will be announced in-app or by email before they take effect. Continuing to use the Service after the effective date constitutes acceptance of the updated Terms.</p>
        </section>

        <section id="law">
          <h2>15. Governing law &amp; disputes</h2>
          <p>These Terms are governed by the laws of <b>India</b>, without regard to conflict-of-law principles. Any dispute shall be subject to the exclusive jurisdiction of the courts of <b>Karnataka, Bengaluru</b>. Before filing a claim, you agree to try to resolve the dispute informally by contacting us at <a href="mailto:support@codessy.site">support@codessy.site</a> and allowing 30 days for a response.</p>
        </section>

        <section id="general">
          <h2>16. General</h2>
          <ul>
            <li>These Terms constitute the entire agreement between you and Codessy regarding the Service.</li>
            <li>If any provision is found unenforceable, the remaining provisions continue in effect.</li>
            <li>Failure to enforce a provision is not a waiver.</li>
            <li>You may not assign these Terms without our consent; we may assign them in connection with a merger, acquisition, or sale of assets.</li>
          </ul>
        </section>

        <section id="contact">
          <h2>17. Contact</h2>
          <p>Questions about these Terms:</p>
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
