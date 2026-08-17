import { useState } from 'react';
import Link from 'next/link';
import { api } from '../lib/api';
import { Button, Field, Input, Panel } from '../components/ui';

export default function Forgot() {
  const [email, setEmail] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api('/api/auth/forgot-password', { method: 'POST', body: { email } });
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <Panel>
        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <h1 style={{ fontSize: 20 }}>Reset your password</h1>
          <p className="muted mb-0">We'll generate a reset token for your account.</p>
        </div>
        {done ? (
          <div className="toast success" style={{ position: 'static' }}>
            If an account exists for {email}, a reset token has been generated. In this local build the token is
            printed to the server log. Use it on the reset page.
          </div>
        ) : (
          <>
            {error && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{error}</div>}
            <form onSubmit={submit}>
              <Field label="Email">
                <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
              </Field>
              <Button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
                {busy ? 'Sending…' : 'Send reset link'}
              </Button>
            </form>
          </>
        )}
        <div className="mt-16" style={{ textAlign: 'center', fontSize: 13 }}>
          <Link href="/login">Back to sign in</Link>
        </div>
      </Panel>
    </div>
  );
}