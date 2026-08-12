"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { PhoenixLogo } from "@/components/layout/phoenix-logo";
import { useFinanceLang } from "@/hooks/useFinanceLang";
import {
  detectIntent,
  harvestSlots,
  nextMissingSlot,
  parseAmount,
  parseLocation,
  parseSector,
  type AdvisorIntent,
  type Slots,
} from "@/lib/finance/advisor";
import {
  DEMO_COMPARISON_PAIR,
  buildBusinessPlan,
  compareLocations,
  type BusinessPlanResult,
  type LocationComparison,
  type TaxComparison,
} from "@/lib/finance/engine";

import { Results } from "./business-plan-view";
import { CreditResults, computeCredit } from "./credit-view";
import styles from "./advisor-chat.module.css";
import { TaxResults, computeTax } from "./tax-view";

type Turn =
  | { role: "bot" | "user"; kind: "text"; text: string }
  | { role: "bot"; kind: "plan"; plan: BusinessPlanResult; comparison: LocationComparison }
  | { role: "bot"; kind: "credit"; credit: ReturnType<typeof computeCredit> }
  | { role: "bot"; kind: "tax"; tax: TaxComparison };

type Session = {
  intent: Exclude<AdvisorIntent, "unknown"> | null;
  slots: Slots;
  awaiting: string | null;
};

const EMPTY_SESSION: Session = { intent: null, slots: {}, awaiting: null };

const START_CODE: Record<Exclude<AdvisorIntent, "unknown">, string> = {
  plan: "adv.startPlan",
  credit: "adv.startCredit",
  tax: "adv.startTax",
  benefits: "adv.startBenefits",
};

export function AdvisorChat() {
  const { c, mc } = useFinanceLang();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [session, setSession] = useState<Session>(EMPTY_SESSION);
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  // Greeting is language-aware, so it is seeded on mount and reset on restart.
  useEffect(() => {
    setTurns([{ role: "bot", kind: "text", text: c.chat.greeting }]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [c.chat.greeting]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  const push = (...items: Turn[]) => setTurns((prev) => [...prev, ...items]);

  const handleUserText = (raw: string) => {
    const text = raw.trim();
    if (!text) return;
    push({ role: "user", kind: "text", text });
    setDraft("");

    let { intent, slots, awaiting } = session;

    // Fill the slot we are waiting on before anything else.
    if (awaiting) {
      const spec = intent ? nextMissingSlot(intent, slots) : null;
      const kind = spec?.kind ?? "number";
      let value: number | string | null = null;
      if (kind === "sector") value = parseSector(text);
      else if (kind === "location") value = parseLocation(text);
      else value = parseAmount(text);

      if (value == null) {
        push({ role: "bot", kind: "text", text: mc("adv.notNumber") });
        return;
      }
      slots = { ...slots, [awaiting]: value };
      awaiting = null;
    }

    if (!intent) {
      const detected = detectIntent(text);
      if (detected === "unknown") {
        push({ role: "bot", kind: "text", text: mc("adv.unknown") });
        return;
      }
      intent = detected;
      slots = harvestSlots(text, slots);
      push({ role: "bot", kind: "text", text: mc(START_CODE[intent]) });
    } else {
      slots = harvestSlots(text, slots);
    }

    advance(intent, slots);
  };

  const advance = (intent: Exclude<AdvisorIntent, "unknown">, slots: Slots) => {
    const missing = nextMissingSlot(intent, slots);
    if (missing) {
      setSession({ intent, slots, awaiting: missing.id });
      push({ role: "bot", kind: "text", text: mc(missing.promptCode) });
      return;
    }

    setSession({ intent, slots, awaiting: null });
    push({ role: "bot", kind: "text", text: mc("adv.ready") });

    const n = (id: keyof Slots) => Number(slots[id] ?? 0);

    if (intent === "plan") {
      const input = {
        businessName: "—",
        sectorId: String(slots.sectorId),
        locationId: String(slots.locationId),
        initialCapitalSom: n("capital"),
        employeeCount: n("employees"),
        monthlyRentSom: n("rent"),
      };
      const compareIds = Array.from(new Set([input.locationId, ...DEMO_COMPARISON_PAIR]));
      const plan = buildBusinessPlan(input);
      const comparison = compareLocations(input, compareIds);
      push({ role: "bot", kind: "plan", plan, comparison });
      return;
    }

    if (intent === "credit" || intent === "benefits") {
      const credit = computeCredit({
        principal: n("principal"),
        months: n("months"),
        ratePct: n("rate"),
        monthlyRevenue: n("revenue"),
        ownerAge: n("age"),
        sectorId: String(slots.sectorId ?? "oziq_ovqat"),
        hasPriorMicroloan: false,
        hasCollateral: false,
      });
      push({ role: "bot", kind: "credit", credit });
      return;
    }

    const tax = computeTax({
      monthlyRevenue: n("revenue"),
      sectorId: String(slots.sectorId),
      employeeCount: n("employees"),
      avgSalary: 4_500_000,
      monthlyRent: 0,
      isIndividual: true,
    });
    if (tax) {
      push({ role: "bot", kind: "tax", tax });
    }
  };

  const restart = () => {
    setSession(EMPTY_SESSION);
    setTurns([{ role: "bot", kind: "text", text: c.chat.greeting }]);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    handleUserText(draft);
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.stream}>
        {turns.map((turn, i) => (
          <div
            key={i}
            className={`${styles.turn} ${turn.role === "user" ? styles.turnUser : styles.turnBot}`}
          >
            {turn.role === "bot" ? (
              <span className={styles.avatar}>
                <PhoenixLogo markOnly style={{ width: "1.05rem", height: "1.05rem" }} />
              </span>
            ) : null}
            <div className={turn.kind === "text" ? styles.bubble : styles.resultCard}>
              {turn.kind === "text" ? (
                turn.text
              ) : turn.kind === "plan" ? (
                <Results plan={turn.plan} comparison={turn.comparison} />
              ) : turn.kind === "credit" ? (
                <CreditResults {...turn.credit} />
              ) : (
                <TaxResults comparison={turn.tax} />
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {turns.length <= 1 ? (
        <div className={styles.suggestions}>
          {c.chat.suggestions.map((s) => (
            <button key={s} type="button" className={styles.chip} onClick={() => handleUserText(s)}>
              {s}
            </button>
          ))}
        </div>
      ) : null}

      <form className={styles.composer} onSubmit={onSubmit}>
        <input
          className={styles.input}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={c.chat.placeholder}
          aria-label={c.chat.placeholder}
        />
        <button type="submit" className={styles.send} disabled={!draft.trim()}>
          {c.chat.send}
        </button>
        <button type="button" className={styles.restart} onClick={restart}>
          {c.chat.restart}
        </button>
      </form>
    </div>
  );
}
