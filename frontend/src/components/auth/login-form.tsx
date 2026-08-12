"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/hooks/useAuth";
import { resolvePostAuthRedirect } from "@/lib/auth/route-redirect";
import type { AuthCredentials } from "@/types/auth";
import { useLanguage } from "@/contexts/language-context";

import { AuthPageShell } from "./auth-page-shell";
import styles from "./auth-shell.module.css";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2"/>
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2"/>
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      <line x1="1" y1="1" x2="23" y2="23" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, busy, hydrated } = useAuth();
  const { t } = useLanguage();

  const [values, setValues] = useState<AuthCredentials>({
    email: "",
    password: "",
  });
  const [validation, setValidation] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setApiError(null);
    if (!values.email.trim() || !values.password) {
      setValidation("Email and password are required.");
      return;
    }
    if (!EMAIL_RE.test(values.email.trim())) {
      setValidation("Enter a valid email address.");
      return;
    }
    setValidation(null);
    try {
      await login(values.email.trim(), values.password);
      router.replace(resolvePostAuthRedirect(searchParams.get("next")));
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Sign-in failed.");
    }
  }

  const submitting = busy || !hydrated;

  return (
    <AuthPageShell
      title={String(t("auth.login.title"))}
      subtitle={String(t("auth.login.subtitle"))}
    >
      <form onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="login-email">
            {String(t("auth.login.email"))}
          </label>
          <input
            id="login-email"
            name="email"
            type="email"
            autoComplete="email"
            className={styles.input}
            value={values.email}
            disabled={submitting}
            onChange={(e) =>
              setValues((v) => ({ ...v, email: e.target.value }))
            }
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="login-password">
            {String(t("auth.login.password"))}
          </label>
          <div className={styles.passwordWrap}>
            <input
              id="login-password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              className={styles.input}
              value={values.password}
              disabled={submitting}
              onChange={(e) =>
                setValues((v) => ({ ...v, password: e.target.value }))
              }
            />
            <button
              type="button"
              className={styles.passwordToggle}
              aria-label={showPassword ? String(t("auth.hidePassword")) : String(t("auth.showPassword"))}
              onClick={() => setShowPassword((s) => !s)}
              tabIndex={-1}
            >
              {showPassword ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </div>
        </div>
        {validation ? (
          <p className={styles.alert} role="alert">
            {validation}
          </p>
        ) : null}
        {apiError ? (
          <p className={styles.alert} role="alert">
            {apiError}
          </p>
        ) : null}
        <button type="submit" className={styles.primaryBtn} disabled={submitting}>
          {submitting ? String(t("auth.login.submitting")) : String(t("auth.login.submit"))}
        </button>
      </form>


      <p className={styles.footer}>
        <Link href="/forgot-password">{String(t("auth.login.forgotPassword"))}</Link>
      </p>
      <p className={styles.footer} style={{ marginTop: "0.5rem", paddingTop: 0, borderTop: "none" }}>
        {String(t("auth.login.noAccount"))} <Link href="/signup">{String(t("auth.login.createOne"))}</Link>
      </p>
    </AuthPageShell>
  );
}
