import type { ReactNode } from "react";

import styles from "./dashboard-content-lead.module.css";

type Props = {
  children: ReactNode;
};

/** Neutral copy block for section pages — no metrics or mock data. */
export function DashboardContentLead({ children }: Props) {
  return <p className={styles.lead}>{children}</p>;
}
