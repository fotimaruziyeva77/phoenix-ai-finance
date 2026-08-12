"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  exchangeOAuthCode,
  fetchAuthBootstrap,
  fetchCurrentUser,
  loginWithEmail,
  registerAccount,
} from "@/lib/api/auth";
import { apiFetch, apiFetchWithAuth } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { authCookieMode } from "@/lib/auth/cookie-mode";
import { setCsrfToken } from "@/lib/auth/csrf";
import { clearStoredSession, readStoredSession, writeStoredSession } from "@/lib/auth/storage";
import type { AuthSession, AuthUser, StoredAuthSession } from "@/types/auth";

type AuthContextValue = {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  /** false until client has read localStorage */
  hydrated: boolean;
  /**
   * True when authenticated API calls may proceed (Bearer token or cookie session + user).
   */
  canUseAuthenticatedApi: boolean;
  /** In-flight login/register/oauth */
  busy: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  completeOAuthExchange: (exchangeCode: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Pitch-demo credentials — let the jury into the dashboard with no backend.
 *
 * Active only in dev builds or when NEXT_PUBLIC_DEMO_LOGIN=1 is set explicitly;
 * a production build without that flag ignores this pair entirely. The session
 * it creates is a plain client-side stub: authenticated API calls will still
 * fail, but every client-computed page (the finance tools) works.
 */
const DEMO_EMAIL = "demo@phoenix.uz";
const DEMO_PASSWORD = "Phoenix2026!";

function demoLoginEnabled(): boolean {
  return (
    process.env.NODE_ENV !== "production" ||
    process.env.NEXT_PUBLIC_DEMO_LOGIN === "1"
  );
}

function buildDemoSession(email = DEMO_EMAIL, fullName = "Phoenix Demo"): AuthSession {
  const now = new Date().toISOString();
  return {
    auth_transport: "bearer",
    access_token: "demo-access-token",
    refresh_token: "demo-refresh-token",
    token_type: "Bearer",
    expires_in: 86_400,
    user: {
      id: `demo-${email}`,
      email,
      full_name: fullName,
      role: "user",
      is_active: true,
      is_verified: true,
      has_password: true,
      created_at: now,
      updated_at: now,
    },
  };
}

/**
 * Local account store for demo mode: when the Python backend is unreachable,
 * registration falls back to this per-browser map so teammates can create and
 * reuse their own accounts. Plain localStorage, this browser only — a stub,
 * not authentication.
 */
const DEMO_USERS_KEY = "phoenix_demo_users_v1";

type DemoUserRecord = { password: string; fullName: string | null };

function readDemoUsers(): Record<string, DemoUserRecord> {
  try {
    const raw = window.localStorage.getItem(DEMO_USERS_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : null;
    return parsed && typeof parsed === "object" ? (parsed as Record<string, DemoUserRecord>) : {};
  } catch {
    return {};
  }
}

function saveDemoUser(email: string, record: DemoUserRecord): void {
  const users = readDemoUsers();
  users[email] = record;
  window.localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(users));
}

function sessionToStored(s: AuthSession): StoredAuthSession | null {
  if (!s.access_token || !s.refresh_token) {
    return null;
  }
  return {
    accessToken: s.access_token,
    refreshToken: s.refresh_token,
    user: s.user,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (authCookieMode()) {
      let cancelled = false;
      void (async () => {
        try {
          const b = await fetchAuthBootstrap();
          if (cancelled) return;
          if (b.authenticated && b.user) {
            setUser(b.user);
            setCsrfToken(b.csrf_token ?? null);
          }
        } catch {
          /* offline / CORS — stay logged out */
        } finally {
          if (!cancelled) setHydrated(true);
        }
      })();
      return () => {
        cancelled = true;
      };
    }

    const stored = readStoredSession();
    if (stored) {
      setAccessToken(stored.accessToken);
      setRefreshToken(stored.refreshToken);
      setUser(stored.user);
    }
    setHydrated(true);
  }, []);

  const applySession = useCallback((session: AuthSession) => {
    setCsrfToken(session.csrf_token ?? null);
    if (authCookieMode()) {
      clearStoredSession();
      setUser(session.user);
      setAccessToken(session.access_token);
      setRefreshToken(session.refresh_token);
      return;
    }
    const stored = sessionToStored(session);
    if (stored) {
      writeStoredSession(stored);
      setAccessToken(stored.accessToken);
      setRefreshToken(stored.refreshToken);
    } else {
      setAccessToken(session.access_token);
      setRefreshToken(session.refresh_token);
    }
    setUser(session.user);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setBusy(true);
      const normalized = email.trim().toLowerCase();
      try {
        if (demoLoginEnabled() && normalized === DEMO_EMAIL && password === DEMO_PASSWORD) {
          applySession(buildDemoSession());
          return;
        }
        try {
          const session = await loginWithEmail({ email, password });
          applySession(session);
        } catch (apiError) {
          // Backend down/unreachable: accept accounts registered locally in
          // demo mode so the team can keep using their own logins.
          const local = demoLoginEnabled() ? readDemoUsers()[normalized] : undefined;
          if (local && local.password === password) {
            applySession(buildDemoSession(normalized, local.fullName ?? normalized));
            return;
          }
          throw apiError;
        }
      } catch (e) {
        throw new Error(parseApiErrorMessage(e));
      } finally {
        setBusy(false);
      }
    },
    [applySession],
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      setBusy(true);
      const normalized = email.trim().toLowerCase();
      const name = fullName?.trim() || null;
      try {
        try {
          const session = await registerAccount({
            email,
            password,
            full_name: name,
          });
          applySession(session);
        } catch (apiError) {
          // Backend down/unreachable in demo mode: create the account locally
          // (this browser only) so sign-up never blocks the pitch demo.
          if (!demoLoginEnabled()) throw apiError;
          saveDemoUser(normalized, { password, fullName: name });
          applySession(buildDemoSession(normalized, name ?? normalized));
        }
      } catch (e) {
        throw new Error(parseApiErrorMessage(e));
      } finally {
        setBusy(false);
      }
    },
    [applySession],
  );

  const completeOAuthExchange = useCallback(
    async (exchangeCode: string) => {
      setBusy(true);
      try {
        const session = await exchangeOAuthCode(exchangeCode);
        applySession(session);
      } catch (e) {
        throw new Error(parseApiErrorMessage(e));
      } finally {
        setBusy(false);
      }
    },
    [applySession],
  );

  const logout = useCallback(() => {
    const t = accessToken;
    clearStoredSession();
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    setCsrfToken(null);
    if (authCookieMode()) {
      void apiFetch("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    } else if (t) {
      void apiFetchWithAuth("/api/v1/auth/logout", t, { method: "POST" }).catch(() => undefined);
    }
    /* Full navigation avoids a race with ``AuthGate`` on /dashboard (no ?next= churn). */
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  }, [accessToken]);

  const refreshProfile = useCallback(async () => {
    if (!authCookieMode() && !accessToken) return;
    try {
      const me = await fetchCurrentUser(authCookieMode() ? null : accessToken);
      setUser(me);
      if (!authCookieMode()) {
        const stored = readStoredSession();
        if (stored) {
          writeStoredSession({
            ...stored,
            user: me,
          });
        }
      }
    } catch {
      /* keep stale user if /me fails */
    }
  }, [accessToken]);

  const canUseAuthenticatedApi = Boolean(
    hydrated && user && (accessToken || authCookieMode()),
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      refreshToken,
      hydrated,
      canUseAuthenticatedApi,
      busy,
      login,
      register,
      completeOAuthExchange,
      logout,
      refreshProfile,
    }),
    [
      user,
      accessToken,
      refreshToken,
      hydrated,
      canUseAuthenticatedApi,
      busy,
      login,
      register,
      completeOAuthExchange,
      logout,
      refreshProfile,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return ctx;
}
