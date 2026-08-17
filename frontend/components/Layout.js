import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import ChatWidget from './ChatWidget';
import { Icons, Spinner } from './ui';

const NAV = [
  { section: 'Overview' },
  { href: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { section: 'Automation' },
  { href: '/campaigns', label: 'Campaigns', icon: 'campaigns' },
  { href: '/recipients', label: 'Recipients', icon: 'recipients' },
  { href: '/ai-agents', label: 'AI Agents', icon: 'agents' },
  { href: '/email-accounts', label: 'Email Accounts', icon: 'email' },
  { href: '/history', label: 'History', icon: 'history' },
  { href: '/analytics', label: 'Analytics', icon: 'analytics' },
  { section: 'Account' },
  { href: '/settings', label: 'Settings', icon: 'settings' },
  { href: '/billing', label: 'Billing', icon: 'billing' },
  { href: '/profile', label: 'Profile', icon: 'profile' },
];

export default function Layout({ title, breadcrumb, actions, children }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  if (loading) {
    return (
      <div className="auth-wrap">
        <Spinner />
      </div>
    );
  }
  if (!user) {
    if (typeof window !== 'undefined') router.replace('/login');
    return null;
  }

  const initials = (user.full_name || user.email).slice(0, 2).toUpperCase();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="logo">✉️</span>
          <span className="brand-text">PulseBoard</span>
        </div>
        <nav className="sidebar-nav">
          {NAV.map((item) =>
            item.section ? (
              <div key={item.section} className="sidebar-section">
                {item.section}
              </div>
            ) : (
              <Link key={item.href} href={item.href}
                className={`sidebar-link ${router.pathname === item.href || router.pathname.startsWith(item.href + '/') ? 'active' : ''}`}>
                {Icons[item.icon]}
                <span>{item.label}</span>
              </Link>
            )
          )}
        </nav>
        <div className="sidebar-footer">
          <span className="plan-pill">
            {user.plan === 'pro' ? '⭐ Pro Plan' : 'Free Plan'} ·{' '}
            <Link href="/billing" style={{ color: '#93c5fd' }}>Upgrade</Link>
          </span>
          <button className="btn ghost sm" style={{ color: '#cbd5e1', width: '100%' }} onClick={logout}>
            {Icons.logout} Sign out
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div>
            {breadcrumb && <div className="breadcrumb">{breadcrumb}</div>}
            {title && <div style={{ fontWeight: 600, fontSize: 15 }}>{title}</div>}
          </div>
          <div className="flex">
            <Link href="/campaigns/new" className="btn sm">
              {Icons.plus} New Campaign
            </Link>
            <span className="avatar" title={user.email}>{initials}</span>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
      <ChatWidget />
    </div>
  );
}