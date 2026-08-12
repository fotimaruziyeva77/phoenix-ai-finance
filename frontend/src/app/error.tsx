"use client";

import { useEffect } from "react";

import { ErrorFallback } from "@/components/ui/error-fallback";

export default function RouteErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Route error:", error);
  }, [error]);

  return (
    <main className="bf-main--narrow">
      <ErrorFallback error={error} onReset={reset} />
    </main>
  );
}
