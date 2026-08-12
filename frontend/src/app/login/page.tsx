import { Suspense } from "react";

import { AuthSessionLoading } from "@/components/auth/auth-session-loading";
import { GuestGate } from "@/components/auth/guest-gate";
import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthSessionLoading />}>
      <GuestGate>
        <LoginForm />
      </GuestGate>
    </Suspense>
  );
}
