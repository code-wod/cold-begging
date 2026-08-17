import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { api } from '../lib/api';
import { Button, Field, Input, Panel } from '../components/ui';

export default function Reset() {
  const router = useRouter();
  const token = router.query.token || '';
  const [password, setPassword] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api('/api/auth/reset-password', { method: 'POST', body: { token, password } });
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
          <h1 style={{ fontSize: 20 }}>Set a new password</h1>
        </div>
        {done ? (
          <div>
            <div className="toast success" style={{ position: 'static', marginBottom: 14 }}>Password updated.</div>
            <Link href="/login" className="btn" style={{ justifyContent: 'center', width: '100%' }}>Sign in</Link>
          </div>
        ) : (
          <>
            {error && <div className="toast error" style={{ position: 'static', marginBottom: 14 }}>{error}</div>}
            <form onSubmit={submit}>
              <Field label="Reset token" help="Paste the token from the reset email / server log.">
                <Input required value={token} onChange={(e) => (router.query.token = e.target.value)} placeholder="reset-token" />
              </Field>
              <Field label="New password" help="At least 8 characters.">
                <Input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
              </Field>
              <Button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
                {busy ? 'Resetting…' : 'Reset password'}
              </Button>
            </form>
          </>
        )}
      </Panel>
    </div>
  );
}