"use client";

import { useState, type FormEvent } from "react";

import { IconAlertTriangle, IconReceipt, IconXCircle } from "@/components/ui/icons";
import { AdviceButton } from "@/components/dashboard/finance/advice-modal";
import { useFinanceLang } from "@/hooks/useFinanceLang";
import { summarizeTax } from "@/lib/finance/advice-summaries";
import {
  SECTORS,
  SELF_EMPLOYED_TURNOVER_CAP_SOM,
  TURNOVER_TAX_CAP_SOM,
  calculateTaxRegimes,
  getSector,
  type TaxComparison,
} from "@/lib/finance/engine";

import styles from "./credit-view.module.css";

type FormState = {
  monthlyRevenue: string;
  sectorId: string;
  employeeCount: string;
  avgSalary: string;
  monthlyRent: string;
  isIndividual: boolean;
};

const INITIAL: FormState = {
  monthlyRevenue: "70000000",
  sectorId: SECTORS[0]!.id,
  employeeCount: "2",
  avgSalary: "4500000",
  monthlyRent: "8000000",
  isIndividual: true,
};

const toInt = (v: string) => {
  const n = Number.parseInt(v.replace(/\s/g, ""), 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
};

/** Shared by the page and the advisor chat so both produce identical numbers. */
export function computeTax(input: {
  monthlyRevenue: number;
  sectorId: string;
  employeeCount: number;
  avgSalary: number;
  monthlyRent: number;
  isIndividual: boolean;
}): TaxComparison | null {
  const sector = getSector(input.sectorId);
  if (!sector) return null;
  const marginRate = sector.grossMarginPct / 100;
  return calculateTaxRegimes({
    annualRevenueSom: input.monthlyRevenue * 12,
    annualCostOfGoodsSom: Math.round(input.monthlyRevenue * (1 - marginRate)) * 12,
    annualPayrollSom: input.employeeCount * input.avgSalary * 12,
    annualOtherCostsSom: input.monthlyRent * 12,
    isIndividualEntrepreneur: input.isIndividual,
  });
}

export function TaxView() {
  const { c, sector } = useFinanceLang();
  const [form, setForm] = useState<FormState>(INITIAL);
  const [out, setOut] = useState<TaxComparison | null>(null);

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm((p) => ({ ...p, [k]: v }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setOut(
      computeTax({
        monthlyRevenue: toInt(form.monthlyRevenue),
        sectorId: form.sectorId,
        employeeCount: toInt(form.employeeCount),
        avgSalary: toInt(form.avgSalary),
        monthlyRent: toInt(form.monthlyRent),
        isIndividual: form.isIndividual,
      }),
    );
  };

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h2 className={styles.formTitle}>{c.tax.formTitle}</h2>
        <p className={styles.formHint}>{c.tax.formHint}</p>

        <label className={styles.field}>
          <span className={styles.label}>{c.tax.f.revenue}</span>
          <input className={styles.input} inputMode="numeric" value={form.monthlyRevenue} onChange={(e) => set("monthlyRevenue", e.target.value)} />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>{c.tax.f.sector}</span>
          <select className={styles.select} value={form.sectorId} onChange={(e) => set("sectorId", e.target.value)}>
            {SECTORS.map((s) => (
              <option key={s.id} value={s.id}>
                {sector(s.id)}
              </option>
            ))}
          </select>
        </label>

        <div className={styles.row}>
          <label className={styles.field}>
            <span className={styles.label}>{c.tax.f.employees}</span>
            <input className={styles.input} inputMode="numeric" value={form.employeeCount} onChange={(e) => set("employeeCount", e.target.value)} />
          </label>
          <label className={styles.field}>
            <span className={styles.label}>{c.tax.f.salary}</span>
            <input className={styles.input} inputMode="numeric" value={form.avgSalary} onChange={(e) => set("avgSalary", e.target.value)} />
          </label>
        </div>

        <label className={styles.field}>
          <span className={styles.label}>{c.tax.f.rent}</span>
          <input className={styles.input} inputMode="numeric" value={form.monthlyRent} onChange={(e) => set("monthlyRent", e.target.value)} />
        </label>

        <label className={styles.checkbox}>
          <input type="checkbox" checked={form.isIndividual} onChange={(e) => set("isIndividual", e.target.checked)} />
          {c.tax.f.individual}
        </label>

        <button type="submit" className={styles.submit}>
          {c.tax.submit}
        </button>
      </form>

      <div className={styles.results}>
        {out ? (
          <TaxResults comparison={out} />
        ) : (
          <div className={styles.empty}>
            <div>
              <div className={styles.emptyIcon}><IconReceipt size={40} /></div>
              <p>{c.tax.empty}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function TaxResults({ comparison }: { comparison: TaxComparison }) {
  const { c, mc, money, fill } = useFinanceLang();
  const { cheapest, savingsVsWorstSom, annualRevenueSom } = comparison;
  const overCap = annualRevenueSom > TURNOVER_TAX_CAP_SOM;
  const overSelfEmployedCap = annualRevenueSom > SELF_EMPLOYED_TURNOVER_CAP_SOM;

  return (
    <>
      {savingsVsWorstSom > 0 ? (
        <section className={styles.headline}>
          <p className={styles.headlineLabel}>{c.tax.headlineLabel}</p>
          <p className={styles.headlineValue}>
            {money(savingsVsWorstSom)} {c.currency}
          </p>
          <p className={styles.headlineCaption}>
            {fill(c.tax.headlineCaption, {
              regime: cheapest ? mc(`regime.${cheapest.regime}`) : "—",
            })}
          </p>
        </section>
      ) : null}

      <div>
        <AdviceButton summary={summarizeTax(comparison)} />
      </div>

      {overSelfEmployedCap && !overCap ? (
        <div className={`${styles.load} ${styles["load--warning"]}`}>
          <IconAlertTriangle size={16} style={{ color: "#fbbf24" }} /> {c.tax.warnOverOneBillion}
        </div>
      ) : null}

      {overCap ? (
        <div className={`${styles.load} ${styles["load--danger"]}`}>
          <IconXCircle size={16} style={{ color: "#f87171" }} /> {c.tax.warnOverFiveBillion}
        </div>
      ) : null}

      <section className={styles.card}>
        <h3 className={styles.sectionTitle}>{c.tax.compareTitle}</h3>
        <p className={styles.sectionHint}>
          {c.tax.annualRevenue}: {money(annualRevenueSom)} {c.currency}
        </p>
        {comparison.results.map((r) => (
          <article
            key={r.regime}
            className={styles.program}
            data-best={cheapest?.regime === r.regime}
            style={r.eligible ? undefined : { opacity: 0.55 }}
          >
            <div className={styles.programHead}>
              <h4 className={styles.programTitle}>
                {mc(`regime.${r.regime}`)}
                {cheapest?.regime === r.regime ? (
                  <span
                    className={styles.badge}
                    style={{
                      background: "color-mix(in srgb, #22c55e 28%, transparent)",
                      color: "#86efac",
                    }}
                  >
                    {c.tax.cheapest}
                  </span>
                ) : null}
              </h4>
              <span className={styles.programRate}>{money(r.annualTaxSom)}</span>
            </div>
            <p className={styles.programMeta}>
              {fill(c.tax.monthlyIs, { amount: money(r.monthlyTaxSom), pct: r.effectiveRatePct })}
            </p>
            {!r.eligible && r.ineligibleCode ? (
              <p className={styles.programMeta}>
                <strong>{c.tax.notEligible}:</strong> {mc(r.ineligibleCode)}
              </p>
            ) : (
              <p className={styles.programMeta}>
                {r.breakdown.map((b) => `${mc(b.code)}: ${money(b.amountSom)}`).join(" · ")}
              </p>
            )}
          </article>
        ))}
        <p className={styles.disclaimer}>{c.tax.engineDisclaimer}</p>
      </section>
    </>
  );
}
