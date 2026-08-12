import { Suspense } from "react";

import { AuthSessionLoading } from "@/components/auth/auth-session-loading";
import { GuestGate } from "@/components/auth/guest-gate";
import { SignupForm } from "@/components/auth/signup-form";

export default function SignupPage() {
  return (
    <Suspense fallback={<AuthSessionLoading />}>
      <GuestGate>
        <SignupForm />
      </GuestGate>
    </Suspense>
  );
}
