import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import { api } from '../lib/api';
import { Button, Field, Input } from '../components/ui';
import ThemeToggle from '../components/ThemeToggle';
import Logo from '../components/Logo';
import AuthAside from '../components/AuthAside';

export default function Login() {
  const { login, finishGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [verified, setVerified] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [consentError, setConsentError] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  // Password reset state
  const resetToken = typeof window !== 'undefined'
    ? new URLSearchParams(window.location.search).get('reset_token')
    : null;
  const [resetPw, setResetPw] = useState('');
  const [resetConfirm, setResetConfirm] = useState('');
  const [resetBusy, setResetBusy] = useState(false);
  const [resetDone, setResetDone] = useState(false);
  const [resetError, setResetError] = useState('');

  useEffect(() => {
    const verifiedParam = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('verified');
    if (verifiedParam === '1') {
      setVerified(true);
      window.history.replaceState(null, '', '/login');
    }

    const hashParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.hash.replace(/^#/, '')) : null;
    const token = hashParams?.get('google_token');
    if (token) {
      finishGoogle(token)
        .then(() => router.replace(hashParams.get('new') === '1' ? '/onboarding' : '/dashboard'))
        .catch((e) => setError(e.message))
        .finally(() => window.history.replaceState(null, '', '/login'));
    } else if (hashParams?.get('google_error')) {
      setError('Google sign-in failed or was cancelled.');
      window.history.replaceState(null, '', '/login');
    }
  }, []);

  const detectCaps = (e) => {
    if (typeof e.getModifierState === 'function') setCapsLock(e.getModifierState('CapsLock'));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!agreed) { setConsentError(true); return; }
    setConsentError(false);
    setBusy(true);
    setError('');
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setResetError('');
    if (resetPw.length < 8) { setResetError('Password must be at least 8 characters'); return; }
    if (resetPw !== resetConfirm) { setResetError('Passwords do not match'); return; }
    setResetBusy(true);
    try {
      await api('/api/auth/reset-password', {
        method: 'POST',
        body: { token: resetToken, new_password: resetPw },
      });
      setResetDone(true);
      window.history.replaceState(null, '', '/login');
    } catch (e) {
      setResetError(e.message || 'Invalid or expired token');
    } finally {
      setResetBusy(false);
    }
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

  return (
    <div className="auth-split">
      <AuthAside
        kicker="Cold email automation"
        title="Outreach that"
        titleAccent="actually gets replies"
        sub="Import a spreadsheet, pick an AI agent, and Codessy researches each recipient, writes a tailored email, and sends it from your own Gmail."
      />

      <div className="auth-form-side">
        <div className="auth-form-theme"><ThemeToggle /></div>
        <div className="auth-form-box">
          <div className="auth-form-head">
            <div className="auth-form-logo">
              <Logo size={38} showText={false} color="#fff" />
            </div>

            {/* ── Password reset form ─────────────────────────── */}
            {resetToken && !resetDone ? (
              <>
                <h1>Reset your password</h1>
                <p>Choose a new password for your account.</p>
              </>
            ) : resetDone ? (
              <>
                <h1>Password updated</h1>
                <p>Your password has been reset. You can now sign in.</p>
              </>
            ) : (
              <>
                <h1>Welcome back</h1>
                <p>Sign in to your Codessy workspace.</p>
              </>
            )}
          </div>

          {resetToken && !resetDone ? (
            <>
              {resetError && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{resetError}</div>}
              <form onSubmit={handleReset}>
                <Field label="New password">
                  <div className="input-with-toggle">
                    <Input type={showPw ? 'text' : 'password'} required value={resetPw}
                      onChange={(e) => setResetPw(e.target.value)}
                      onKeyUp={detectCaps} onKeyDown={detectCaps}
                      placeholder="At least 8 characters" minLength={8} />
                    <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                      {showPw ? '🙈' : '👁️'}
                    </button>
                  </div>
                  {capsLock && <div className="pw-caps-warn">⚠️ Caps Lock is on</div>}
                </Field>
                <Field label="Confirm password">
                  <Input type="password" required value={resetConfirm}
                    onChange={(e) => setResetConfirm(e.target.value)}
                    onKeyUp={detectCaps} onKeyDown={detectCaps}
                    placeholder="Re-enter password" minLength={8} />
                </Field>
                <Button type="submit" disabled={resetBusy || !resetPw || !resetConfirm} style={{ width: '100%', justifyContent: 'center' }}>
                  {resetBusy ? 'Resetting…' : 'Reset password'}
                </Button>
              </form>
              <div className="auth-alt-link">
                <Link href="/login" onClick={(e) => { e.preventDefault(); window.history.replaceState(null, '', '/login'); router.replace('/login'); }}>
                  Back to sign in
                </Link>
              </div>
            </>
          ) : resetDone ? (
            <>
              <Button onClick={() => { setResetDone(false); window.history.replaceState(null, '', '/login'); }}
                style={{ width: '100%', justifyContent: 'center' }}>
                Sign in
              </Button>
            </>
          ) : (
            <>
              {verified && (
                <div className="toast success" style={{ position: 'static', marginBottom: 14 }}>
                  Your email has been verified! You can now sign in.
                </div>
              )}
              {error && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{error}</div>}
              <form onSubmit={submit}>
                <Field label="Email">
                  <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" />
                </Field>
                <Field label="Password">
                  <div className="input-with-toggle">
                    <Input type={showPw ? 'text' : 'password'} required value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyUp={detectCaps} onKeyDown={detectCaps}
                      placeholder="Enter your password" autoComplete="current-password" />
                    <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                      {showPw ? '🙈' : '👁️'}
                    </button>
                  </div>
                  {capsLock && <div className="pw-caps-warn">⚠️ Caps Lock is on</div>}
                </Field>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
                  <Link href="/forgot-password" style={{ fontSize: 12.5 }}>Forgot password?</Link>
                </div>
                <label className="auth-consent">
                  <input type="checkbox" checked={agreed} onChange={(e) => { setAgreed(e.target.checked); setConsentError(false); }} />
                  <span>
                    I agree to the <Link href="/terms" target="_blank">Terms of Service</Link> and{' '}
                    <Link href="/privacy" target="_blank">Privacy Policy</Link>, including consent to receive
                    transactional emails and account-related communications.
                  </span>
                </label>
                {consentError && <div className="auth-consent-error">Please accept the Terms and Privacy Policy to continue.</div>}
                <Button type="submit" disabled={busy || !agreed} style={{ width: '100%', justifyContent: 'center' }}>
                  {busy ? 'Signing in…' : 'Sign in'}
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
                New to Codessy? <Link href="/signup">Create an account</Link>
              </div>
              <div className="auth-social-note">
                <span className="lock">🔒</span> OAuth via Google · Your credentials never touch our servers
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
