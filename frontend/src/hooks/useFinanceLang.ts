"use client";

import { useLanguage } from "@/contexts/language-context";
import {
  asFinanceLang,
  copy,
  formatMoney,
  locationLabel,
  msg,
  sectorLabel,
  type FinanceCopy,
  type FinanceLang,
  type Msg,
} from "@/i18n/finance";

export type FinanceLangApi = {
  lang: FinanceLang;
  /** UI copy for the current language. */
  c: FinanceCopy;
  /** Render an engine message (`{ code, params }`). */
  m: (message: Msg) => string;
  /** Render a bare i18n code, optionally with params. */
  mc: (code: string, params?: Record<string, string | number>) => string;
  /** Locale-formatted so'm amount. */
  money: (value: number) => string;
  sector: (id: string) => string;
  city: (id: string) => string;
  /** Fill {placeholders} in a copy string. */
  fill: (template: string, params: Record<string, string | number>) => string;
};

/**
 * Single access point for finance-surface translations.
 *
 * The legacy `useLanguage()` covers the older dashboard bundle; this wraps it so
 * finance components never touch raw dictionaries or re-implement formatting.
 */
export function useFinanceLang(): FinanceLangApi {
  const { lang: rawLang } = useLanguage();
  const lang = asFinanceLang(rawLang);

  return {
    lang,
    c: copy(lang),
    m: (message) => msg(message, lang),
    mc: (code, params) => msg({ code, params }, lang),
    money: (value) => formatMoney(value, lang),
    sector: (id) => sectorLabel(id, lang),
    city: (id) => locationLabel(id, lang),
    fill: (template, params) =>
      template.replace(/\{(\w+)\}/g, (_, key: string) => String(params[key] ?? `{${key}}`)),
  };
}
