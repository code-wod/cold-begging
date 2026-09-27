import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import ChatWidget from './ChatWidget';
import ThemeToggle from './ThemeToggle';
import Logo from './Logo';
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
  { section: 'Job Hunting' },
  { href: '/jobs', label: 'Jobs', icon: 'search' },
  { href: '/applications', label: 'Applications', icon: 'send' },
  { href: '/job-portals', label: 'Job Portals', icon: 'link' },
  { href: '/agent', label: 'Agent Control', icon: 'play' },
  { href: '/resumes', label: 'Resumes', icon: 'profile' },
  { href: '/resume-score', label: 'Resume Score', icon: 'analytics' },
  { href: '/job-preferences', label: 'Job Preferences', icon: 'settings' },
  { section: 'Account' },
  { href: '/settings', label: 'Settings', icon: 'settings' },
  { href: '/billing', label: 'Billing', icon: 'billing' },
  { href: '/profile', label: 'Profile', icon: 'profile' },
];

const ADMIN_NAV = [{ href: '/admin', label: 'Admin', icon: 'settings' }];

export default function Layout({ title, breadcrumb, actions, children }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const navRef = useRef(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!navRef.current) return;
    const active = navRef.current.querySelector('.sidebar-link.active');
    if (active) active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [router.pathname]);

  useEffect(() => { setSidebarOpen(false); }, [router.pathname]);

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

  const renderNav = () => (
    <>
      {NAV.map((item) =>
        item.section ? (
          <div key={item.section} className="sidebar-section">{item.section}</div>
        ) : (
          <Link key={item.href} href={item.href}
            className={`sidebar-link ${router.pathname === item.href || router.pathname.startsWith(item.href + '/') ? 'active' : ''}`}>
            {Icons[item.icon]}
            <span>{item.label}</span>
          </Link>
        )
      )}
      {user.is_admin && ADMIN_NAV.map((item) => (
        <Link key={item.href} href={item.href}
          className={`sidebar-link ${router.pathname === item.href ? 'active' : ''}`}>
          {Icons[item.icon]}
          <span>{item.label}</span>
        </Link>
      ))}
    </>
  );

  return (
    <div className="app-shell">
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <Logo size={28} showText={false} color="#fff" />
          <span className="brand-text">Codessy</span>
        </div>
        <nav className="sidebar-nav" ref={navRef}>
          {renderNav()}
        </nav>
        <div className="sidebar-footer">
          {user.plan === 'pro' ? (
            <div className="sidebar-plan-badge sidebar-plan-pro">&#9733; Pro Plan</div>
          ) : (
            <Link href="/billing" className="sidebar-plan-badge sidebar-plan-free">
              Free Plan &middot; Upgrade
            </Link>
          )}
          <button className="btn ghost sm" style={{ color: '#cbd5e1', width: '100%' }} onClick={logout}>
            {Icons.logout} Sign out
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle sidebar">
              <span /><span /><span />
            </button>
            <div>
              {breadcrumb && <div className="breadcrumb">{breadcrumb}</div>}
              {title && <div style={{ fontWeight: 600, fontSize: 15 }}>{title}</div>}
            </div>
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
