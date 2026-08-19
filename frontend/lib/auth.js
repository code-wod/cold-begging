import { createContext, useContext, useEffect, useState } from 'react';
import { api, clearToken, getToken, setToken } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api('/api/auth/me')
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const d = await api('/api/auth/login', { method: 'POST', body: { email, password } });
    setToken(d.access_token);
    setUser(d.user);
    return d.user;
  };

  const signup = async (email, password, fullName) => {
    const d = await api('/api/auth/signup', {
      method: 'POST',
      body: { email, password, full_name: fullName },
    });
    setToken(d.access_token);
    setUser(d.user);
    return d.user;
  };

  const finishGoogle = async (token) => {
    setToken(token);
    const user = await api('/api/auth/me');
    setUser(user);
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