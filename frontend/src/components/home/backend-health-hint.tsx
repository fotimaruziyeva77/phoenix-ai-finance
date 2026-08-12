"use client";

import { useEffect, useState } from "react";

import { fetchBackendHealth } from "@/lib/api/health";

type State =
  | { kind: "loading" }
  | { kind: "ok"; status: string }
  | { kind: "error"; message: string };

export function BackendHealthHint() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetchBackendHealth()
      .then((body) => setState({ kind: "ok", status: body.status }))
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : "Failed to reach backend";
        setState({ kind: "error", message });
      });
  }, []);

  if (state.kind === "loading") {
    return (
      <p className="bf-backendHealth" data-state="pending" aria-live="polite" aria-busy>
        Checking API health…
      </p>
    );
  }

  if (state.kind === "ok") {
    return (
      <p className="bf-backendHealth" aria-live="polite">
        Backend health: <strong>{state.status}</strong>
      </p>
    );
  }

  return (
    <p className="bf-backendHealth" data-state="error" role="status" aria-live="polite">
      Backend: {state.message}
    </p>
  );
}
