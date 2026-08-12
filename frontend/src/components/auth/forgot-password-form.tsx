"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { forgotPassword } from "@/lib/api/auth";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { useLanguage } from "@/contexts/language-context";

import { AuthPageShell } from "./auth-page-shell";
import styles from "./auth-shell.module.css";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ForgotPasswordForm() {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [validation, setValidation] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setApiError(null);
    const trimmed = email.trim();
    if (!trimmed) {
      setValidation("Email address is required.");
      return;
    }
    if (!EMAIL_RE.test(trimmed)) {
      setValidation("Enter a valid email address.");
      return;
    }
    setValidation(null);
    setLoading(true);
    try {
      await forgotPassword(trimmed);
      setSubmitted(true);
    } catch (err: unknown) {
      // API always returns 204 regardless of whether email exists —
      // we still handle unexpected errors (network, 503, etc.)
      setApiError(parseApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <AuthPageShell
        title={String(t("auth.forgotPassword.title"))}
        subtitle={String(t("auth.forgotPassword.success"))}
      >
        <p className={styles.footer} style={{ marginTop: 0, paddingTop: 0, borderTop: "none" }}>
          <Link href="/login">{String(t("auth.forgotPassword.backToLogin"))}</Link>
        </p>
      </AuthPageShell>
    );
  }

  return (
    <AuthPageShell
      title={String(t("auth.forgotPassword.title"))}
      subtitle={String(t("auth.forgotPassword.subtitle"))}
    >
      <form onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="forgot-email">
            {String(t("auth.forgotPassword.email"))}
          </label>
          <input
            id="forgot-email"
            name="email"
            type="email"
            autoComplete="email"
            className={styles.input}
            value={email}
            disabled={loading}
            onChange={(e) => setEmail(e.target.value)}
          />
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
          {loading ? String(t("auth.forgotPassword.submitting")) : String(t("auth.forgotPassword.submit"))}
        </button>
      </form>

      <p className={styles.footer}>
        <Link href="/login">{String(t("auth.forgotPassword.backToLogin"))}</Link>
      </p>
    </AuthPageShell>
  );
}
