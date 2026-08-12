import { Suspense } from "react";
import type { Metadata } from "next";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { GuestGate } from "@/components/auth/guest-gate";

export const metadata: Metadata = {
  title: "Reset password",
};

export default function ForgotPasswordPage() {
  return (
    <GuestGate>
      <Suspense>
        <ForgotPasswordForm />
      </Suspense>
    </GuestGate>
  );
}
