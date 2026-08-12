"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";

/**
 * Redirect already-authenticated users away from public pages.
 * Returns true when safe to render public content (hydrated + not authed).
 */
export function useRedirectIfAuthed(destination = "/dashboard"): boolean {
  const { hydrated, canUseAuthenticatedApi } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!hydrated) return;
    if (canUseAuthenticatedApi) {
      router.replace(destination);
    }
  }, [hydrated, canUseAuthenticatedApi, destination, router]);

  return hydrated && !canUseAuthenticatedApi;
}
