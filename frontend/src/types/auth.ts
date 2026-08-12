/** Shape for login / signup forms (no prefilled values in UI). */
export type AuthCredentials = {
  email: string;
  password: string;
};

export type SignupFields = AuthCredentials & {
  confirmPassword: string;
  fullName: string;
};

export type AuthUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  /** False for OAuth-only accounts. May be undefined on bootstrap (older sessions). */
  has_password?: boolean;
  created_at: string;
  updated_at: string;
};

/**
 * ``GET /api/v1/auth/me`` — backend ``MeResponse`` (user + reserved verification/plan fields).
 */
export type MeUser = AuthUser & {
  has_password: boolean;
  email_verified_at: string | null;
  plan_key: string | null;
};

/** ``GET /api/v1/auth/bootstrap`` — backend ``AuthBootstrapResponse``. */
export type AuthBootstrap = {
  authenticated: boolean;
  auth_transport: "bearer" | "cookie" | "none";
  user: AuthUser | null;
  csrf_token: string | null;
};

/**
 * Backend ``AuthSessionResponse`` (register, login, OAuth exchange).
 * ``auth_transport`` is always set by the API (bearer vs cookie mode).
 */
export type AuthSession = {
  auth_transport: "bearer" | "cookie";
  user: AuthUser;
  access_token: string | null;
  refresh_token: string | null;
  token_type: "Bearer";
  expires_in: number;
  csrf_token?: string | null;
};

/** ``POST /api/v1/auth/refresh`` — backend ``TokenResponse``. */
export type TokenPairResponse = {
  auth_transport: "bearer" | "cookie";
  access_token: string | null;
  refresh_token: string | null;
  token_type: "Bearer";
  expires_in: number;
  csrf_token?: string | null;
};

/** Persisted client session (bearer mode; tokens + user snapshot). */
export type StoredAuthSession = {
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
};
