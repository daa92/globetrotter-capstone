/**
 * src/context/AuthContext.jsx
 *
 * Holds the current user + access token in React state (never localStorage
 * — see api/client.js for why), and re-establishes a session on page load
 * via a silent POST /auth/refresh (works because the httpOnly refresh
 * cookie, if any, is sent automatically by the browser).
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadCurrentUser = useCallback(async (token) => {
    const me = await api.getMe(token);
    setUser(me);
    return me;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const { access_token } = await api.refreshToken();
        setAccessToken(access_token);
        await loadCurrentUser(access_token);
      } catch {
        // No valid refresh cookie — the visitor just isn't logged in. Not an error.
      } finally {
        setLoading(false);
      }
    })();
  }, [loadCurrentUser]);

  const applySession = useCallback(
    async (result) => {
      if (result.mfa_required) return result; // caller prompts for a code and retries
      setAccessToken(result.access_token);
      await loadCurrentUser(result.access_token);
      return result;
    },
    [loadCurrentUser]
  );

  const login = useCallback(
    async (username, password, mfaCode) => applySession(await api.login(username, password, mfaCode)),
    [applySession]
  );

  const loginWithGoogle = useCallback(
    async (idToken, mfaCode) => applySession(await api.loginGoogle(idToken, mfaCode)),
    [applySession]
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Even if the server call fails, clear local state — the user still
      // expects to be logged out on their end.
    }
    setAccessToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!accessToken) return null;
    return loadCurrentUser(accessToken);
  }, [accessToken, loadCurrentUser]);

  const value = {
    user,
    accessToken,
    loading,
    isAuthenticated: Boolean(accessToken && user),
    login,
    loginWithGoogle,
    logout,
    refreshUser,
    register: api.register,
    registerPhone: api.registerPhone,
    verifyAccount: api.verifyAccount,
    requestPasswordReset: api.requestPasswordReset,
    confirmPasswordReset: api.confirmPasswordReset,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
