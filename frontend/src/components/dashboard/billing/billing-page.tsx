"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import {
  createCheckoutSession,
  createPortalSession,
  fetchPlans,
  fetchSubscription,
  type PlanDto,
  type SubscriptionDto,
} from "@/lib/api/billing";

import styles from "./billing-page.module.css";

// ─── helpers ────────────────────────────────────────────────────────────────

const PLAN_ORDER = ["free", "pro", "business", "enterprise"];

function planRank(slug: string): number {
  return PLAN_ORDER.indexOf(slug);
}

type TFn = ReturnType<typeof useLanguage>["t"];

/** Format a limit value: null → "Unlimited", else localized number */
function fmtLimit(value: number | null, unlimitedLabel: string): string {
  if (value === null) return unlimitedLabel;
  return value.toLocaleString();
}

/** Format storage: null → Unlimited, ≥1000 → X GB, else X MB */
function fmtStorage(mb: number | null, unlimitedLabel: string): string {
  if (mb === null) return unlimitedLabel;
  if (mb >= 1000) return `${mb / 1000} GB`;
  return `${mb} MB`;
}

// ─── status badge ────────────────────────────────────────────────────────────

const STATUS_LABEL_KEYS: Record<string, string> = {
  active: "dashboard.billing.statusActive",
  trialing: "dashboard.billing.statusTrialing",
  past_due: "dashboard.billing.statusPastDue",
  canceled: "dashboard.billing.statusCanceled",
  expired: "dashboard.billing.statusExpired",
};

function getStatusStyle(status: string) {
  if (status === "active" || status === "trialing") return styles.badgeActive ?? "";
  if (status === "past_due") return styles.badgePastDue ?? "";
  return styles.badgeCanceled ?? "";
}

function StatusBadge({ status, t }: { status: SubscriptionDto["status"]; t: TFn }) {
  const label = t(STATUS_LABEL_KEYS[status] ?? "dashboard.billing.statusActive") as string;
  return <span className={`${styles.badge} ${getStatusStyle(status)}`}>{label}</span>;
}

// ─── main component ──────────────────────────────────────────────────────────

export function BillingPage() {
  const { t, lang } = useLanguage();
  const { accessToken } = useAuth();
  const searchParams = useSearchParams();
  const checkoutStatus = searchParams.get("status") as "success" | "canceled" | null;

  const [sub, setSub] = useState<SubscriptionDto | null>(null);
  const [plans, setPlans] = useState<PlanDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  const unlimited = t("dashboard.billing.unlimited") as string;

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const [subData, plansData] = await Promise.all([
          fetchSubscription(accessToken),
          fetchPlans(),
        ]);
        if (!alive) return;
        setSub(subData);
        setPlans(plansData);
      } catch (e: unknown) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : (t("dashboard.billing.loadError") as string));
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [accessToken, t]);

  const handleUpgrade = useCallback(
    async (planSlug: string) => {
      setUpgrading(planSlug);
      setError(null);
      try {
        const { checkout_url } = await createCheckoutSession(accessToken, planSlug);
        window.location.href = checkout_url;
      } catch (e: unknown) {
        setError(
          e instanceof Error && e.message.includes("stripe_not_configured")
            ? (t("dashboard.billing.stripeNotConfigured") as string)
            : e instanceof Error
              ? e.message
              : (t("dashboard.billing.checkoutFailed") as string),
        );
      } finally {
        setUpgrading(null);
      }
    },
    [accessToken, t],
  );

  const handlePortal = useCallback(async () => {
    setPortalLoading(true);
    setError(null);
    try {
      const { portal_url } = await createPortalSession(accessToken);
      window.location.href = portal_url;
    } catch (e: unknown) {
      setError(
        e instanceof Error && e.message.includes("stripe_not_configured")
          ? (t("dashboard.billing.noStripeLinked") as string)
          : e instanceof Error
            ? e.message
            : (t("dashboard.billing.portalUnavailable") as string),
      );
    } finally {
      setPortalLoading(false);
    }
  }, [accessToken, t]);

  if (loading) {
    return (
      <div className={styles.loadingWrap}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>{t("dashboard.billing.loading") as string}</p>
      </div>
    );
  }

  const currentPlan = plans.find((p) => p.slug === sub?.plan_slug) ?? null;
  const currentRank = planRank(sub?.plan_slug ?? "free");

  const dateLocale = lang === "uz" ? "uz-UZ" : lang === "ru" ? "ru-RU" : "en-US";

  return (
    <div className={styles.stack} data-testid="billing-page-root">
      {/* ── Page header ───────────────────────────────────── */}
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>{t("dashboard.billing.title") as string}</h1>
        <p className={styles.pageSubtitle}>{t("dashboard.billing.subtitle") as string}</p>
      </header>

      {checkoutStatus === "success" && (
        <div className={styles.bannerSuccess}>
          {t("dashboard.billing.checkoutSuccess") as string}
        </div>
      )}
      {checkoutStatus === "canceled" && (
        <div className={styles.bannerCanceled}>
          {t("dashboard.billing.checkoutCanceled") as string}
        </div>
      )}
      {error && <div className={styles.error}>{error}</div>}

      {/* ── Current plan ──────────────────────────────────── */}
      {sub && (
        <div className={styles.currentCard}>
          <div className={styles.currentHeader}>
            <div>
              <p className={styles.currentTitle}>
                {sub.plan_name}{" "}
                {sub.price_dollars > 0 && (
                  <span className={styles.priceInline}>
                    (${sub.price_dollars}{t("dashboard.billing.perMonth") as string})
                  </span>
                )}
              </p>
              <p className={styles.currentMeta}>
                {t("dashboard.billing.activeSub") as string}
                {sub.current_period_end && (
                  <span className={styles.periodEnd}>
                    {" · "}
                    {t("dashboard.billing.renews") as string}{" "}
                    {new Date(sub.current_period_end).toLocaleDateString(dateLocale, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                )}
              </p>
            </div>
            <StatusBadge status={sub.status} t={t} />
          </div>

          {currentPlan && (
            <div className={styles.limitsGrid}>
              <div className={styles.limitItem}>
                <span className={styles.limitLabel}>
                  {t("dashboard.billing.convPerMonth") as string}
                </span>
                <span className={styles.limitValue}>
                  {fmtLimit(currentPlan.conversations_per_month, unlimited)}
                </span>
              </div>
              <div className={styles.limitItem}>
                <span className={styles.limitLabel}>
                  {t("dashboard.billing.bots") as string}
                </span>
                <span className={styles.limitValue}>
                  {fmtLimit(currentPlan.bots_max, unlimited)}
                </span>
              </div>
              <div className={styles.limitItem}>
                <span className={styles.limitLabel}>
                  {t("dashboard.billing.pdfFiles") as string}
                </span>
                <span className={styles.limitValue}>
                  {fmtLimit(currentPlan.pdf_files_max, unlimited)}
                </span>
              </div>
              <div className={styles.limitItem}>
                <span className={styles.limitLabel}>
                  {t("dashboard.billing.storage") as string}
                </span>
                <span className={styles.limitValue}>
                  {fmtStorage(currentPlan.storage_mb, unlimited)}
                </span>
              </div>
            </div>
          )}

          <div className={styles.actions}>
            {sub.plan_slug !== "free" && sub.stripe_subscription_id && (
              <button
                className={styles.btnSecondary}
                onClick={handlePortal}
                disabled={portalLoading}
              >
                {portalLoading
                  ? (t("dashboard.billing.opening") as string)
                  : (t("dashboard.billing.manageBilling") as string)}
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Plans grid ─────────────────────────────────────── */}
      <section>
        <h2 className={styles.sectionTitle}>
          {t("dashboard.billing.availablePlans") as string}
        </h2>
        <div className={styles.plansGrid}>
          {plans.map((plan) => {
            const isCurrent = plan.slug === sub?.plan_slug;
            const planR = planRank(plan.slug);
            const isUpgrade = planR > currentRank;
            const isLoading = upgrading === plan.slug;

            return (
              <div
                key={plan.slug}
                className={[
                  styles.planCard,
                  isCurrent ? styles.planCardCurrent : "",
                  plan.is_popular && !isCurrent ? styles.planCardPopular : "",
                ].join(" ")}
              >
                {plan.is_popular && !isCurrent && (
                  <span className={styles.popularBadge}>
                    {t("dashboard.billing.mostPopular") as string}
                  </span>
                )}
                <p className={styles.planName}>{plan.name}</p>
                <p className={styles.planPrice}>
                  {plan.slug === "enterprise"
                    ? (t("dashboard.billing.contactUs") as string)
                    : plan.price_dollars === 0
                      ? (t("dashboard.billing.free") as string)
                      : `$${plan.price_dollars}`}
                  {plan.price_dollars > 0 && plan.slug !== "enterprise" && (
                    <span className={styles.planPriceUnit}>
                      {t("dashboard.billing.perMonth") as string}
                    </span>
                  )}
                </p>
                <p className={styles.planTagline}>{plan.tagline}</p>
                <ul className={styles.planFeatures}>
                  <li className={styles.planFeature}>
                    {fmtLimit(plan.conversations_per_month, unlimited)}{" "}
                    {t("dashboard.billing.conversations") as string}
                  </li>
                  <li className={styles.planFeature}>
                    {fmtLimit(plan.bots_max, unlimited)}{" "}
                    {plan.bots_max === 1
                      ? (t("dashboard.billing.bot") as string)
                      : (t("dashboard.billing.bots") as string).toLowerCase()}
                  </li>
                  <li className={styles.planFeature}>
                    {fmtLimit(plan.pdf_files_max, unlimited)}{" "}
                    {t("dashboard.billing.pdfFiles") as string}
                  </li>
                  <li className={styles.planFeature}>
                    {fmtStorage(plan.storage_mb, unlimited)}{" "}
                    {t("dashboard.billing.storageUnit") as string}
                  </li>
                </ul>

                {isCurrent ? (
                  <button className={`${styles.planBtn} ${styles.planBtnCurrent}`} disabled>
                    {t("dashboard.billing.currentPlanBtn") as string}
                  </button>
                ) : plan.slug === "enterprise" ? (
                  <button
                    className={`${styles.planBtn} ${styles.planBtnUpgrade}`}
                    onClick={() => handleUpgrade(plan.slug)}
                    disabled={!!upgrading}
                  >
                    {upgrading === plan.slug
                      ? (t("dashboard.billing.redirecting") as string)
                      : (t("dashboard.billing.contactUs") as string)}
                  </button>
                ) : plan.slug === "free" ? (
                  <button className={`${styles.planBtn} ${styles.planBtnDowngrade}`} disabled>
                    {t("dashboard.billing.contactSupport") as string}
                  </button>
                ) : isUpgrade ? (
                  <button
                    className={`${styles.planBtn} ${styles.planBtnUpgrade}`}
                    onClick={() => handleUpgrade(plan.slug)}
                    disabled={!!upgrading}
                  >
                    {isLoading
                      ? (t("dashboard.billing.redirecting") as string)
                      : (t("dashboard.billing.upgrade") as string)}
                  </button>
                ) : (
                  <button
                    className={`${styles.planBtn} ${styles.planBtnDowngrade}`}
                    onClick={handlePortal}
                    disabled={portalLoading}
                  >
                    {portalLoading
                      ? (t("dashboard.billing.opening") as string)
                      : (t("dashboard.billing.manage") as string)}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
