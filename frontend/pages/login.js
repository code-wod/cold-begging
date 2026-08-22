import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import { api } from '../lib/api';
import { Button, Field, Input, Panel } from '../components/ui';
import ThemeToggle from '../components/ThemeToggle';

export default function Login() {
  const { login, finishGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [verified, setVerified] = useState(false);

  useEffect(() => {
    // Check for verification success after email click
    const verifiedParam = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('verified');
    if (verifiedParam === '1') {
      setVerified(true);
      window.history.replaceState(null, '', '/login');
    }

    // Handle Google OAuth callback via fragment token
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

  return (
    <div className="auth-wrap">
      <div className="auth-theme"><ThemeToggle /></div>
      <Panel bodyClassName="panel-body">
        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <div style={{ fontSize: 26 }}>✉️</div>
          <h1 style={{ fontSize: 20 }}>Sign in to PulseBoard</h1>
          <p className="muted mb-0">Cold email automation, powered by AI.</p>
        </div>
        {verified && (
          <div className="toast success" style={{ position: 'static', marginBottom: 14 }}>
            🎉 Your email has been verified! You can now sign in.
          </div>
        )}
        {error && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{error}</div>}
        <form onSubmit={submit}>
          <Field label="Email">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </Field>
          <Field label="Password">
            <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
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
          <Link href="/forgot">Forgot password?</Link>
        </div>
        <div className="mt-8" style={{ textAlign: 'center', fontSize: 13 }}>
          New here? <Link href="/signup">Create an account</Link>
        </div>
      </Panel>
    </div>
  );
}
