/**
 * Conversational advisor logic — intent detection and slot filling.
 *
 * This mirrors the backend sales pipeline (`app/services/intent_classifier_service.py`
 * → `question_planner.py` → `conversation_state_machine.py`): classify what the user
 * wants, ask for exactly one missing field per turn, then hand the completed slots to
 * the deterministic calculators.
 *
 * **No language model is involved.** Every number the advisor reports comes from
 * `engine.ts`, the same code the calculator pages use. A model can later be layered
 * on top to phrase the explanation — it must never compute the figures.
 */

import { SECTORS } from "./engine";

export type AdvisorIntent = "plan" | "credit" | "tax" | "benefits" | "unknown";

export type SlotId =
  | "sectorId"
  | "locationId"
  | "capital"
  | "employees"
  | "rent"
  | "principal"
  | "months"
  | "rate"
  | "revenue"
  | "age";

export type SlotKind = "number" | "sector" | "location";

export type SlotSpec = { id: SlotId; kind: SlotKind; promptCode: string };

/** Ordered per intent — the advisor always asks for the first unfilled slot. */
export const INTENT_SLOTS: Record<Exclude<AdvisorIntent, "unknown">, readonly SlotSpec[]> = {
  plan: [
    { id: "sectorId", kind: "sector", promptCode: "ask.sector" },
    { id: "locationId", kind: "location", promptCode: "ask.location" },
    { id: "capital", kind: "number", promptCode: "ask.capital" },
    { id: "employees", kind: "number", promptCode: "ask.employees" },
    { id: "rent", kind: "number", promptCode: "ask.rent" },
  ],
  credit: [
    { id: "principal", kind: "number", promptCode: "ask.principal" },
    { id: "months", kind: "number", promptCode: "ask.months" },
    { id: "rate", kind: "number", promptCode: "ask.rate" },
    { id: "revenue", kind: "number", promptCode: "ask.revenue" },
    { id: "age", kind: "number", promptCode: "ask.age" },
  ],
  benefits: [
    { id: "age", kind: "number", promptCode: "ask.age" },
    { id: "sectorId", kind: "sector", promptCode: "ask.sector" },
    { id: "principal", kind: "number", promptCode: "ask.principal" },
    { id: "months", kind: "number", promptCode: "ask.months" },
    { id: "rate", kind: "number", promptCode: "ask.rate" },
    { id: "revenue", kind: "number", promptCode: "ask.revenue" },
  ],
  tax: [
    { id: "revenue", kind: "number", promptCode: "ask.revenue" },
    { id: "sectorId", kind: "sector", promptCode: "ask.sector" },
    { id: "employees", kind: "number", promptCode: "ask.employees" },
  ],
};

const INTENT_KEYWORDS: Record<Exclude<AdvisorIntent, "unknown">, readonly string[]> = {
  plan: [
    "biznes", "reja", "foyda", "ochsam", "ochmoqchi", "zararsiz", "qoplan",
    "бизнес", "план", "прибыл", "открыть", "окуп", "безубыт",
    "business", "plan", "profit", "open", "break", "payback", "viable",
  ],
  credit: [
    "kredit", "qarz", "to'lov", "tolov", "foiz", "bank",
    "кредит", "заём", "займ", "платёж", "платеж", "ставк", "банк",
    "credit", "loan", "payment", "rate", "bank", "borrow",
  ],
  tax: [
    "soliq", "qqs", "yatt", "aylanma", "rejim",
    "налог", "ндс", "ип", "оборот", "режим",
    "tax", "vat", "regime", "turnover",
  ],
  benefits: [
    "imtiyoz", "subsidiya", "dastur", "grant", "yoshlar",
    "льгот", "субсиди", "программ", "грант", "молод",
    "benefit", "subsid", "programme", "program", "grant", "youth",
  ],
};

export function detectIntent(text: string): AdvisorIntent {
  const lower = text.toLowerCase();
  let best: AdvisorIntent = "unknown";
  let bestScore = 0;
  for (const [intent, words] of Object.entries(INTENT_KEYWORDS)) {
    const score = words.reduce((n, w) => (lower.includes(w) ? n + 1 : n), 0);
    if (score > bestScore) {
      bestScore = score;
      best = intent as AdvisorIntent;
    }
  }
  return best;
}

/**
 * Parse an amount, honouring "mln"/"млн"/"million" and "mlrd"/"млрд"/"billion"
 * suffixes — entrepreneurs type "200 mln", not "200000000".
 */
export function parseAmount(text: string): number | null {
  const cleaned = text.toLowerCase().replace(/\s+/g, " ");
  const match = cleaned.match(/(\d+(?:[.,]\d+)?)\s*(mlrd|млрд|billion|bln|mln|млн|million|ming|тыс|k)?/);
  if (!match) return null;
  const value = Number.parseFloat(match[1]!.replace(",", "."));
  if (!Number.isFinite(value)) return null;
  const suffix = match[2];
  if (!suffix) return Math.round(value);
  if (/mlrd|млрд|billion|bln/.test(suffix)) return Math.round(value * 1_000_000_000);
  if (/mln|млн|million/.test(suffix)) return Math.round(value * 1_000_000);
  if (/ming|тыс|k/.test(suffix)) return Math.round(value * 1_000);
  return Math.round(value);
}

const LOCATION_ALIASES: Record<string, string> = {
  toshkent: "toshkent", tashkent: "toshkent", ташкент: "toshkent",
  navoiy: "navoiy", navoi: "navoiy", навои: "navoiy", наво: "navoiy",
  samarqand: "samarqand", samarkand: "samarqand", самарканд: "samarqand",
  buxoro: "buxoro", bukhara: "buxoro", бухара: "buxoro",
};

export function parseLocation(text: string): string | null {
  const lower = text.toLowerCase();
  for (const [alias, id] of Object.entries(LOCATION_ALIASES)) {
    if (lower.includes(alias)) return id;
  }
  return null;
}

const SECTOR_ALIASES: Record<string, readonly string[]> = {
  oziq_ovqat: ["oziq", "do'kon", "dokon", "produkt", "продукт", "магазин", "grocery", "shop", "store"],
  kafe: ["kafe", "oshxona", "restoran", "кафе", "столов", "ресторан", "cafe", "restaurant"],
  nonvoyxona: ["non", "nonvoy", "пекарн", "хлеб", "bakery", "bread"],
  kiyim: ["kiyim", "одежд", "clothing", "clothes", "fashion"],
  gozallik: ["go'zallik", "gozallik", "salon", "красот", "beauty", "barber"],
  avtoservis: ["avtoservis", "avto", "автосервис", "auto", "car service"],
  chorvachilik: ["chorva", "mol", "животновод", "livestock", "cattle"],
  parrandachilik: ["parranda", "tovuq", "птицевод", "кур", "poultry", "chicken"],
  it_xizmat: ["it ", "dasturiy", "raqamli", "айти", "цифров", "software", "digital"],
  yuk_tashish: ["yuk", "dostavka", "tashish", "грузо", "доставк", "delivery", "logistics"],
};

export function parseSector(text: string): string | null {
  const lower = text.toLowerCase();
  for (const [id, aliases] of Object.entries(SECTOR_ALIASES)) {
    if (aliases.some((a) => lower.includes(a))) return id;
  }
  return SECTORS.find((s) => lower.includes(s.id))?.id ?? null;
}

export type Slots = Partial<Record<SlotId, number | string>>;

/** Pull whatever the message offers into the slot bag, without overwriting. */
export function harvestSlots(text: string, slots: Slots): Slots {
  const next: Slots = { ...slots };
  const sector = parseSector(text);
  if (sector && next.sectorId == null) next.sectorId = sector;
  const location = parseLocation(text);
  if (location && next.locationId == null) next.locationId = location;
  return next;
}

export function nextMissingSlot(
  intent: Exclude<AdvisorIntent, "unknown">,
  slots: Slots,
): SlotSpec | null {
  return INTENT_SLOTS[intent].find((s) => slots[s.id] == null) ?? null;
}
