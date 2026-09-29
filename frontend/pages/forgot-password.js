import { useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import Logo from '../components/Logo';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError('');
    try {
      await api('/api/auth/forgot-password', {
        method: 'POST',
        body: { email: email.trim() },
      });
      setSent(true);
    } catch (e) {
      // Show success even if user not found (don't leak existence)
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Forgot Password">
      <div style={{ maxWidth: 440, margin: '60px auto', padding: '0 16px' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Logo size={48} showText={false} />
          <h1 style={{ fontSize: 24, fontWeight: 700, marginTop: 16, marginBottom: 8 }}>Forgot Password</h1>
          <p className="muted" style={{ fontSize: 14 }}>
            Enter your email and we&apos;ll send you a reset link.
          </p>
        </div>

        {sent ? (
          <div className="panel" style={{ padding: 32, textAlign: 'center' }}>
            <p style={{ fontSize: 32, margin: '0 0 12px' }}>📧</p>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Check your email</h2>
            <p style={{ fontSize: 14, color: '#666', marginBottom: 20, lineHeight: 1.6 }}>
              If an account exists for <strong>{email}</strong>, we&apos;ve sent a password reset link.
              The link expires in 1 hour.
            </p>
            <Link href="/login">
              <a style={{
                display: 'inline-block', padding: '10px 24px', background: '#ff9900', color: 'white',
                borderRadius: 8, fontSize: 14, fontWeight: 600, textDecoration: 'none',
              }}>
                Back to Login
              </a>
            </Link>
          </div>
        ) : (
          <div className="panel" style={{ padding: 32 }}>
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Email address</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                  style={{
                    width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 6,
                    fontSize: 14, outline: 'none', boxSizing: 'border-box',
                  }}
                />
              </div>
              {error && <p style={{ color: '#dc2626', fontSize: 13, marginBottom: 12 }}>{error}</p>}
              <button
                type="submit"
                disabled={loading || !email.trim()}
                style={{
                  width: '100%', padding: '12px', background: '#ff9900', color: 'white',
                  border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 600,
                  cursor: loading ? 'wait' : 'pointer', opacity: loading || !email.trim() ? 0.6 : 1,
                }}
              >
                {loading ? 'Sending...' : 'Send Reset Link'}
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
