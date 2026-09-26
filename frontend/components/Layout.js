import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import ChatWidget from './ChatWidget';
import ThemeToggle from './ThemeToggle';
import { Icons, Spinner } from './ui';

const NAV = [
  { section: 'Overview' },
  { href: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { section: 'Job Hunting' },
  { href: '/jobs', label: 'Jobs', icon: 'search' },
  { href: '/applications', label: 'Applications', icon: 'send' },
  { href: '/job-portals', label: 'Job Portals', icon: 'link' },
  { href: '/agent', label: 'Agent Control', icon: 'play' },
  { href: '/resumes', label: 'Resumes', icon: 'profile' },
  { href: '/job-preferences', label: 'Job Preferences', icon: 'settings' },
  { section: 'Job Autofill' },
  { href: '/job-applications', label: 'Applications', icon: 'send' },
  { href: '/job-applications/iframe-fill', label: 'Fill Application', icon: 'play' },
  { href: '/job-applications/auto-fill', label: 'Auto-Fill (Background)', icon: 'play' },
  { href: '/job-applications/history', label: 'History', icon: 'history' },
  { href: '/job-profile', label: 'Job Profile', icon: 'profile' },
  { section: 'Extension' },
  { href: '/extension/download', label: 'Download', icon: 'link' },
  { href: '/extension/applications', label: 'Extension Apps', icon: 'send' },
  { section: 'Automation' },
  { href: '/campaigns', label: 'Campaigns', icon: 'campaigns' },
  { href: '/recipients', label: 'Recipients', icon: 'recipients' },
  { href: '/recipient-catalog', label: 'Recipient Catalog', icon: 'recipients' },
  { href: '/ai-agents', label: 'AI Agents', icon: 'agents' },
  { href: '/email-accounts', label: 'Email Accounts', icon: 'email' },
  { href: '/history', label: 'History', icon: 'history' },
  { href: '/analytics', label: 'Analytics', icon: 'analytics' },
  { section: 'Account' },
  { href: '/settings', label: 'Settings', icon: 'settings' },
  { href: '/billing', label: 'Billing', icon: 'billing' },
  { href: '/profile', label: 'Profile', icon: 'profile' },
];

const ADMIN_NAV = [{ href: '/admin', label: 'Admin', icon: 'settings' }];

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
          <svg viewBox="0 0 120 120" style={{ height: 28, flexShrink: 0 }} role="img" aria-label="Codessy">
            <defs>
              <linearGradient id="sb-blue" x1="22" y1="0" x2="58" y2="36" gradientUnits="userSpaceOnUse">
                <stop stop-color="#35A7FF" /><stop offset="1" stop-color="#2875F0" />
              </linearGradient>
              <linearGradient id="sb-purple" x1="64" y1="0" x2="100" y2="36" gradientUnits="userSpaceOnUse">
                <stop stop-color="#9B5CFF" /><stop offset="1" stop-color="#7340E8" />
              </linearGradient>
              <linearGradient id="sb-green" x1="22" y1="50" x2="58" y2="76" gradientUnits="userSpaceOnUse">
                <stop stop-color="#22D3A6" /><stop offset="1" stop-color="#10B981" />
              </linearGradient>
              <linearGradient id="sb-coral" x1="64" y1="50" x2="100" y2="76" gradientUnits="userSpaceOnUse">
                <stop stop-color="#FF9A55" /><stop offset="1" stop-color="#F45F72" />
              </linearGradient>
            </defs>
            <rect width="120" height="120" rx="28" fill="#070B1F"/>
            <g transform="translate(-1 22)">
              <path d="M22 18C22 8.059 30.059 0 40 0h18v18c0 9.941-8.059 18-18 18H22V18Z" fill="url(#sb-blue)" />
              <circle cx="82" cy="18" r="18" fill="url(#sb-purple)" />
              <path d="M22 40h18c9.941 0 18 8.059 18 18v18H40c-9.941 0-18-8.059-18-18V40Z" fill="url(#sb-green)" />
              <path d="M64 40h18c9.941 0 18 8.059 18 18v18H82c-9.941 0-18-8.059-18-18V40Z" fill="url(#sb-coral)" />
            </g>
          </svg>
          <span className="brand-text">Codessy</span>
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
          {user.is_admin &&
            ADMIN_NAV.map((item) => (
              <Link key={item.href} href={item.href}
                className={`sidebar-link ${router.pathname === item.href ? 'active' : ''}`}>
                {Icons[item.icon]}
                <span>{item.label}</span>
              </Link>
            ))}
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
            <ThemeToggle />
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