"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import styles from "./pricing-section.module.css";

const PLAN_IDS = ["free", "pro", "business", "enterprise"] as const;
const PLAN_PRICES: Record<string, string> = { free: "$0", pro: "$39", business: "$99" };
const PLAN_IS_POPULAR: Record<string, boolean> = { pro: true };
const PLAN_IS_ENTERPRISE: Record<string, boolean> = { enterprise: true };
export function PricingSection() {
  const { t } = useLanguage();

  return (
    <section id="pricing" className="bf-landingSection" aria-labelledby="pricing-heading">
      <div className="bf-landingSection__header">
        <h2 id="pricing-heading" className="bf-landingSection__title">
          {String(t("pricing.title"))}
        </h2>
        <p className="bf-landingSection__lead">
          {String(t("pricing.subtitle"))}
        </p>
      </div>
      <ul className={styles.grid} aria-label="Pricing plans">
        {PLAN_IDS.map((id) => {
          const plan = t(`pricing.plans.${id}`) as { name: string; price: string; desc: string; cta: string; features: string[] };
          const isPopular = PLAN_IS_POPULAR[id];
          const isEnterprise = PLAN_IS_ENTERPRISE[id];
          const displayPrice = PLAN_PRICES[id] ?? "";

          return (
            <li
              key={id}
              className={[
                styles.card,
                isPopular ? styles.popular : "",
                isEnterprise ? styles.enterpriseCard : "",
              ].filter(Boolean).join(" ")}
            >
              {isPopular && (
                <div className={styles.priceBadge} aria-label="Most popular plan">
                  {String(t("pricing.popular"))}
                </div>
              )}

              <h3 className={styles.planName}>{plan.name}</h3>

              <p className={styles.price}>
                {isEnterprise ? (
                  <span className={styles.priceAmount}>{plan.price}</span>
                ) : (
                  <>
                    <span className={styles.priceAmount}>{displayPrice}</span>
                    <span className={styles.pricePeriod}> {String(t("pricing.perMonth"))}</span>
                  </>
                )}
              </p>

              <p className={styles.description}>{plan.desc}</p>

              <ul className={styles.features} aria-label={`${plan.name} features`}>
                {Array.isArray(plan.features) && plan.features.map((f, fi) => (
                  <li key={fi}>
                    <span className={styles.checkmark} aria-hidden>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              {isEnterprise ? (
                <a href="mailto:support@botforge.ai" className={styles.cta}>
                  {plan.cta}
                </a>
              ) : (
                <Link href="/signup" className={styles.cta}>
                  {plan.cta}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
