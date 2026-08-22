const TOKEN_KEY = 'cold_email_token';

export const getToken = () =>
  typeof window !== 'undefined' ? window.localStorage.getItem(TOKEN_KEY) : null;
export const setToken = (t) => window.localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => window.localStorage.removeItem(TOKEN_KEY);
const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (body) headers['Content-Type'] = 'application/json';

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: form ? form : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      detail = j.detail || j.message || detail;
    } catch {
      /* ignore */
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const AUTH_URL = BASE;
