"use client";

import { useMemo } from "react";

import { useAuth } from "@/hooks/useAuth";
import { getWorkspaceOverviewState } from "@/lib/dashboard/workspace-overview";
import type { AuthUser } from "@/types/auth";

import { OverviewFirstBotCta } from "./overview-first-bot-cta";
import { OverviewPanels } from "./overview-panels";
import { OverviewQuickActions } from "./overview-quick-actions";
import { OverviewWelcome } from "./overview-welcome";
import styles from "./overview.module.css";

function greetingFirstName(user: AuthUser | null): string {
  if (!user) return "";
  const full = user.full_name?.trim();
  if (full) {
    const first = full.split(/\s+/)[0];
    return first ?? "";
  }
  const local = user.email.split("@")[0];
  if (!local) return "";
  return local.charAt(0).toUpperCase() + local.slice(1);
}

export function DashboardOverview() {
  const { user } = useAuth();
  const workspace = useMemo(() => getWorkspaceOverviewState(), []);
  const name = greetingFirstName(user);

  return (
    <div className={styles.stack}>
      <OverviewWelcome greetingName={name} />
      <OverviewQuickActions />
      {!workspace.hasBots ? <OverviewFirstBotCta /> : null}
      <OverviewPanels />
    </div>
  );
}
