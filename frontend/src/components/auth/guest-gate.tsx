"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";
import { resolvePostAuthRedirect } from "@/lib/auth/route-redirect";

import { AuthSessionLoading } from "./auth-session-loading";

type Props = {
  children: ReactNode;
};

/**
 * For /login and /signup only: wait for real session hydration, then either
 * show the guest form or redirect authenticated users (respects `?next=`).
 */
export function GuestGate({ children }: Props) {
  const { user, hydrated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextParam = searchParams.get("next");

  useEffect(() => {
    if (!hydrated || !user) return;
    router.replace(resolvePostAuthRedirect(nextParam));
  }, [hydrated, user, router, nextParam]);

  if (!hydrated) {
    return <AuthSessionLoading />;
  }
  if (user) {
    return <AuthSessionLoading message="Redirecting…" />;
  }

  return <>{children}</>;
}
