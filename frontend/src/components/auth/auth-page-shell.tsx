"use client";

import type { ReactNode } from "react";

import styles from "./auth-shell.module.css";

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export function AuthPageShell({ title, subtitle, children }: Props) {
  return (
    <div className={styles.shell} suppressHydrationWarning>
      <div className={styles.card} suppressHydrationWarning>
        <h1 className={styles.title}>{title}</h1>
        {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
        {children}
      </div>
    </div>
  );
}
