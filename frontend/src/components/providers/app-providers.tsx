"use client";

import type { ReactNode } from "react";

import { ErrorBoundary } from "@/components/error-boundary";
import { AuthProvider } from "@/contexts/auth-context";
import { LanguageProvider } from "@/contexts/language-context";

type Props = {
  children: ReactNode;
};

/**
 * Root providers.
 *
 * `NicheCatalogProvider` deliberately lives in the dashboard layout rather than
 * here: only the bot-creation wizard consumes it, and mounting it at the root
 * made every public page fire a backend request it has no use for.
 */
export function AppProviders({ children }: Props) {
  return (
    <ErrorBoundary>
      <LanguageProvider>
        <AuthProvider>{children}</AuthProvider>
      </LanguageProvider>
    </ErrorBoundary>
  );
}
