const KEY = 'pb-theme';

export function getTheme() {
  if (typeof window === 'undefined') return 'light';
  return localStorage.getItem(KEY) || 'light';
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === 'dark') root.setAttribute('data-theme', 'dark');
  else root.removeAttribute('data-theme');
}

export function toggleTheme() {
  const next = getTheme() === 'dark' ? 'light' : 'dark';
  localStorage.setItem(KEY, next);
  applyTheme(next);
  return next;
}

export function initTheme() {
  let theme = localStorage.getItem(KEY);
  if (!theme && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    theme = 'dark';
  }
  applyTheme(theme || 'light');
}