import { useEffect, useState } from 'react';
import { applyTheme, getTheme, toggleTheme } from '../lib/theme';

const Sun = (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4l1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4l1.4-1.4" />
  </svg>
);

const Moon = (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" />
  </svg>
);

export default function ThemeToggle({ variant = '' }) {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    setTheme(getTheme());
  }, []);

  const onClick = () => setTheme(toggleTheme());
  return (
    <button
      className={`theme-toggle ${variant}`}
      onClick={onClick}
      title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      aria-label="Toggle color theme"
    >
      {theme === 'dark' ? Sun : Moon}
    </button>
  );
}