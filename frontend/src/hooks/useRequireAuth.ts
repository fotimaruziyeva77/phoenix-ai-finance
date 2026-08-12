"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import type { AuthUser } from "@/types/auth";

/**
 * Redirect unauthenticated visitors to /login.
 * Returns null while hydrating, AuthUser once confirmed.
 */
export function useRequireAuth(): AuthUser | null {
  const { user, hydrated, canUseAuthenticatedApi } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!hydrated) return;
    if (!canUseAuthenticatedApi) {
      const next =
        typeof window !== "undefined" ? window.location.pathname : "";
      const target =
        next && next !== "/"
          ? `/login?next=${encodeURIComponent(next)}`
          : "/login";
      router.replace(target);
    }
  }, [hydrated, canUseAuthenticatedApi, router]);

  if (!hydrated || !canUseAuthenticatedApi) return null;
  return user;
}
