import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";

import { AuthGate } from "@/components/auth/auth-gate";
import { AuthSessionLoading } from "@/components/auth/auth-session-loading";
import { SuperadminGate } from "@/components/superadmin/superadmin-gate";
import { SuperadminShell } from "@/components/superadmin/superadmin-shell";

export const metadata: Metadata = {
  title: "Platform admin",
};

export default function SuperadminLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<AuthSessionLoading />}>
      <AuthGate>
        <SuperadminGate>
          <SuperadminShell>{children}</SuperadminShell>
        </SuperadminGate>
      </AuthGate>
    </Suspense>
  );
}
