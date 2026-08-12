/** Format ISO timestamps for dashboard tables (locale-aware). */
export function formatDashboardDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d);
}

/** Date-only (e.g. lead created). */
export function formatDashboardDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(d);
}

// Explicit Uzbek (Latin) month names: browser ICU data for `uz` is often incomplete,
// so toLocaleDateString("uz-UZ", …) falls back to the root locale and renders months
// as "M06" instead of "iyun". We format Uzbek dates ourselves to avoid that.
const UZ_MONTHS = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr",
] as const;

function langToLocale(lang: string): string {
  return lang === "uz" ? "uz-UZ" : lang === "ru" ? "ru-RU" : "en-US";
}

/** Language-aware date (e.g. "14-iyun, 2026"). Robust for Uzbek across browsers. */
export function formatLocalizedDate(iso: string | null | undefined, lang: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  if (lang === "uz") {
    return `${d.getDate()}-${UZ_MONTHS[d.getMonth()]}, ${d.getFullYear()}`;
  }
  return d.toLocaleDateString(langToLocale(lang), {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Language-aware date + time (e.g. "14-iyun, 2026, 12:46"). Robust for Uzbek. */
export function formatLocalizedDateTime(iso: string | null | undefined, lang: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  if (lang === "uz") {
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${d.getDate()}-${UZ_MONTHS[d.getMonth()]}, ${d.getFullYear()}, ${hh}:${mm}`;
  }
  return d.toLocaleString(langToLocale(lang), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
