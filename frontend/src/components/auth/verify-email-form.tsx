"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { useLanguage } from "@/contexts/language-context";

import { AuthPageShell } from "./auth-page-shell";
import styles from "./auth-shell.module.css";

export function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const { t } = useLanguage();
  const token = searchParams.get("token") ?? "";

  const [status, setStatus] = useState<"loading" | "success" | "error" | "missing">(
    token ? "loading" : "missing",
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const calledRef = useRef(false);

  useEffect(() => {
    if (!token || calledRef.current) return;
    calledRef.current = true;

    async function verify() {
      try {
        await apiFetch("/api/v1/auth/verify-email", {
          method: "POST",
          body: { token },
        });
        setStatus("success");
      } catch (err: unknown) {
        setErrorMsg(parseApiErrorMessage(err));
        setStatus("error");
      }
    }
    verify();
  }, [token]);

  if (status === "missing") {
    return (
      <AuthPageShell
        title={String(t("auth.verify.invalid"))}
        subtitle=""
      >
        <p className={styles.footer}>
          <Link href="/login">{String(t("auth.forgotPassword.backToLogin"))}</Link>
        </p>
      </AuthPageShell>
    );
  }

  if (status === "loading") {
    return (
      <AuthPageShell title={String(t("auth.verify.title"))}>
        <div className={styles.gateLoading} style={{ minHeight: "auto", paddingTop: "1rem" }}>
          <div className={styles.spinner} />
        </div>
      </AuthPageShell>
    );
  }

  if (status === "success") {
    return (
      <AuthPageShell
        title={String(t("auth.verify.title"))}
        subtitle={String(t("auth.verify.success"))}
      >
        <Link href="/login" className={styles.linkButton}>
          {String(t("auth.login.submit"))}
        </Link>
      </AuthPageShell>
    );
  }

  // error
  return (
    <AuthPageShell
      title={String(t("auth.verify.invalid"))}
      subtitle={String(t("auth.verify.invalid"))}
    >
      {errorMsg && (
        <p className={styles.alert} role="alert">
          {errorMsg}
        </p>
      )}
      <p className={styles.footer}>
        <Link href="/login">{String(t("auth.forgotPassword.backToLogin"))}</Link>
      </p>
    </AuthPageShell>
  );
}
