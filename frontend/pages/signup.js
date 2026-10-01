import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import { api } from '../lib/api';
import { Button, Field, Input } from '../components/ui';
import ThemeToggle from '../components/ThemeToggle';
import Logo from '../components/Logo';
import AuthAside from '../components/AuthAside';

const scorePassword = (pw) => {
  if (!pw) return 0;
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return Math.min(s, 4);
};
const STRENGTH = [
  { cls: '', label: 'Too short — use at least 8 characters' },
  { cls: 'pw-strength-s1', label: 'Weak — add numbers or symbols' },
  { cls: 'pw-strength-s2', label: 'Fair — mix in upper & lowercase' },
  { cls: 'pw-strength-s3', label: 'Good password' },
  { cls: 'pw-strength-s4', label: 'Strong password' },
];

export default function Signup() {
  const { signup } = useAuth();
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [consentError, setConsentError] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  const strength = scorePassword(password);
  const strengthMeta = STRENGTH[strength];

  const detectCaps = (e) => {
    if (typeof e.getModifierState === 'function') setCapsLock(e.getModifierState('CapsLock'));
  };

  const google = async () => {
    if (!agreed) { setConsentError(true); return; }
    setConsentError(false);
    setGoogleBusy(true);
    setError('');
    try {
      const res = await api('/api/auth/google');
      window.location.href = res.authorize_url;
    } catch (err) {
      setError(err.message);
      setGoogleBusy(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!agreed) { setConsentError(true); return; }
    setConsentError(false);
    setBusy(true);
    setError('');
    try {
      await signup(email, password, name, phone);
      setSubmitted(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-split">
      <AuthAside
        kicker="Free forever plan"
        title="Start sending"
        titleAccent="in minutes"
        sub="Create your account, connect your Gmail, and let the AI agent research and draft personalized outreach — while you review and approve."
      />

      <div className="auth-form-side">
        <div className="auth-form-theme"><ThemeToggle /></div>
        <div className="auth-form-box">
          <div className="auth-form-head">
            <div className="auth-form-logo">
              <Logo size={38} showText={false} color="#fff" />
            </div>
            {submitted ? (
              <>
                <h1>Check your email</h1>
                <p>We sent a verification link to <b>{email}</b>.</p>
              </>
            ) : (
              <>
                <h1>Create your account</h1>
                <p>Free plan · No credit card required</p>
              </>
            )}
          </div>

          {submitted ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 44, marginBottom: 14 }}>📧</div>
              <p className="muted" style={{ fontSize: 13.5, marginBottom: 18 }}>
                Click the link in that email to verify your account, then sign in to start your first campaign.
              </p>
              <Button variant="secondary" onClick={() => router.push('/login')} style={{ width: '100%', justifyContent: 'center' }}>
                Back to sign in
              </Button>
            </div>
          ) : (
            <>
              {error && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{error}</div>}
              <form onSubmit={submit}>
                <Field label="Full name">
                  <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ada Lovelace" autoComplete="name" />
                </Field>
                <Field label="Work email">
                  <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" />
                </Field>
                <Field label="Phone number" help="Required to reduce duplicate requests">
                  <Input type="tel" required value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1234567890" autoComplete="tel" />
                </Field>
                <Field label="Password" help="At least 8 characters.">
                  <div className="input-with-toggle">
                    <Input type={showPw ? 'text' : 'password'} required minLength={8} value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyUp={detectCaps} onKeyDown={detectCaps}
                      placeholder="Create a strong password" autoComplete="new-password" />
                    <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                      {showPw ? '🙈' : '👁️'}
                    </button>
                  </div>
                  {password.length > 0 && (
                    <div className={`pw-strength ${strengthMeta.cls}`}>
                      <div className="pw-strength-bar"><div className="pw-strength-fill" /></div>
                      <div className="pw-strength-label"><b>{strengthMeta.label.split(' — ')[0]}</b>{strengthMeta.label.includes(' — ') ? ` — ${strengthMeta.label.split(' — ')[1]}` : ''}</div>
                    </div>
                  )}
                  {capsLock && <div className="pw-caps-warn">⚠️ Caps Lock is on</div>}
                </Field>
                <label className="auth-consent">
                  <input type="checkbox" checked={agreed} onChange={(e) => { setAgreed(e.target.checked); setConsentError(false); }} />
                  <span>
                    I agree to the <Link href="/terms" target="_blank">Terms of Service</Link> and{' '}
                    <Link href="/privacy" target="_blank">Privacy Policy</Link>, including consent to receive
                    transactional emails, verification links, and account-related communications.
                  </span>
                </label>
                {consentError && <div className="auth-consent-error">Please accept the Terms and Privacy Policy to continue.</div>}
                <Button type="submit" disabled={busy || !agreed} style={{ width: '100%', justifyContent: 'center' }}>
                  {busy ? 'Creating account…' : 'Get started free'}
                </Button>
              </form>
              <div className="flex" style={{ alignItems: 'center', gap: 10, margin: '16px 0' }}>
                <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                <span className="muted" style={{ fontSize: 12 }}>or</span>
                <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
              </div>
              <Button variant="secondary" disabled={googleBusy || !agreed} onClick={google} style={{ width: '100%', justifyContent: 'center' }}>
                {googleBusy ? 'Redirecting to Google…' : 'Continue with Google'}
              </Button>
              <div className="auth-alt-link">
                Already have an account? <Link href="/login">Sign in</Link>
              </div>
              <div className="auth-social-note">
                <span className="lock">🔒</span> Your data is encrypted at rest · Never sold to third parties
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
