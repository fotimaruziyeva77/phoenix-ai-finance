"use client";

import { Suspense } from "react";

import { AuthGate } from "@/components/auth/auth-gate";
import { AuthSessionLoading } from "@/components/auth/auth-session-loading";
import { useFinanceLang } from "@/hooks/useFinanceLang";

import { AdvisorChat } from "./advisor-chat";
import { BusinessPlanView } from "./business-plan-view";
import { CreditView } from "./credit-view";
import { TaxView } from "./tax-view";
import { ToolShell, type ToolKey } from "./tool-shell";

/**
 * Renders one advisory tool with its language-aware heading and shell.
 *
 * The tools sit behind login (product decision 2026-08-12): the landing page
 * markets them, but calculations require an account. `AuthGate` redirects
 * anonymous visitors to `/login?next=<tool>`; the demo credentials satisfy it
 * with no backend. Suspense is required because AuthGate reads search params.
 */
export function FinanceToolPage({ tool }: { tool: ToolKey }) {
  const { c } = useFinanceLang();

  const meta: Record<ToolKey, { title: string; subtitle: string; disclaimer: string }> = {
    plan: { title: c.plan.title, subtitle: c.plan.subtitle, disclaimer: c.plan.disclaimer },
    credit: { title: c.credit.title, subtitle: c.credit.subtitle, disclaimer: c.credit.disclaimer },
    tax: { title: c.tax.title, subtitle: c.tax.subtitle, disclaimer: c.tax.disclaimer },
    chat: { title: c.chat.title, subtitle: c.chat.subtitle, disclaimer: c.chat.engineNote },
  };

  const { title, subtitle, disclaimer } = meta[tool];

  return (
    <Suspense fallback={<AuthSessionLoading />}>
      <AuthGate>
        <ToolShell tool={tool} title={title} subtitle={subtitle} disclaimer={disclaimer}>
          {tool === "plan" ? <BusinessPlanView /> : null}
          {tool === "credit" ? <CreditView /> : null}
          {tool === "tax" ? <TaxView /> : null}
          {tool === "chat" ? <AdvisorChat /> : null}
        </ToolShell>
      </AuthGate>
    </Suspense>
  );
}
