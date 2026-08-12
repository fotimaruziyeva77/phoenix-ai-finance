"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AuthSessionLoading } from "@/components/auth/auth-session-loading";
import { useAuth } from "@/hooks/useAuth";

const SUPERADMIN_ROLE = "superadmin";

type Props = {
  children: ReactNode;
};

/**
 * Keeps platform routes unreachable for customer admins (and any non-superadmin).
 * Must sit under ``AuthGate`` so ``user`` is always present when this renders children.
 */
export function SuperadminGate({ children }: Props) {
  const { user, hydrated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!hydrated) return;
    if (user && user.role !== SUPERADMIN_ROLE) {
      router.replace("/dashboard");
    }
  }, [hydrated, user, router]);

  if (!hydrated || !user) {
    return <AuthSessionLoading />;
  }

  if (user.role !== SUPERADMIN_ROLE) {
    return <AuthSessionLoading />;
  }

  return <>{children}</>;
}
