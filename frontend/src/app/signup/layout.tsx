import type { Metadata } from "next";
import type { ReactNode } from "react";

import { MarketingShell } from "@/components/layout/marketing-shell";

export const metadata: Metadata = {
  title: "Sign up",
};

export default function SignupLayout({ children }: { children: ReactNode }) {
  return <MarketingShell>{children}</MarketingShell>;
}
