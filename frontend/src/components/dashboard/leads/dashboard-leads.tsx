"use client";

import { useEffect, useMemo, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useWorkspaceLeads } from "@/hooks/useWorkspaceLeads";

import { LeadsEmptyState } from "./leads-empty-state";
import { LeadsErrorBanner } from "./leads-error-banner";
import { LeadsList } from "./leads-list";
import { LeadsListSkeleton } from "./leads-list-skeleton";
import { LeadsStatsBar } from "./leads-stats-bar";
import { LeadsToolbar } from "./leads-toolbar";
import styles from "./leads-dashboard.module.css";

export function DashboardLeads() {
  const { t } = useLanguage();
  const [statusFilter, setStatusFilter] = useState("");
  const [nicheInput, setNicheInput] = useState("");
  const [nicheDebounced, setNicheDebounced] = useState("");
  const [tempFilter, setTempFilter] = useState("");

  useEffect(() => {
    const id = setTimeout(() => setNicheDebounced(nicheInput.trim()), 400);
    return () => clearTimeout(id);
  }, [nicheInput]);

  const apiFilters = useMemo(
    () => ({
      status: statusFilter || undefined,
      niche: nicheDebounced || undefined,
      temperature: tempFilter || undefined,
    }),
    [statusFilter, nicheDebounced, tempFilter],
  );

  const { status, leads, total, endpointUnavailable, errorMessage, refetch, hasMore, loadingMore, loadMore } = useWorkspaceLeads(apiFilters);

  const showLoading = status === "loading" || status === "idle";
  const showError = status === "error" && Boolean(errorMessage);
  const showList = status === "success" && leads.length > 0;
  const showEmpty = status === "success" && leads.length === 0;

  const hasActiveFilters = Boolean(statusFilter || tempFilter || nicheDebounced);

  function formatCount(n: number): string {
    const word = n === 1 ? (t("dashboard.leads.countOne") as string) : (t("dashboard.leads.count") as string);
    return `${n} ${word}`;
  }

  return (
    <div className={styles.stack} data-testid="leads-page-root">
      <header className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>{t("dashboard.leads.title") as string}</h1>
          <p className={styles.pageSubtitle}>
            {t("dashboard.leads.subtitle") as string}
          </p>
          {status === "success" && !endpointUnavailable ? (
            <>
              <p className={styles.countLine} data-testid="leads-total-count">
                {formatCount(total)}
                {hasActiveFilters ? ` ${t("dashboard.leads.filtered") as string}` : ""}
              </p>
              {total > leads.length ? (
                <p className={styles.capNote}>
                  {t("dashboard.leads.showing") as string} {leads.length} / {total}
                </p>
              ) : null}
            </>
          ) : null}
        </div>
      </header>

      {/* Stats bar — visible when we have leads */}
      {showList ? <LeadsStatsBar leads={leads} total={total} /> : null}

      <LeadsToolbar
        status={statusFilter}
        niche={nicheInput}
        temperature={tempFilter}
        onStatusChange={setStatusFilter}
        onNicheChange={setNicheInput}
        onTemperatureChange={setTempFilter}
      />

      {showError && errorMessage ? (
        <LeadsErrorBanner message={errorMessage} onRetry={() => void refetch()} />
      ) : null}

      <section
        className={styles.mainRegion}
        data-testid="leads-data-region"
        aria-label="Leads list content"
        aria-live="polite"
      >
        {showLoading ? <LeadsListSkeleton /> : null}
        {showEmpty ? (
          <LeadsEmptyState
            filtered={hasActiveFilters}
            endpointUnavailable={endpointUnavailable}
          />
        ) : null}
        {showList ? (
          <LeadsList
            leads={leads}
            hasMore={hasMore}
            loadingMore={loadingMore}
            onLoadMore={() => void loadMore?.()}
          />
        ) : null}
      </section>
    </div>
  );
}
