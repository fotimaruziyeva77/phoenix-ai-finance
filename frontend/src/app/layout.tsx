import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Golos_Text, JetBrains_Mono, Unbounded } from "next/font/google";

import { AppProviders } from "@/components/providers/app-providers";

import "./globals.css";

/**
 * Phoenix AI type system — all three faces ship Cyrillic, which the ru locale
 * needs and most display faces lack:
 *  - Unbounded: display voice (hero, section titles, verdicts). Wide and
 *    rounded; used sparingly at moderate sizes.
 *  - Golos Text: body voice — a Cyrillic-native grotesque that stays warm.
 *  - JetBrains Mono: the "calculator tape" voice for money figures.
 */
const display = Unbounded({
  subsets: ["latin", "cyrillic"],
  weight: ["500", "700"],
  variable: "--font-display",
  display: "swap",
});

const body = Golos_Text({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  weight: ["500", "700"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Phoenix AI — moliyaviy maslahatchi", template: "%s · Phoenix AI" },
  description:
    "Kichik tadbirkorlar uchun AI moliyaviy maslahatchi: biznes-reja, kredit, soliq va imtiyozlar.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html
      lang="uz"
      suppressHydrationWarning
      className={`${display.variable} ${body.variable} ${mono.variable}`}
    >
      <body suppressHydrationWarning>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
