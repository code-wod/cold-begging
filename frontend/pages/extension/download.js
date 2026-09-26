import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';

const INSTALL_STEPS = [
  { step: 1, title: 'Download the extension', description: 'Click the download button below to get the extension ZIP file.' },
  { step: 2, title: 'Open Chrome extensions', description: 'Navigate to chrome://extensions in your browser address bar.' },
  { step: 3, title: 'Enable Developer mode', description: 'Toggle the "Developer mode" switch in the top-right corner.' },
  { step: 4, title: 'Load unpacked extension', description: 'Click "Load unpacked" and select the extracted extension folder.' },
  { step: 5, title: 'Pin the extension', description: 'Click the puzzle icon in your toolbar and pin Codessy.' },
  { step: 6, title: 'Sign in and go', description: 'Open the side panel, sign in with your account, and start autofilling.' },
];

const FEATURES = [
  { icon: '⚡', title: 'Universal Detection', desc: 'Works on Greenhouse, Workday, Lever, Ashby, and any career page' },
  { icon: '🧠', title: 'AI-Powered Mapping', desc: 'Understands field labels in any language or format' },
  { icon: '✓', title: 'Review Before Fill', desc: 'Confidence scoring — you approve every field' },
  { icon: '🔒', title: 'Privacy First', desc: 'Data stays in your browser until you sign in' },
  { icon: '💡', title: 'Learns Your Answers', desc: 'Remembers custom Q&A for recurring questions' },
  { icon: '🔄', title: 'Multi-Step Forms', desc: 'Navigates through pages automatically' },
];

export default function ExtensionDownload() {
  const [downloading, setDownloading] = useState(false);
  const [version, setVersion] = useState('');

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const apiUrl = base.endsWith('/api') ? base : `${base}/api`;
    fetch(`${apiUrl}/extension/version`)
      .then(r => r.json())
      .then(d => setVersion(d.version))
      .catch(() => {});
  }, []);

  async function handleDownload() {
    setDownloading(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const apiUrl = base.endsWith('/api') ? base : `${base}/api`;
      const res = await fetch(`${apiUrl}/extension/download`);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cold-begging-extension.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      alert('Download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  }

  const s = {
    page: { maxWidth: 900, margin: '0 auto', padding: '40px 20px' },
    hero: { textAlign: 'center', padding: '60px 0 40px' },
    badge: { display: 'inline-block', padding: '6px 16px', background: '#ff9900', color: '#fff', borderRadius: 20, fontSize: 13, fontWeight: 600, marginBottom: 20 },
    h1: { fontSize: 36, fontWeight: 800, margin: '0 0 16px', lineHeight: 1.2 },
    heroP: { fontSize: 16, color: '#666', maxWidth: 600, margin: '0 auto 24px', lineHeight: 1.6 },
    dlBtn: { display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 32px', background: '#ff9900', color: '#fff', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: 'pointer' },
    hint: { fontSize: 13, color: '#999', marginTop: 12 },
    section: { margin: '60px 0' },
    sectionH2: { fontSize: 24, fontWeight: 700, textAlign: 'center', marginBottom: 8 },
    sectionSub: { textAlign: 'center', color: '#666', marginBottom: 32 },
    grid3: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, marginTop: 32 },
    featureCard: { padding: 24, background: '#f8f9fa', borderRadius: 12, textAlign: 'center' },
    featureIcon: { fontSize: 32, marginBottom: 12 },
    featureH3: { fontSize: 15, margin: '0 0 8px' },
    featureP: { fontSize: 13, color: '#666', margin: 0 },
    stepsWrap: { maxWidth: 600, margin: '0 auto' },
    step: { display: 'flex', gap: 16, marginBottom: 20, alignItems: 'flex-start' },
    stepNum: { width: 32, height: 32, background: '#ff9900', color: '#fff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, flexShrink: 0 },
    stepH3: { fontSize: 15, margin: '0 0 4px' },
    stepP: { fontSize: 13, color: '#666', margin: 0 },
    ctaCenter: { textAlign: 'center', marginTop: 32 },
    flow: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginTop: 32, flexWrap: 'wrap' },
    flowStep: { textAlign: 'center', padding: 20, background: '#f8f9fa', borderRadius: 12, minWidth: 160 },
    flowIcon: { fontSize: 28, marginBottom: 8 },
    flowH3: { fontSize: 14, margin: '0 0 4px' },
    flowP: { fontSize: 12, color: '#666', margin: 0 },
    flowArrow: { fontSize: 24, color: '#ccc' },
    platforms: { display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginTop: 24 },
    platformTag: { padding: '8px 20px', background: '#f0f0f0', borderRadius: 20, fontSize: 14, fontWeight: 500 },
    secGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, marginTop: 32 },
    secCard: { padding: 24, background: '#f8f9fa', borderRadius: 12 },
    secH3: { fontSize: 15, margin: '0 0 8px' },
    secP: { fontSize: 13, color: '#666', margin: 0, lineHeight: 1.5 },
  };

  return (
    <Layout>
      <div style={s.page}>
        <div style={s.hero}>
          <div style={s.badge}>Chrome Extension {version && `v${version}`}</div>
          <h1 style={s.h1}>Fill every job application<br />in one click</h1>
          <p style={s.heroP}>
            Our browser extension detects application forms, maps your profile to
            every field, and fills them instantly. Works across Greenhouse, Workday,
            Lever, Ashby, and any custom career page.
          </p>
          <button style={s.dlBtn} onClick={handleDownload} disabled={downloading}>
            {downloading ? 'Downloading...' : 'Download Extension'}
          </button>
          <p style={s.hint}>Free · No Chrome Web Store required · Works offline</p>
        </div>

        <section style={s.section}>
          <h2 style={s.sectionH2}>Why use the extension?</h2>
          <div style={s.grid3}>
            {FEATURES.map(f => (
              <div key={f.title} style={s.featureCard}>
                <div style={s.featureIcon}>{f.icon}</div>
                <h3 style={s.featureH3}>{f.title}</h3>
                <p style={s.featureP}>{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section style={s.section}>
          <h2 style={s.sectionH2}>How to install</h2>
          <p style={s.sectionSub}>
            Chrome doesn't allow installing extensions outside the Web Store by default.
            Here's how to sideload it in 60 seconds:
          </p>
          <div style={s.stepsWrap}>
            {INSTALL_STEPS.map(st => (
              <div key={st.step} style={s.step}>
                <div style={s.stepNum}>{st.step}</div>
                <div>
                  <h3 style={s.stepH3}>{st.title}</h3>
                  <p style={s.stepP}>{st.description}</p>
                </div>
              </div>
            ))}
          </div>
          <div style={s.ctaCenter}>
            <button style={s.dlBtn} onClick={handleDownload} disabled={downloading}>
              {downloading ? 'Downloading...' : 'Download Extension'}
            </button>
          </div>
        </section>

        <section style={s.section}>
          <h2 style={s.sectionH2}>How it works</h2>
          <div style={s.flow}>
            <div style={s.flowStep}><div style={s.flowIcon}>🌐</div><h3 style={s.flowH3}>Visit a job page</h3><p style={s.flowP}>Navigate to any career page</p></div>
            <div style={s.flowArrow}>→</div>
            <div style={s.flowStep}><div style={s.flowIcon}>🔍</div><h3 style={s.flowH3}>Auto-detection</h3><p style={s.flowP}>Extension finds the form</p></div>
            <div style={s.flowArrow}>→</div>
            <div style={s.flowStep}><div style={s.flowIcon}>📋</div><h3 style={s.flowH3}>Review fields</h3><p style={s.flowP}>See confidence scores</p></div>
            <div style={s.flowArrow}>→</div>
            <div style={s.flowStep}><div style={s.flowIcon}>⚡</div><h3 style={s.flowH3}>Fill instantly</h3><p style={s.flowP}>One click. Submit manually.</p></div>
          </div>
        </section>

        <section style={s.section}>
          <h2 style={s.sectionH2}>Supported platforms</h2>
          <div style={s.platforms}>
            {['Greenhouse', 'Workday', 'Lever', 'Ashby', 'SmartRecruiters', 'Any career page'].map(p => (
              <div key={p} style={s.platformTag}>{p}</div>
            ))}
          </div>
        </section>

        <section style={s.section}>
          <h2 style={s.sectionH2}>Your data stays yours</h2>
          <div style={s.secGrid}>
            <div style={s.secCard}>
              <h3 style={s.secH3}>Local storage</h3>
              <p style={s.secP}>Your profile lives in your browser. Nothing leaves your machine until you sign in.</p>
            </div>
            <div style={s.secCard}>
              <h3 style={s.secH3}>Encrypted sync</h3>
              <p style={s.secP}>When you sign in, data syncs over encrypted HTTPS with the same encryption as your account.</p>
            </div>
            <div style={s.secCard}>
              <h3 style={s.secH3}>No auto-submit</h3>
              <p style={s.secP}>The extension never clicks Submit. You make the final decision on every application.</p>
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
