"use client";

import { useMemo, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useWorkspaceBots } from "@/hooks/useWorkspaceBots";
import { cloneBot } from "@/lib/api/bots";
import type { WorkspaceBot } from "@/lib/api/bots";

import { BotsEmptyState } from "./bots-empty-state";
import { BotsErrorBanner } from "./bots-error-banner";
import { BotsList } from "./bots-list";
import { BotsListSkeleton } from "./bots-list-skeleton";
import { BotsPageHeader } from "./bots-page-header";
import { BotsToolbar } from "./bots-toolbar";
import styles from "./bots-dashboard.module.css";

export function DashboardBots() {
  const { status, bots, endpointUnavailable, errorMessage, refetch } = useWorkspaceBots();
  const { accessToken } = useAuth();
  const [cloningId, setCloningId] = useState<string | null>(null);

  // ── Search & filter state ──────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<WorkspaceBot["status"] | "">("");

  const filteredBots = useMemo(() => {
    let result = bots;

    // Filter by status
    if (statusFilter) {
      result = result.filter((bot) => bot.status === statusFilter);
    }

    // Filter by search query (name match, case-insensitive)
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (bot) =>
          bot.name.toLowerCase().includes(q) ||
          bot.nicheLabel.toLowerCase().includes(q) ||
          bot.goalLabel.toLowerCase().includes(q),
      );
    }

    return result;
  }, [bots, searchQuery, statusFilter]);

  const showLoading = status === "loading" || status === "idle";
  const showError = status === "error" && Boolean(errorMessage);
  const showEmpty = status === "success" && bots.length === 0;
  const showList = status === "success" && bots.length > 0;

  async function handleClone(botId: string) {
    if (cloningId !== null) return;
    setCloningId(botId);
    try {
      await cloneBot(accessToken, botId);
      await refetch();
    } finally {
      setCloningId(null);
    }
  }

  return (
    <div className={styles.stack} data-testid="bots-page-root">
      <BotsPageHeader />
      <BotsToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
      />

      {showError && errorMessage ? (
        <BotsErrorBanner message={errorMessage} onRetry={() => void refetch()} />
      ) : null}

      <section
        className={styles.mainRegion}
        data-testid="bots-data-region"
        aria-label="Bots list content"
        aria-live="polite"
      >
        {showLoading ? <BotsListSkeleton /> : null}
        {showEmpty ? <BotsEmptyState endpointUnavailable={endpointUnavailable} /> : null}
        {showList ? (
          <BotsList bots={filteredBots} onClone={(id) => void handleClone(id)} cloningId={cloningId} />
        ) : null}
      </section>
    </div>
  );
}
