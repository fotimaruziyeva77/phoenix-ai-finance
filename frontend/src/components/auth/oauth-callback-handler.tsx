"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";

import { AuthPageShell } from "./auth-page-shell";
import styles from "./auth-shell.module.css";

/**
 * Completes browser OAuth: backend redirects here with ``oauth_exchange_code`` or ``oauth_error``.
 */
export function OAuthCallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { completeOAuthExchange, hydrated } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(true);

  const oauthErrorQ = searchParams.get("oauth_error") ?? "";
  const oauthDetailQ = searchParams.get("oauth_error_detail") ?? "";
  const oauthCodeQ = searchParams.get("oauth_exchange_code") ?? "";

  useEffect(() => {
    if (!hydrated) return;

    if (oauthErrorQ) {
      setWorking(false);
      setError(
        oauthDetailQ
          ? `${humanizeOAuthError(oauthErrorQ)} (${oauthDetailQ})`
          : humanizeOAuthError(oauthErrorQ),
      );
      return;
    }

    if (!oauthCodeQ.trim()) {
      setWorking(false);
      setError("Missing OAuth exchange code. Start sign-in again from the login page.");
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        await completeOAuthExchange(oauthCodeQ.trim());
        if (!cancelled) router.replace("/dashboard");
      } catch (e) {
        if (!cancelled) {
          setWorking(false);
          setError(e instanceof Error ? e.message : "Could not complete sign-in.");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    hydrated,
    oauthErrorQ,
    oauthDetailQ,
    oauthCodeQ,
    completeOAuthExchange,
    router,
  ]);

  if (working) {
    return (
      <AuthPageShell
        title="Completing sign-in"
        subtitle="Hang tight—we are connecting your account."
      >
        <div className={styles.gateLoading} style={{ minHeight: "auto" }} suppressHydrationWarning>
          <div className={styles.spinner} suppressHydrationWarning />
          <p className={styles.gateText}>Finishing OAuth…</p>
        </div>
      </AuthPageShell>
    );
  }

  if (error) {
    return (
      <AuthPageShell title="Sign-in issue" subtitle="We could not finish connecting your account.">
        <p className={styles.alert} role="alert">
          {error}
        </p>
        <Link href="/login" className={styles.linkButton}>
          Back to sign in
        </Link>
      </AuthPageShell>
    );
  }

  return null;
}

function humanizeOAuthError(code: string): string {
  const map: Record<string, string> = {
    google_oauth_denied: "Google sign-in was cancelled.",
    google_oauth_invalid_state: "This sign-in link expired. Please try again.",
    google_oauth_missing_code: "Invalid OAuth response from Google.",
    google_token_exchange_failed:
      "Could not verify Google credentials. Check redirect URI in Google Cloud vs GOOGLE_OAUTH_REDIRECT_URI, client secret, and backend logs (google_token_exchange_http_error).",
    google_userinfo_failed: "Could not load your Google profile.",
    google_email_not_verified: "Your Google email must be verified.",
    google_oauth_link_conflict: "This email is already linked to another Google account.",
    github_oauth_denied: "GitHub sign-in was cancelled.",
    github_oauth_invalid_state: "This sign-in link expired. Please try again.",
    github_oauth_missing_code: "Invalid OAuth response from GitHub.",
    github_token_exchange_failed: "Could not verify GitHub credentials.",
    github_userinfo_failed: "Could not load your GitHub profile.",
    github_oauth_email_unavailable: "GitHub did not provide a verified email.",
    github_oauth_link_conflict: "This email is already linked to another GitHub account.",
    google_oauth_internal_error: "Server error during Google sign-in. Check backend logs.",
    github_oauth_internal_error: "Server error during GitHub sign-in. Check backend logs.",
    inactive_user: "This account is disabled.",
  };
  return map[code] ?? `Sign-in failed (${code}).`;
}
