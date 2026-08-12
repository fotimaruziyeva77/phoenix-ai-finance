"use client";

import Link from "next/link";

import { TOOL_ICONS, type ToolKey } from "@/components/dashboard/finance/tool-shell";
import { useAuth } from "@/hooks/useAuth";
import { useFinanceLang } from "@/hooks/useFinanceLang";

import styles from "./finance-home.module.css";

const TOOL_HREF: Record<ToolKey, string> = {
  chat: "/maslahatchi",
  plan: "/biznes-reja",
  credit: "/kredit",
  tax: "/soliq",
};

const TOOL_ORDER: readonly ToolKey[] = ["chat", "plan", "credit", "tax"];

/** Feature blurbs in the landing copy follow the same order as the tool grid. */
const FEAT_INDEX: Record<ToolKey, number> = { plan: 0, credit: 1, tax: 2, chat: 0 };

/**
 * Dashboard home for the finance-advisor product. The previous overview walked
 * the user through building a bot — the old positioning — so it now opens the
 * advisory tools instead.
 */
export function FinanceHome() {
  const { user } = useAuth();
  const { c } = useFinanceLang();
  const firstName = user?.full_name?.split(" ")[0] ?? user?.email ?? "";

  return (
    <div className={styles.wrap}>
      <header className={styles.head}>
        <h1 className={styles.title}>
          {firstName ? `Salom, ${firstName}` : "Xush kelibsiz"}
        </h1>
        <p className={styles.lead}>{c.landing.featSub}</p>
      </header>

      <div className={styles.grid}>
        {TOOL_ORDER.map((key) => {
          const Icon = TOOL_ICONS[key];
          const blurb =
            key === "chat" ? c.chat.subtitle : c.landing.feats[FEAT_INDEX[key]]!.text;
          return (
            <Link key={key} href={TOOL_HREF[key]} className={styles.card}>
              <span className={styles.cardIcon}>
                <Icon size={22} />
              </span>
              <span className={styles.cardTitle}>{c.tools[key]}</span>
              <span className={styles.cardText}>{blurb}</span>
            </Link>
          );
        })}
      </div>

      <p className={styles.note}>{c.landing.disclaimer}</p>
    </div>
  );
}
