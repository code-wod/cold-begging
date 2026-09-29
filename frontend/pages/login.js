import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import { api } from '../lib/api';
import { Button, Field, Input, Panel } from '../components/ui';
import ThemeToggle from '../components/ThemeToggle';
import Logo from '../components/Logo';

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

  const submit = async (e) => {
    e.preventDefault();
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

  // ── Password reset form ──────────────────────────────────────────────
  if (resetToken && !resetDone) {
    return (
      <div className="auth-wrap">
        <div className="auth-theme"><ThemeToggle /></div>
        <Panel bodyClassName="panel-body">
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <Logo size={40} showText={false} color="#fff" style={{ justifyContent: 'center' }} />
            <h1 style={{ fontSize: 20, marginTop: 12 }}>Reset Password</h1>
            <p className="muted mb-0">Enter your new password below.</p>
          </div>
          {resetError && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{resetError}</div>}
          <form onSubmit={handleReset}>
            <Field label="New Password">
              <div className="input-with-toggle">
                <Input type={showPw ? 'text' : 'password'} required value={resetPw}
                  onChange={(e) => setResetPw(e.target.value)} placeholder="At least 8 characters" minLength={8} />
                <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                  {showPw ? '🙈' : '👁️'}
                </button>
              </div>
            </Field>
            <Field label="Confirm Password">
              <Input type="password" required value={resetConfirm}
                onChange={(e) => setResetConfirm(e.target.value)} placeholder="Re-enter password" minLength={8} />
            </Field>
            <Button type="submit" disabled={resetBusy || !resetPw || !resetConfirm} style={{ width: '100%', justifyContent: 'center' }}>
              {resetBusy ? 'Resetting…' : 'Reset Password'}
            </Button>
          </form>
        </Panel>
      </div>
    );
  }

  // ── Reset success ────────────────────────────────────────────────────
  if (resetDone) {
    return (
      <div className="auth-wrap">
        <div className="auth-theme"><ThemeToggle /></div>
        <Panel bodyClassName="panel-body" style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 32, margin: '0 0 12px' }}>✅</p>
          <h1 style={{ fontSize: 20, marginTop: 0 }}>Password Updated</h1>
          <p className="muted" style={{ marginBottom: 20 }}>Your password has been reset. You can now sign in.</p>
          <Button onClick={() => { setResetDone(false); window.history.replaceState(null, '', '/login'); }}
            style={{ width: '100%', justifyContent: 'center' }}>
            Sign In
          </Button>
        </Panel>
      </div>
    );
  }

  // ── Normal login form ────────────────────────────────────────────────
  return (
    <div className="auth-wrap">
      <div className="auth-theme"><ThemeToggle /></div>
      <Panel bodyClassName="panel-body">
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <Logo size={40} showText={false} color="#fff" style={{ justifyContent: 'center' }} />
          <h1 style={{ fontSize: 20, marginTop: 12 }}>Sign in to Codessy</h1>
          <p className="muted mb-0">Cold email automation, powered by AI.</p>
        </div>
        {verified && (
          <div className="toast success" style={{ position: 'static', marginBottom: 14 }}>
            Your email has been verified! You can now sign in.
          </div>
        )}
        {error && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{error}</div>}
        <form onSubmit={submit}>
          <Field label="Email">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </Field>
          <Field label="Password">
            <div className="input-with-toggle">
              <Input type={showPw ? 'text' : 'password'} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" />
              <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                {showPw ? '🙈' : '👁️'}
              </button>
            </div>
          </Field>
          <Button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
            {busy ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
        <div className="flex" style={{ alignItems: 'center', gap: 10, margin: '14px 0' }}>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          <span className="muted" style={{ fontSize: 12 }}>or</span>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        </div>
        <Button variant="secondary" disabled={googleBusy} onClick={google} style={{ width: '100%', justifyContent: 'center' }}>
          {googleBusy ? 'Redirecting to Google…' : 'Continue with Google'}
        </Button>
        <div className="mt-16 flex" style={{ justifyContent: 'center', fontSize: 13 }}>
          <Link href="/forgot-password">Forgot password?</Link>
        </div>
        <div className="mt-8" style={{ textAlign: 'center', fontSize: 13 }}>
          New here? <Link href="/signup">Create an account</Link>
        </div>
      </Panel>
    </div>
  );
}
