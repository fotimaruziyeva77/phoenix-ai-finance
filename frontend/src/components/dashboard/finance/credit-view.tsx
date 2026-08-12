"use client";

import { useState, type FormEvent } from "react";

import {
  IconAlertTriangle,
  IconBank,
  IconCheckCircle,
  IconCoins,
  IconGift,
  IconXCircle,
} from "@/components/ui/icons";
import { AdviceButton } from "@/components/dashboard/finance/advice-modal";
import { useFinanceLang } from "@/hooks/useFinanceLang";
import { summarizeCredit } from "@/lib/finance/advice-summaries";
import {
  SECTORS,
  calculateCredit,
  evaluateCreditLoad,
  type CreditLoad,
  type CreditResult,
} from "@/lib/finance/engine";
import { BANK_OFFERS, matchPrograms, typicalMarketRate, type Program } from "@/lib/finance/programs";

import styles from "./credit-view.module.css";

type FormState = {
  principal: string;
  months: string;
  ratePct: string;
  monthlyRevenue: string;
  ownerAge: string;
  sectorId: string;
  hasPriorMicroloan: boolean;
  hasCollateral: boolean;
};

const INITIAL: FormState = {
  principal: "200000000",
  months: "36",
  ratePct: "28",
  monthlyRevenue: "35000000",
  ownerAge: "26",
  sectorId: SECTORS[0]!.id,
  hasPriorMicroloan: false,
  hasCollateral: false,
};

const toInt = (v: string) => {
  const n = Number.parseInt(v.replace(/\s/g, ""), 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
};
const toNum = (v: string) => {
  const n = Number.parseFloat(v.replace(",", "."));
  return Number.isFinite(n) && n >= 0 ? n : 0;
};

type Computed = {
  base: CreditResult;
  load: CreditLoad | null;
  programs: readonly Program[];
  bestProgram: { program: Program; result: CreditResult; savings: number } | null;
  enteredRate: number;
};

export function CreditView() {
  const { c } = useFinanceLang();
  const [form, setForm] = useState<FormState>(INITIAL);
  const [error, setError] = useState<string | null>(null);
  const [out, setOut] = useState<Computed | null>(null);

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm((p) => ({ ...p, [k]: v }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const principal = toInt(form.principal);
    const months = toInt(form.months);
    const ratePct = toNum(form.ratePct);
    if (principal <= 0 || months <= 0) {
      setError(c.credit.invalid);
      return;
    }
    try {
      setOut(
        computeCredit({
          principal,
          months,
          ratePct,
          monthlyRevenue: toInt(form.monthlyRevenue),
          ownerAge: toInt(form.ownerAge),
          sectorId: form.sectorId,
          hasPriorMicroloan: form.hasPriorMicroloan,
          hasCollateral: form.hasCollateral,
        }),
      );
      setError(null);
    } catch {
      setError(c.credit.invalid);
      setOut(null);
    }
  };

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h2 className={styles.formTitle}>{c.credit.formTitle}</h2>
        <p className={styles.formHint}>{c.credit.formHint}</p>

        <label className={styles.field}>
          <span className={styles.label}>{c.credit.f.principal}</span>
          <input className={styles.input} inputMode="numeric" value={form.principal} onChange={(e) => set("principal", e.target.value)} />
        </label>

        <div className={styles.row}>
          <label className={styles.field}>
            <span className={styles.label}>{c.credit.f.months}</span>
            <input className={styles.input} inputMode="numeric" value={form.months} onChange={(e) => set("months", e.target.value)} />
          </label>
          <label className={styles.field}>
            <span className={styles.label}>{c.credit.f.rate}</span>
            <input className={styles.input} inputMode="decimal" value={form.ratePct} onChange={(e) => set("ratePct", e.target.value)} />
          </label>
        </div>

        <label className={styles.field}>
          <span className={styles.label}>{c.credit.f.revenue}</span>
          <input className={styles.input} inputMode="numeric" value={form.monthlyRevenue} onChange={(e) => set("monthlyRevenue", e.target.value)} />
        </label>

        <div className={styles.row}>
          <label className={styles.field}>
            <span className={styles.label}>{c.credit.f.age}</span>
            <input className={styles.input} inputMode="numeric" value={form.ownerAge} onChange={(e) => set("ownerAge", e.target.value)} />
          </label>
          <label className={styles.field}>
            <span className={styles.label}>{c.credit.f.sector}</span>
            <SectorOptions value={form.sectorId} onChange={(v) => set("sectorId", v)} />
          </label>
        </div>

        <label className={styles.checkbox}>
          <input type="checkbox" checked={form.hasPriorMicroloan} onChange={(e) => set("hasPriorMicroloan", e.target.checked)} />
          {c.credit.f.priorLoan}
        </label>
        <label className={styles.checkbox}>
          <input type="checkbox" checked={form.hasCollateral} onChange={(e) => set("hasCollateral", e.target.checked)} />
          {c.credit.f.collateral}
        </label>

        <button type="submit" className={styles.submit}>
          {c.credit.submit}
        </button>

        {error ? <p className={styles.error}>{error}</p> : null}
      </form>

      <div className={styles.results}>
        {out ? (
          <CreditResults {...out} />
        ) : (
          <div className={styles.empty}>
            <div>
              <div className={styles.emptyIcon}><IconCoins size={40} /></div>
              <p>{c.credit.empty}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SectorOptions({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { sector } = useFinanceLang();
  return (
    <select className={styles.select} value={value} onChange={(e) => onChange(e.target.value)}>
      {SECTORS.map((s) => (
        <option key={s.id} value={s.id}>
          {sector(s.id)}
        </option>
      ))}
    </select>
  );
}

/** Shared by the page and the advisor chat so both produce identical numbers. */
export function computeCredit(input: {
  principal: number;
  months: number;
  ratePct: number;
  monthlyRevenue: number;
  ownerAge: number;
  sectorId: string;
  hasPriorMicroloan: boolean;
  hasCollateral: boolean;
}): Computed {
  const base = calculateCredit({
    principalSom: input.principal,
    annualRatePct: input.ratePct,
    months: input.months,
  });
  const load =
    input.monthlyRevenue > 0
      ? evaluateCreditLoad(base.monthlyPaymentSom, input.monthlyRevenue)
      : null;

  const programs = matchPrograms({
    ownerAge: input.ownerAge,
    sectorId: input.sectorId,
    hasPriorMicroloan: input.hasPriorMicroloan,
    hasCollateral: input.hasCollateral,
    annualRevenueSom: input.monthlyRevenue * 12,
  });

  const rateCutting = programs.filter(
    (p): p is Program & { ratePct: number } => p.ratePct != null && p.ratePct < input.ratePct,
  );
  const bestProgram = rateCutting.length
    ? (() => {
        const winner = rateCutting.reduce((a, b) => (b.ratePct < a.ratePct ? b : a));
        const result = calculateCredit({
          principalSom: input.principal,
          annualRatePct: winner.ratePct,
          months: input.months,
        });
        return { program: winner, result, savings: base.totalPaymentSom - result.totalPaymentSom };
      })()
    : null;

  return { base, load, programs, bestProgram, enteredRate: input.ratePct };
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

export function CreditResults({ base, load, programs, bestProgram, enteredRate }: Computed) {
  const { c, lang, mc, money, fill } = useFinanceLang();
  const marketMax = typicalMarketRate();

  return (
    <>
      {bestProgram ? (
        <section className={styles.headline}>
          <p className={styles.headlineLabel}>{c.credit.headlineLabel}</p>
          <p className={styles.headlineValue}>
            {money(bestProgram.savings)} {c.currency}
          </p>
          <p className={styles.headlineCaption}>
            {fill(c.credit.headlineCaption, {
              program: bestProgram.program.text[lang].title,
              rate: bestProgram.program.ratePct ?? 0,
              entered: enteredRate,
              before: money(base.monthlyPaymentSom),
              after: money(bestProgram.result.monthlyPaymentSom),
            })}
          </p>
        </section>
      ) : null}

      {load ? (
        <div className={`${styles.load} ${styles[`load--${load.level}`]}`}>
          {load.level === "danger" ? (
            <IconXCircle size={16} style={{ color: "#f87171" }} />
          ) : load.level === "warning" ? (
            <IconAlertTriangle size={16} style={{ color: "#fbbf24" }} />
          ) : (
            <IconCheckCircle size={16} style={{ color: "#4ade80" }} />
          )}{" "}
          {mc(load.code, { pct: load.loadPct })}
        </div>
      ) : null}

      <div className={styles.metrics}>
        <Metric label={c.credit.m.monthly} value={money(base.monthlyPaymentSom)} unit={c.currency} />
        <Metric label={c.credit.m.total} value={money(base.totalPaymentSom)} unit={c.currency} />
        <Metric label={c.credit.m.interest} value={money(base.totalInterestSom)} unit={c.currency} />
        <Metric label={c.credit.m.overpay} value={`${base.overpaymentPct}`} unit="%" />
      </div>

      <div>
        <AdviceButton summary={summarizeCredit({ base, load, programs, bestProgram, enteredRate })} />
      </div>

      <section className={styles.card}>
        <h3 className={styles.sectionTitle}><IconGift size={16} /> {c.credit.programsTitle}</h3>
        <p className={styles.sectionHint}>{c.credit.programsHint}</p>
        {programs.length === 0 ? (
          <p className={styles.noMatch}>{c.credit.noPrograms}</p>
        ) : (
          programs.map((p) => (
            <article
              key={p.code}
              className={styles.program}
              data-best={bestProgram?.program.code === p.code}
            >
              <div className={styles.programHead}>
                <h4 className={styles.programTitle}>
                  {p.text[lang].title}
                  {!p.verified ? <span className={styles.badge}>{c.unverified}</span> : null}
                </h4>
                {p.ratePct != null ? <span className={styles.programRate}>{p.ratePct}%</span> : null}
              </div>
              <p className={styles.programMeta}>{p.text[lang].terms}</p>
              <p className={styles.programMeta}>
                <strong>{c.credit.forWhom}:</strong> {p.text[lang].criteria}
              </p>
              {bestProgram?.program.code === p.code ? (
                <p className={styles.programSaving}>
                  {c.credit.saving}: {money(bestProgram.savings)} {c.currency}
                </p>
              ) : null}
              <p className={styles.source}>
                {c.credit.source}: {p.source} ·{" "}
                <a href={p.sourceUrl} target="_blank" rel="noreferrer noopener">
                  {c.credit.link}
                </a>
              </p>
            </article>
          ))
        )}
      </section>

      <section className={styles.card}>
        <h3 className={styles.sectionTitle}><IconBank size={16} /> {c.credit.banksTitle}</h3>
        <p className={styles.sectionHint}>{c.credit.banksHint}</p>
        <div className={styles.bankHeader}>
          <span>{c.credit.th.bank}</span>
          <span>{c.credit.th.rate}</span>
          <span>{c.credit.th.term}</span>
          <span>{c.credit.th.max}</span>
        </div>
        <div className={styles.bankTable}>
          {BANK_OFFERS.map((b, i) => (
            <div
              key={b.bank}
              className={styles.bankRow}
              data-cheapest={i === 0}
              data-expensive={b.ratePct === marketMax}
            >
              <span className={styles.bankName}>{b.bank}</span>
              <span className={styles.bankRate}>
                {b.ratePct != null
                  ? b.rateMaxPct
                    ? `${b.ratePct}–${b.rateMaxPct}%`
                    : `${b.ratePct}%`
                  : "—"}
              </span>
              <span className={styles.bankMeta}>
                {b.termYears != null ? `${b.termYears} ${c.credit.years}` : "—"}
              </span>
              <span className={styles.bankMeta}>{b.maxAmountLabel}</span>
            </div>
          ))}
        </div>
        <p className={styles.disclaimer}>{c.credit.banksNote}</p>
      </section>
    </>
  );
}
