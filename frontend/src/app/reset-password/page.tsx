import { Suspense } from "react";
import type { Metadata } from "next";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { GuestGate } from "@/components/auth/guest-gate";

export const metadata: Metadata = {
  title: "Set new password",
};

// Alias route — the backend email template links to /auth/reset-password?token=xxx
// This path is kept as a fallback for direct links.
export default function ResetPasswordPage() {
  return (
    <GuestGate>
      <Suspense>
        <ResetPasswordForm />
      </Suspense>
    </GuestGate>
  );
}
