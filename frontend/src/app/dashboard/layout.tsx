import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";

import { AuthGate } from "@/components/auth/auth-gate";
import { AuthSessionLoading } from "@/components/auth/auth-session-loading";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<AuthSessionLoading />}>
      <AuthGate>
        <DashboardShell>{children}</DashboardShell>
      </AuthGate>
    </Suspense>
  );
}
