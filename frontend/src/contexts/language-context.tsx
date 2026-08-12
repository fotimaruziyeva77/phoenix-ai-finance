"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { Lang, translations } from "@/i18n/translations";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TResult = string | string[] | Record<string, unknown>;

type LanguageContextValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  /** Resolve a dot-path key against the current language's translations.
   *
   *  Examples:
   *    t("nav.features")        → "Features"
   *    t("pricing.plans.pro.name") → "Pro"
   *    t("faq.items.0.q")       → "What does BotForge AI do?"
   */
  t: (path: string) => TResult;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "bf_lang";
const SUPPORTED_LANGS: Lang[] = ["en", "uz", "ru"];

function isSupportedLang(v: unknown): v is Lang {
  return typeof v === "string" && (SUPPORTED_LANGS as string[]).includes(v);
}

/** Detect the best language from the browser's navigator.language list. */
function detectBrowserLang(): Lang {
  // Uzbek is the product's primary market, so it is the fallback rather than English.
  if (typeof window === "undefined") return "uz";
  const preferred = (navigator.languages ?? [navigator.language])
    .map((l) => l.split("-")[0])
    .find(isSupportedLang);
  return preferred ?? "uz";
}

/** Walk a dot-path (with numeric array indices) into an object. */
function resolvePath(obj: unknown, parts: string[]): TResult {
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || current === undefined) return "";
    if (Array.isArray(current)) {
      const idx = Number(part);
      current = Number.isFinite(idx) ? current[idx] : undefined;
    } else if (typeof current === "object") {
      current = (current as Record<string, unknown>)[part];
    } else {
      return "";
    }
  }
  if (typeof current === "string") return current;
  if (Array.isArray(current)) return current as string[];
  if (typeof current === "object" && current !== null)
    return current as Record<string, unknown>;
  return String(current ?? "");
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const LanguageContext = createContext<LanguageContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

type LanguageProviderProps = {
  children: React.ReactNode;
  /** Override the initial lang (useful for server-side rendering hints). */
  initialLang?: Lang;
};

export function LanguageProvider({
  children,
  initialLang,
}: LanguageProviderProps) {
  // Uzbek is the product's primary market, so the server renders Uzbek and the
  // first client render matches it. Anything else is applied after mount from
  // localStorage — keeping SSR and hydration in agreement for most visitors.
  const [lang, setLangState] = useState<Lang>(initialLang ?? "uz");

  // Hydrate from localStorage (or browser language) after mount.
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (isSupportedLang(stored)) {
      setLangState(stored);
    } else {
      const detected = detectBrowserLang();
      setLangState(detected);
      localStorage.setItem(STORAGE_KEY, detected);
    }
  }, []);

  const setLang = useCallback((next: Lang) => {
    if (!isSupportedLang(next)) return;
    setLangState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const t = useCallback(
    (path: string): TResult => {
      const parts = path.split(".");
      const dict = translations[lang];
      const result = resolvePath(dict, parts);

      // Fallback to English if the key is missing in the current language.
      if (
        lang !== "en" &&
        (result === "" || result === undefined || result === null)
      ) {
        return resolvePath(translations["en"], parts);
      }

      return result;
    },
    [lang],
  );

  const value: LanguageContextValue = { lang, setLang, t };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used inside <LanguageProvider>.");
  }
  return ctx;
}

/** Alias for useLanguage. */
export const useLang = useLanguage;
