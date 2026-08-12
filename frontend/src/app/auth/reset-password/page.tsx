import { Suspense } from "react";
import type { Metadata } from "next";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { GuestGate } from "@/components/auth/guest-gate";

export const metadata: Metadata = {
  title: "Set new password",
};

export default function AuthResetPasswordPage() {
  return (
    <GuestGate>
      <Suspense>
        <ResetPasswordForm />
      </Suspense>
    </GuestGate>
  );
}
