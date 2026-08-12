import { Suspense } from "react";

import { OAuthCallbackHandler } from "@/components/auth/oauth-callback-handler";

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "calc(100vh - 57px)",
            display: "grid",
            placeItems: "center",
            color: "#a1a1aa",
          }}
        >
          Loading…
        </div>
      }
    >
      <OAuthCallbackHandler />
    </Suspense>
  );
}
