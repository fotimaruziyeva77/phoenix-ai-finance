"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, type ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";
import { buildLoginRedirectUrl } from "@/lib/auth/route-redirect";

import { AuthSessionLoading } from "./auth-session-loading";

type Props = {
  children: ReactNode;
};

/**
 * Protects customer dashboard (and any subtree it wraps): after real session hydration,
 * anonymous users go to `/login?next=<current>`, including query string when present.
 */
export function AuthGate({ children }: Props) {
  const { user, hydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname() ?? "";
  const searchParams = useSearchParams();

  const returnPath = useMemo(() => {
    const q = searchParams.toString();
    return q ? `${pathname}?${q}` : pathname;
  }, [pathname, searchParams]);

  useEffect(() => {
    if (!hydrated) return;
    if (user) return;
    router.replace(buildLoginRedirectUrl(returnPath));
  }, [hydrated, user, router, returnPath]);

  if (!hydrated || !user) {
    return <AuthSessionLoading />;
  }

  return <>{children}</>;
}
