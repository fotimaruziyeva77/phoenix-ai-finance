"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { resetPassword } from "@/lib/api/auth";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { useLanguage } from "@/contexts/language-context";

import { AuthPageShell } from "./auth-page-shell";
import styles from "./auth-shell.module.css";

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

export function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useLanguage();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [validation, setValidation] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // If no token in URL, show invalid-link screen immediately
  const missingToken = !token;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setApiError(null);

    if (!password) {
      setValidation("New password is required.");
      return;
    }
    if (password.length < 8) {
      setValidation("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setValidation("Passwords do not match.");
      return;
    }
    setValidation(null);
    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
      // Redirect to login after a short delay
      setTimeout(() => router.replace("/login"), 2500);
    } catch (err: unknown) {
      setApiError(parseApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (missingToken) {
    return (
      <AuthPageShell
        title={String(t("auth.verify.invalid"))}
        subtitle=""
      >
        <Link href="/forgot-password" className={styles.linkButton}>
          {String(t("auth.forgotPassword.submit"))}
        </Link>
        <p className={styles.footer}>
          <Link href="/login">{String(t("auth.forgotPassword.backToLogin"))}</Link>
        </p>
      </AuthPageShell>
    );
  }

  if (done) {
    return (
      <AuthPageShell
        title={String(t("auth.resetPassword.title"))}
        subtitle={String(t("auth.resetPassword.success"))}
      >
        <p className={styles.footer} style={{ marginTop: 0, paddingTop: 0, borderTop: "none" }}>
          <Link href="/login">{String(t("auth.forgotPassword.backToLogin"))}</Link>
        </p>
      </AuthPageShell>
    );
  }

  return (
    <AuthPageShell
      title={String(t("auth.resetPassword.title"))}
      subtitle={String(t("auth.resetPassword.subtitle"))}
    >
      <form onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="reset-password">
            {String(t("auth.resetPassword.password"))}
          </label>
          <div className={styles.passwordWrap}>
            <input
              id="reset-password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              className={styles.input}
              value={password}
              disabled={loading}
              onChange={(e) => setPassword(e.target.value)}
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
          <label className={styles.label} htmlFor="reset-confirm">
            {String(t("auth.resetPassword.confirmPassword"))}
          </label>
          <div className={styles.passwordWrap}>
            <input
              id="reset-confirm"
              name="confirm"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              className={styles.input}
              value={confirm}
              disabled={loading}
              onChange={(e) => setConfirm(e.target.value)}
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

        {validation && (
          <p className={styles.alert} role="alert">
            {validation}
          </p>
        )}
        {apiError && (
          <p className={styles.alert} role="alert">
            {apiError}
          </p>
        )}

        <button type="submit" className={styles.primaryBtn} disabled={loading}>
          {loading ? String(t("auth.resetPassword.submitting")) : String(t("auth.resetPassword.submit"))}
        </button>
      </form>

      <p className={styles.footer}>
        <Link href="/login">{String(t("auth.forgotPassword.backToLogin"))}</Link>
      </p>
    </AuthPageShell>
  );
}
