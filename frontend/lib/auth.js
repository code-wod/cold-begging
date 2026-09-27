import { createContext, useContext, useEffect, useState } from 'react';
import { api, clearToken, getToken, setToken } from './api';

const AuthContext = createContext(null);

function detectTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api('/api/auth/me')
      .then((u) => {
        setUser(u);
        // Auto-detect and save timezone if not set
        const browserTz = detectTimezone();
        if (u.timezone !== browserTz) {
          api('/api/auth/detect-timezone', { method: 'POST', body: { timezone: browserTz } })
            .then((res) => setUser((prev) => prev ? { ...prev, timezone: res.timezone } : prev))
            .catch(() => {});
        }
      })
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const d = await api('/api/auth/login', { method: 'POST', body: { email, password } });
    setToken(d.access_token);
    setUser(d.user);
    // Detect timezone after login
    const browserTz = detectTimezone();
    api('/api/auth/detect-timezone', { method: 'POST', body: { timezone: browserTz } })
      .then((res) => setUser((prev) => prev ? { ...prev, timezone: res.timezone } : prev))
      .catch(() => {});
    return d.user;
  };

  const signup = async (email, password, fullName, phone) => {
    const d = await api('/api/auth/signup', {
      method: 'POST',
      body: { email, password, full_name: fullName, phone },
    });
    setToken(d.access_token);
    setUser(d.user);
    // Detect timezone after signup
    const browserTz = detectTimezone();
    api('/api/auth/detect-timezone', { method: 'POST', body: { timezone: browserTz } })
      .then((res) => setUser((prev) => prev ? { ...prev, timezone: res.timezone } : prev))
      .catch(() => {});
    return d.user;
  };

  const finishGoogle = async (token) => {
    setToken(token);
    const user = await api('/api/auth/me');
    setUser(user);
    // Detect timezone after Google login
    const browserTz = detectTimezone();
    api('/api/auth/detect-timezone', { method: 'POST', body: { timezone: browserTz } })
      .then((res) => setUser((prev) => prev ? { ...prev, timezone: res.timezone } : prev))
      .catch(() => {});
    return user;
  };

  const logout = () => {
    clearToken();
    setUser(null);
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, finishGoogle, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
