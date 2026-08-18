import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import { Button, Field, Input, Panel } from '../components/ui';
import ThemeToggle from '../components/ThemeToggle';

export default function Signup() {
  const { signup } = useAuth();
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await signup(email, password, name);
      router.push('/onboarding');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-theme"><ThemeToggle /></div>
      <Panel>
        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <div style={{ fontSize: 26 }}>✉️</div>
          <h1 style={{ fontSize: 20 }}>Create your free account</h1>
          <p className="muted mb-0">Connect your own Gmail. Use your own AI key. Start today.</p>
        </div>
        {error && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{error}</div>}
        <form onSubmit={submit}>
          <Field label="Full name">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ada Lovelace" />
          </Field>
          <Field label="Work email">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </Field>
          <Field label="Password" help="At least 8 characters.">
            <Input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </Field>
          <Button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
            {busy ? 'Creating account…' : 'Get Started Free'}
          </Button>
        </form>
        <div className="mt-16" style={{ textAlign: 'center', fontSize: 13 }}>
          Already have an account? <Link href="/login">Sign in</Link>
        </div>
      </Panel>
    </div>
  );
}