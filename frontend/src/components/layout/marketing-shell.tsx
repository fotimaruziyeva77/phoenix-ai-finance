import type { ReactNode } from "react";

import { MarketingNavbar } from "./marketing-navbar";
import styles from "./marketing-shell.module.css";
import { SiteFooter } from "./site-footer";

type Props = {
  children: ReactNode;
};

export function MarketingShell({ children }: Props) {
  return (
    <div className={styles.shell}>
      <MarketingNavbar />
      <div className={styles.content}>{children}</div>
      <SiteFooter />
    </div>
  );
}
