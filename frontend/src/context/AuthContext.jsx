import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const authRequestIdRef = useRef(0);

  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('agriscan_user');
      const token = localStorage.getItem('agriscan_token');
      return token && savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem('agriscan_token') || null;
    } catch {
      return null;
    }
  });

  const [loading, setLoading] = useState(true);

  // Secure logout: clears client state, invalidates in-flight requests, and notifies server
  const logout = useCallback(async () => {
    authRequestIdRef.current += 1;
    try {
      localStorage.removeItem('agriscan_token');
      localStorage.removeItem('agriscan_user');
    } catch (e) {
      console.warn('[AuthContext] LocalStorage removal error:', e);
    }
    setToken(null);
    setUser(null);
    setLoading(false);

    try {
      await api.post('/auth/logout').catch(() => null);
    } catch {
      // Fire-and-forget
    }
  }, []);

  // Verify active user session against the server
  const verifySession = useCallback(async () => {
    const currentRequestId = ++authRequestIdRef.current;
    const storedToken = localStorage.getItem('agriscan_token');

    if (!storedToken) {
      setUser(null);
      setToken(null);
      setLoading(false);
      return;
    }

    try {
      const res = await api.get('/auth/me');
      if (currentRequestId !== authRequestIdRef.current) return;

      if (res.data?.success && res.data?.user) {
        setUser(res.data.user);
        setToken(storedToken);
        localStorage.setItem('agriscan_user', JSON.stringify(res.data.user));
      } else {
        await logout();
      }
    } catch (err) {
      if (currentRequestId !== authRequestIdRef.current) return;

      // If server explicitly returned 401 Unauthorized or 403 Forbidden, session is revoked
      if (err.response?.status === 401 || err.response?.status === 403) {
        await logout();
      } else if (!err.response) {
        // True network error / server cold start: allow cached offline credentials
        const savedUser = localStorage.getItem('agriscan_user');
        if (savedUser) {
          try {
            setUser(JSON.parse(savedUser));
            setToken(storedToken);
          } catch {
            await logout();
          }
        } else {
          await logout();
        }
      } else {
        await logout();
      }
    } finally {
      if (currentRequestId === authRequestIdRef.current) {
        setLoading(false);
      }
    }
  }, [logout]);

  // Initial verification on mount
  useEffect(() => {
    verifySession();
  }, [verifySession]);

  // Global listeners for 401 events, multi-tab sync, and browser navigation (Back/Forward & bfcache)
  useEffect(() => {
    // 1. Backend 401 Unauthorized interceptor event
    const handleUnauthorized = () => {
      logout();
    };

    // 2. Multi-tab synchronization (logout in another tab clears this tab)
    const handleStorageChange = (e) => {
      if (e.key === 'agriscan_token' && !e.newValue) {
        logout();
      }
    };

    // 3. Browser Back / Forward navigation (popstate) & bfcache restoration (pageshow)
    const handleNavigation = (e) => {
      const storedToken = localStorage.getItem('agriscan_token');
      if (!storedToken) {
        // Token was removed; ensure state is cleanly wiped
        logout();
      } else if (e.persisted) {
        // Page was restored from Back-Forward Cache (bfcache): re-validate with server
        verifySession();
      }
    };

    window.addEventListener('agriscan:unauthorized', handleUnauthorized);
    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('popstate', handleNavigation);
    window.addEventListener('pageshow', handleNavigation);

    return () => {
      window.removeEventListener('agriscan:unauthorized', handleUnauthorized);
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('popstate', handleNavigation);
      window.removeEventListener('pageshow', handleNavigation);
    };
  }, [logout, verifySession]);

  const login = async (email, password) => {
    const currentRequestId = ++authRequestIdRef.current;
    try {
      const res = await api.post('/auth/login', { email, password });
      if (res.data?.success && res.data?.token) {
        if (currentRequestId !== authRequestIdRef.current) return { success: false, message: 'Session cancelled' };
        localStorage.setItem('agriscan_token', res.data.token);
        localStorage.setItem('agriscan_user', JSON.stringify(res.data.user));
        setToken(res.data.token);
        setUser(res.data.user);
        setLoading(false);
        return { success: true, user: res.data.user };
      }
      return {
        success: false,
        message: res.data?.message || 'Login failed',
      };
    } catch (err) {
      const message =
        err.response?.data?.message ||
        (!err.response
          ? 'Unable to connect to AgriScan server. Please ensure backend is running.'
          : 'Invalid email or password');
      return {
        success: false,
        message,
      };
    }
  };

  const register = async (userData) => {
    const currentRequestId = ++authRequestIdRef.current;
    try {
      const res = await api.post('/auth/register', userData);
      if (res.data?.success && res.data?.token) {
        if (currentRequestId !== authRequestIdRef.current) return { success: false, message: 'Session cancelled' };
        localStorage.setItem('agriscan_token', res.data.token);
        localStorage.setItem('agriscan_user', JSON.stringify(res.data.user));
        setToken(res.data.token);
        setUser(res.data.user);
        setLoading(false);
        return { success: true, user: res.data.user };
      }
      return {
        success: false,
        message: res.data?.message || 'Registration failed',
      };
    } catch (err) {
      const message =
        err.response?.data?.message ||
        (!err.response
          ? 'Unable to connect to AgriScan server. Please ensure backend is running.'
          : 'Registration failed');
      return {
        success: false,
        message,
      };
    }
  };

  const updateProfile = async (updates) => {
    try {
      const res = await api.put('/auth/profile', updates);
      if (res.data?.success) {
        setUser(res.data.user);
        localStorage.setItem('agriscan_user', JSON.stringify(res.data.user));
        return { success: true };
      }
      return { success: false, message: res.data?.message || 'Update failed' };
    } catch (err) {
      return { success: false, message: err.response?.data?.message || 'Update failed' };
    }
  };

  // Authenticated ONLY if React state has user AND token AND localStorage has token
  const hasStoredToken = typeof window !== 'undefined' && Boolean(localStorage.getItem('agriscan_token'));
  const isAuthenticated = Boolean(user && token && hasStoredToken);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        verifySession,
        updateProfile,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export default AuthContext;
