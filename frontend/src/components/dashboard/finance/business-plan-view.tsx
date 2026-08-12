"use client";

import { useState, type FormEvent } from "react";

import {
  IconAlertTriangle,
  IconBulb,
  IconChart,
  IconCheckCircle,
  IconGift,
  IconPin,
  IconReceipt,
  IconSliders,
  IconXCircle,
} from "@/components/ui/icons";
import { AdviceButton } from "@/components/dashboard/finance/advice-modal";
import { useFinanceLang } from "@/hooks/useFinanceLang";
import { summarizePlan } from "@/lib/finance/advice-summaries";
import {
  DEMO_COMPARISON_PAIR,
  LOCATIONS,
  SECTORS,
  buildBusinessPlan,
  compareLocations,
  type BusinessPlanInput,
  type BusinessPlanResult,
  type LocationComparison,
  type Verdict,
} from "@/lib/finance/engine";

import styles from "./business-plan-view.module.css";

/** Traffic-light verdict marks — colour comes from the verdict card itself. */
export const VERDICT_ICON: Record<Verdict, React.ReactNode> = {
  viable: <IconCheckCircle size={17} style={{ color: "#4ade80" }} />,
  tight: <IconAlertTriangle size={17} style={{ color: "#fbbf24" }} />,
  unprofitable: <IconXCircle size={17} style={{ color: "#f87171" }} />,
};

/** Large variant for the verdict banner head. */
const VERDICT_BADGE: Record<Verdict, React.ReactNode> = {
  viable: <IconCheckCircle size={30} style={{ color: "#4ade80" }} />,
  tight: <IconAlertTriangle size={30} style={{ color: "#fbbf24" }} />,
  unprofitable: <IconXCircle size={30} style={{ color: "#f87171" }} />,
};

type FormState = {
  businessName: string;
  sectorId: string;
  locationId: string;
  initialCapitalSom: string;
  employeeCount: string;
  monthlyRentSom: string;
  productDescription: string;
  goal: string;
};

const INITIAL_FORM: FormState = {
  businessName: "",
  sectorId: SECTORS[0]!.id,
  locationId: "toshkent",
  initialCapitalSom: "150000000",
  employeeCount: "2",
  monthlyRentSom: "8000000",
  productDescription: "",
  goal: "",
};

function toInt(value: string): number {
  const n = Number.parseInt(value.replace(/\s/g, ""), 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

export function BusinessPlanView() {
  const { c } = useFinanceLang();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<
    { plan: BusinessPlanResult; comparison: LocationComparison } | null
  >(null);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!form.businessName.trim()) {
      setError(c.plan.nameRequired);
      return;
    }
    const input: BusinessPlanInput = {
      businessName: form.businessName.trim(),
      sectorId: form.sectorId,
      locationId: form.locationId,
      initialCapitalSom: toInt(form.initialCapitalSom),
      employeeCount: toInt(form.employeeCount),
      monthlyRentSom: toInt(form.monthlyRentSom),
      productDescription: form.productDescription,
      goal: form.goal,
    };
    try {
      const compareIds = Array.from(new Set([form.locationId, ...DEMO_COMPARISON_PAIR]));
      setResult({
        plan: buildBusinessPlan(input),
        comparison: compareLocations(input, compareIds),
      });
      setError(null);
    } catch {
      setError(c.plan.nameRequired);
      setResult(null);
    }
  };

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h2 className={styles.formTitle}>{c.plan.formTitle}</h2>
        <p className={styles.formHint}>{c.plan.formHint}</p>

        <Field label={c.plan.f.name}>
          <input
            className={styles.input}
            value={form.businessName}
            onChange={(e) => set("businessName", e.target.value)}
            placeholder="Baraka Market"
          />
        </Field>

        <Field label={c.plan.f.sector}>
          <SectorSelect value={form.sectorId} onChange={(v) => set("sectorId", v)} />
        </Field>

        <Field label={c.plan.f.location}>
          <LocationSelect value={form.locationId} onChange={(v) => set("locationId", v)} />
        </Field>

        <div className={styles.row}>
          <Field label={c.plan.f.capital}>
            <input
              className={styles.input}
              inputMode="numeric"
              value={form.initialCapitalSom}
              onChange={(e) => set("initialCapitalSom", e.target.value)}
            />
          </Field>
          <Field label={c.plan.f.employees}>
            <input
              className={styles.input}
              inputMode="numeric"
              value={form.employeeCount}
              onChange={(e) => set("employeeCount", e.target.value)}
            />
          </Field>
        </div>

        <Field label={c.plan.f.rent}>
          <input
            className={styles.input}
            inputMode="numeric"
            value={form.monthlyRentSom}
            onChange={(e) => set("monthlyRentSom", e.target.value)}
          />
        </Field>

        <Field label={c.plan.f.product}>
          <input
            className={styles.input}
            value={form.productDescription}
            onChange={(e) => set("productDescription", e.target.value)}
          />
        </Field>

        <Field label={c.plan.f.goal}>
          <input
            className={styles.input}
            value={form.goal}
            onChange={(e) => set("goal", e.target.value)}
          />
        </Field>

        <button type="submit" className={styles.submit}>
          {c.plan.submit}
        </button>

        {error ? <p className={styles.error}>{error}</p> : null}
      </form>

      <div className={styles.results}>
        {result ? (
          <Results plan={result.plan} comparison={result.comparison} />
        ) : (
          <div className={styles.empty}>
            <div>
              <div className={styles.emptyIcon}><IconChart size={40} /></div>
              <p>{c.plan.empty}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className={styles.field}>
      <span className={styles.label}>{label}</span>
      {children}
    </label>
  );
}

export function SectorSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const { sector } = useFinanceLang();
  return (
    <select className={styles.select} value={value} onChange={(e) => onChange(e.target.value)}>
      {SECTORS.map((s) => (
        <option key={s.id} value={s.id}>
          {sector(s.id)}
          {s.preferentialSector ? " ★" : ""}
        </option>
      ))}
    </select>
  );
}

export function LocationSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const { city } = useFinanceLang();
  return (
    <select className={styles.select} value={value} onChange={(e) => onChange(e.target.value)}>
      {LOCATIONS.map((l) => (
        <option key={l.id} value={l.id}>
          {city(l.id)}
        </option>
      ))}
    </select>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className={styles.metric}>
      <p className={styles.metricLabel}>{label}</p>
      <p className={styles.metricValue}>
        {value}
        {unit ? <span className={styles.metricUnit}>{unit}</span> : null}
      </p>
    </div>
  );
}

export function Results({
  plan,
  comparison,
}: {
  plan: BusinessPlanResult;
  comparison: LocationComparison;
}) {
  const { c, lang, m, mc, money, sector, city, fill } = useFinanceLang();
  const cheapest = plan.tax.cheapest;

  const best = comparison.plans.find((p) => p.location.id === comparison.bestLocationId)!;
  const other = comparison.plans.find((p) => p.location.id === comparison.otherLocationId)!;
  const summary = comparison.verdictDiffers
    ? fill(c.plan.compareDiffer, {
        bestCity: city(best.location.id),
        bestVerdict: mc(best.verdictCode).toLowerCase(),
        otherCity: city(other.location.id),
        otherVerdict: mc(other.verdictCode).toLowerCase(),
      })
    : fill(c.plan.compareSame, {
        bestCity: city(best.location.id),
        bestVerdict: mc(best.verdictCode).toLowerCase(),
      });

  const incentives = comparison.plans.flatMap((p) =>
    p.location.incentives.map((i) => ({ ...i, cityName: city(p.location.id) })),
  );

  return (
    <>
      <section className={`${styles.verdict} ${styles[`verdict--${plan.verdict}`]}`}>
        <div className={styles.verdictHead}>
          <span className={styles.verdictBadge}>{VERDICT_BADGE[plan.verdict]}</span>
          <div>
            <h2 className={styles.verdictTitle}>{mc(plan.verdictCode)}</h2>
            <p className={styles.verdictSub}>
              {/* The advisor chat never asks for a name, so it passes a placeholder. */}
              {[plan.businessName, sector(plan.sector.id), city(plan.location.id)]
                .filter((part) => part && part !== "—")
                .join(" · ")}
            </p>
          </div>
        </div>
        <ul className={styles.reasons}>
          {plan.verdictReasons.map((r) => (
            <li key={r.code}>{m({ ...r, params: formatParams(r.params, money) })}</li>
          ))}
        </ul>
        <div style={{ marginTop: "0.875rem" }}>
          <AdviceButton summary={summarizePlan(plan, comparison)} />
        </div>
      </section>

      <div className={styles.metrics}>
        <Metric label={c.plan.m.breakEven} value={money(plan.breakEvenRevenueSom)} unit={c.perMonth} />
        <Metric label={c.plan.m.daily} value={String(plan.breakEvenCustomersPerDay)} unit={c.people} />
        <Metric label={c.plan.m.profit} value={money(plan.monthlyNetProfitSom)} unit={c.currency} />
        <Metric
          label={c.plan.m.payback}
          value={plan.paybackMonths != null ? String(plan.paybackMonths) : "—"}
          unit={plan.paybackMonths != null ? c.months : undefined}
        />
        <Metric label={c.plan.m.util} value={`${plan.utilisationPct}`} unit="%" />
        <Metric label={c.plan.m.fixed} value={money(plan.monthlyFixedCostsSom)} unit={c.perMonth} />
      </div>

      <section className={styles.card}>
        <h3 className={styles.sectionTitle}><IconPin size={16} /> {c.plan.compareTitle}</h3>
        <p className={styles.compareSummary}>{summary}</p>
        <div className={styles.compareGrid}>
          {comparison.plans.map((p) => (
            <div
              key={p.location.id}
              className={styles.compareCard}
              data-best={p.location.id === comparison.bestLocationId}
            >
              <p className={styles.compareCity}>
                {city(p.location.id)}
                {p.location.id === comparison.bestLocationId ? (
                  <span className={styles.bestTag}>{c.plan.best}</span>
                ) : null}
              </p>
              <p className={styles.compareVerdict}>
                {VERDICT_ICON[p.verdict]} {mc(p.verdictCode)}
              </p>
              <Row label={c.plan.cmp.breakEven} value={`${money(p.breakEvenRevenueSom)} ${c.currency}`} />
              <Row label={c.plan.cmp.daily} value={`${p.breakEvenCustomersPerDay}`} />
              <Row label={c.plan.cmp.profit} value={`${money(p.monthlyNetProfitSom)} ${c.currency}`} />
              <Row
                label={c.plan.cmp.payback}
                value={
                  p.paybackMonths != null
                    ? `${p.paybackMonths} ${c.months}`
                    : c.plan.cmp.noPayback
                }
              />
              <Row
                label={c.plan.cmp.salary}
                value={`${money(p.location.avgMonthlySalarySom)} ${c.currency}`}
              />
            </div>
          ))}
        </div>

        {incentives.map((i) => (
          <div key={`${i.cityName}-${i.code}`} className={styles.incentive}>
            <div className={styles.incentiveTitle}>
              <IconGift size={15} /> {i.cityName}: {i.text[lang].title}
              {!i.verified ? <span className={styles.unverified}>{c.unverified}</span> : null}
            </div>
            <div>{i.text[lang].detail}</div>
          </div>
        ))}
      </section>

      <section className={styles.card}>
        <h3 className={styles.sectionTitle}><IconReceipt size={16} /> {c.plan.taxTitle}</h3>
        <div className={styles.taxTable}>
          {plan.tax.results.map((r) => (
            <div
              key={r.regime}
              className={styles.taxRow}
              data-cheapest={cheapest?.regime === r.regime}
              data-eligible={r.eligible}
            >
              <span>
                {mc(`regime.${r.regime}`)}
                {!r.eligible && r.ineligibleCode ? ` — ${mc(r.ineligibleCode)}` : ""}
              </span>
              <span className={styles.taxAmount}>
                {money(r.annualTaxSom)} {c.perYear}
              </span>
            </div>
          ))}
        </div>
        {cheapest && plan.tax.savingsVsWorstSom > 0 ? (
          <p className={styles.compareSummary} style={{ marginTop: "1rem", marginBottom: 0 }}>
            {fill(c.plan.taxBest, {
              regime: mc(`regime.${cheapest.regime}`),
              amount: money(plan.tax.savingsVsWorstSom),
            })}
          </p>
        ) : null}
        <p className={styles.disclaimer}>{c.tax.engineDisclaimer}</p>
      </section>

      {plan.recommendations.length > 0 ? (
        <section className={styles.card}>
          <h3 className={styles.sectionTitle}><IconBulb size={16} /> {c.plan.recTitle}</h3>
          <ul className={styles.list}>
            {plan.recommendations.map((r) => (
              <li key={r.code}>
                {m({
                  ...r,
                  params: r.params
                    ? {
                        ...formatParams(r.params, money),
                        ...(typeof r.params.regime === "string"
                          ? { regime: mc(r.params.regime) }
                          : {}),
                      }
                    : undefined,
                })}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className={styles.card}>
        <h3 className={styles.sectionTitle}><IconSliders size={16} /> {c.plan.assumeTitle}</h3>
        <div className={styles.assumptions}>
          {plan.assumptions.map((a) => (
            <div key={a.key} className={styles.assumption}>
              <span>
                {mc(a.labelCode, a.labelParams ? { city: city(String(a.labelParams.city)) } : undefined)}
              </span>
              <span>
                {a.valueSom != null ? `${money(a.valueSom)} ${c.currency}` : a.valueText}
              </span>
            </div>
          ))}
        </div>
        <p className={styles.disclaimer}>{c.plan.assumeNote}</p>
      </section>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.compareRow}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

/** Money-like params are locale-formatted before substitution. */
function formatParams(
  params: Record<string, string | number> | undefined,
  money: (n: number) => string,
): Record<string, string | number> | undefined {
  if (!params) return undefined;
  const moneyKeys = new Set(["amount", "check"]);
  const out: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(params)) {
    out[k] = moneyKeys.has(k) && typeof v === "number" ? money(v) : v;
  }
  return out;
}
