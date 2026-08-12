"use client";

import Link from "next/link";
import type { ComponentType, ReactNode } from "react";

import {
  IconAdvisor,
  IconChart,
  IconCoins,
  IconReceipt,
} from "@/components/ui/icons";
import { useFinanceLang } from "@/hooks/useFinanceLang";

import styles from "./tool-shell.module.css";

export type ToolKey = "plan" | "credit" | "tax" | "chat";

const TOOL_HREF: Record<ToolKey, string> = {
  plan: "/biznes-reja",
  credit: "/kredit",
  tax: "/soliq",
  chat: "/maslahatchi",
};

export const TOOL_ICONS: Record<ToolKey, ComponentType<{ size?: number }>> = {
  plan: IconChart,
  credit: IconCoins,
  tax: IconReceipt,
  chat: IconAdvisor,
};

const TOOL_ORDER: readonly ToolKey[] = ["chat", "plan", "credit", "tax"];

type Props = {
  tool: ToolKey;
  title: string;
  subtitle: string;
  disclaimer: string;
  children: ReactNode;
};

/**
 * Chrome shared by every public advisory page: language-aware heading, the tool
 * switcher, and the mandatory disclaimer. Kept client-side so switching language
 * re-renders the copy without a round trip.
 */
export function ToolShell({ tool, title, subtitle, disclaimer, children }: Props) {
  const { c } = useFinanceLang();

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headText}>
          <p className={styles.eyebrow}>{c.free}</p>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>{subtitle}</p>
        </div>
        <Link href="/" className={styles.back}>
          {c.back}
        </Link>
      </header>

      <nav className={styles.tools} aria-label="Tools">
        {TOOL_ORDER.map((key) => {
          const Icon = TOOL_ICONS[key];
          return (
            <Link
              key={key}
              href={TOOL_HREF[key]}
              className={styles.tool}
              data-active={key === tool}
            >
              <Icon size={15} /> {c.tools[key]}
            </Link>
          );
        })}
      </nav>

      {children}

      <p className={styles.disclaimer}>{disclaimer}</p>
    </main>
  );
}
