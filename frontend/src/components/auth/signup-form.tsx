"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/hooks/useAuth";
import { resolvePostAuthRedirect } from "@/lib/auth/route-redirect";
import type { SignupFields } from "@/types/auth";
import { useLanguage } from "@/contexts/language-context";

import { AuthPageShell } from "./auth-page-shell";
import styles from "./auth-shell.module.css";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD = 8;

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

export function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register, busy, hydrated } = useAuth();
  const { t } = useLanguage();

  const [values, setValues] = useState<SignupFields>({
    email: "",
    password: "",
    confirmPassword: "",
    fullName: "",
  });
  const [validation, setValidation] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setApiError(null);
    if (
      !values.email.trim() ||
      !values.password ||
      !values.confirmPassword
    ) {
      setValidation("Email and both password fields are required.");
      return;
    }
    if (!EMAIL_RE.test(values.email.trim())) {
      setValidation("Enter a valid email address.");
      return;
    }
    if (values.password.length < MIN_PASSWORD) {
      setValidation(`Password must be at least ${MIN_PASSWORD} characters.`);
      return;
    }
    if (values.password !== values.confirmPassword) {
      setValidation("Passwords do not match.");
      return;
    }
    setValidation(null);
    try {
      await register(
        values.email.trim(),
        values.password,
        values.fullName.trim() || undefined,
      );
      router.replace(resolvePostAuthRedirect(searchParams.get("next")));
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Could not create account.");
    }
  }

  const submitting = busy || !hydrated;

  return (
    <AuthPageShell
      title={String(t("auth.signup.title"))}
      subtitle={String(t("auth.signup.subtitle"))}
    >
      <form onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="signup-name">
            {String(t("auth.signup.name"))} <span style={{ opacity: 0.6 }}>{String(t("auth.signup.nameOptional"))}</span>
          </label>
          <input
            id="signup-name"
            name="fullName"
            type="text"
            autoComplete="name"
            className={styles.input}
            value={values.fullName}
            disabled={submitting}
            onChange={(e) =>
              setValues((v) => ({ ...v, fullName: e.target.value }))
            }
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="signup-email">
            {String(t("auth.signup.email"))}
          </label>
          <input
            id="signup-email"
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
          <label className={styles.label} htmlFor="signup-password">
            {String(t("auth.signup.password"))}
          </label>
          <div className={styles.passwordWrap}>
            <input
              id="signup-password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
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
        <div className={styles.field}>
          <label className={styles.label} htmlFor="signup-confirm">
            {String(t("auth.signup.confirmPassword"))}
          </label>
          <div className={styles.passwordWrap}>
            <input
              id="signup-confirm"
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              className={styles.input}
              value={values.confirmPassword}
              disabled={submitting}
              onChange={(e) =>
                setValues((v) => ({ ...v, confirmPassword: e.target.value }))
              }
            />
            <button
              type="button"
              className={styles.passwordToggle}
              aria-label={showConfirmPassword ? String(t("auth.hidePassword")) : String(t("auth.showPassword"))}
              onClick={() => setShowConfirmPassword((s) => !s)}
              tabIndex={-1}
            >
              {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
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
          {submitting ? String(t("auth.signup.submitting")) : String(t("auth.signup.submit"))}
        </button>
      </form>


      <p className={styles.footer}>
        {String(t("auth.signup.haveAccount"))} <Link href="/login">{String(t("auth.signup.signIn"))}</Link>
      </p>
    </AuthPageShell>
  );
}
