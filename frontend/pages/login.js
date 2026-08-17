import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import { Button, Field, Input, Panel } from '../components/ui';

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

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

  return (
    <div className="auth-wrap">
      <Panel bodyClassName="panel-body">
        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <div style={{ fontSize: 26 }}>✉️</div>
          <h1 style={{ fontSize: 20 }}>Sign in to PulseBoard</h1>
          <p className="muted mb-0">Cold email automation, powered by AI.</p>
        </div>
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