import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import Logo from '../components/Logo';

export default function ResetPassword() {
  const router = useRouter();
  const { reset_token: rawToken } = router.query;
  const token = rawToken;
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  if (!rawToken) {
    return (
      <Layout title="Reset Password">
        <div style={{ maxWidth: 440, margin: '60px auto', padding: '0 16px', textAlign: 'center' }}>
          <p style={{ fontSize: 16, color: '#dc2626' }}>Invalid or missing reset token.</p>
          <Link href="/forgot-password"><a style={{ color: '#ff9900', fontSize: 14 }}>Request a new reset link</a></Link>
        </div>
      </Layout>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await api('/api/auth/reset-password', {
        method: 'POST',
        body: { token: rawToken, new_password: password },
      });
      setSuccess(true);
    } catch (e) {
      setError(e.message || 'Invalid or expired token');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Reset Password">
      <div style={{ maxWidth: 440, margin: '60px auto', padding: '0 16px' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Logo size={48} showText={false} />
          <h1 style={{ fontSize: 24, fontWeight: 700, marginTop: 16, marginBottom: 8 }}>Reset Password</h1>
          <p className="muted" style={{ fontSize: 14 }}>Enter your new password below.</p>
        </div>

        {success ? (
          <div className="panel" style={{ padding: 32, textAlign: 'center' }}>
            <p style={{ fontSize: 32, margin: '0 0 12px' }}>✅</p>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Password Updated</h2>
            <p style={{ fontSize: 14, color: '#666', marginBottom: 20 }}>
              Your password has been reset. You can now sign in with your new password.
            </p>
            <Link href="/login">
              <a style={{
                display: 'inline-block', padding: '10px 24px', background: '#ff9900', color: 'white',
                borderRadius: 8, fontSize: 14, fontWeight: 600, textDecoration: 'none',
              }}>
                Sign In
              </a>
            </Link>
          </div>
        ) : (
          <div className="panel" style={{ padding: 32 }}>
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>New Password</label>
                <input
                  type="password"
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoFocus
                  minLength={8}
                  style={{
                    width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 6,
                    fontSize: 14, outline: 'none', boxSizing: 'border-box',
                  }}
                />
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Confirm Password</label>
                <input
                  type="password"
                  placeholder="Re-enter password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  minLength={8}
                  style={{
                    width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 6,
                    fontSize: 14, outline: 'none', boxSizing: 'border-box',
                  }}
                />
              </div>
              {error && <p style={{ color: '#dc2626', fontSize: 13, marginBottom: 12 }}>{error}</p>}
              <button
                type="submit"
                disabled={loading || !password || !confirm}
                style={{
                  width: '100%', padding: '12px', background: '#ff9900', color: 'white',
                  border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 600,
                  cursor: loading ? 'wait' : 'pointer', opacity: loading || !password || !confirm ? 0.6 : 1,
                }}
              >
                {loading ? 'Resetting...' : 'Reset Password'}
              </button>
            </form>
            <p style={{ textAlign: 'center', marginTop: 16, fontSize: 13 }}>
              <Link href="/login"><a style={{ color: '#ff9900' }}>← Back to Login</a></Link>
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}
