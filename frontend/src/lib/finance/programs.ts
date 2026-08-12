/**
 * Commercial bank offers and state preferential-credit programs.
 *
 * Data is hand-curated from public sources on 2026-08-12 and every record keeps
 * its `source` so the UI can cite it. This is *published information*, not a
 * recommendation or a partnership: the product compares openly available terms
 * and the entrepreneur chooses. Nothing here implies a relationship with any bank.
 *
 * Rates move constantly — `DATA_AS_OF` must be shown wherever these render.
 */

export type BankOffer = {
  bank: string;
  ratePct: number | null;
  /** Some listings publish a band rather than a single rate. */
  rateMaxPct?: number;
  termYears: number | null;
  maxAmountLabel: string;
  source: string;
};

/** Sorted cheapest-first; `null` rate means the listing did not publish one. */
export const BANK_OFFERS: readonly BankOffer[] = [
  { bank: "Xalq banki", ratePct: 4, termYears: 1, maxAmountLabel: "$1 mln", source: "bank.uz" },
  { bank: "Saderat Bank", ratePct: 11, rateMaxPct: 14, termYears: 5, maxAmountLabel: "—", source: "bank.uz" },
  { bank: "Sanoatqurilishbank", ratePct: 14, termYears: 3, maxAmountLabel: "$500 000", source: "bank.uz" },
  { bank: "KDB Bank Uzbekistan", ratePct: 18, rateMaxPct: 24, termYears: null, maxAmountLabel: "50 mlrd", source: "bank.uz" },
  { bank: "Aloqabank", ratePct: 19, termYears: 3, maxAmountLabel: "300 mln", source: "bank.uz" },
  { bank: "Kapitalbank (Solar)", ratePct: 21, termYears: 10, maxAmountLabel: "300 mln", source: "bank.uz" },
  { bank: "Asakabank", ratePct: 21, termYears: 3, maxAmountLabel: "$2 mln", source: "bank.uz" },
  { bank: "Asia Alliance Bank", ratePct: 23, termYears: 5, maxAmountLabel: "—", source: "bank.uz" },
  { bank: "Kapitalbank", ratePct: 24, termYears: 5, maxAmountLabel: "10 mlrd", source: "bank.uz" },
  { bank: "Ipak Yo'li Bank", ratePct: 24, termYears: 5, maxAmountLabel: "$1 mln", source: "bank.uz" },
  { bank: "Agrobank", ratePct: 26, termYears: null, maxAmountLabel: "50 mln", source: "bank.uz" },
  { bank: "Hamkorbank", ratePct: 28, termYears: 4, maxAmountLabel: "—", source: "bank.uz" },
];

/** Central Bank base rate — several programs are priced off it. */
export const CB_BASE_RATE_PCT = 14;

/**
 * Profile the eligibility engine matches programs against. Every field exists
 * because at least one real program keys off it.
 */
export type EligibilityProfile = {
  ownerAge: number;
  sectorId: string;
  hasPriorMicroloan: boolean;
  hasCollateral: boolean;
  annualRevenueSom: number;
};

export type ProgramText = { title: string; terms: string; criteria: string };

export type Program = {
  code: string;
  /** Localised name, terms and eligibility, keyed by language. */
  text: Record<"uz" | "ru" | "en", ProgramText>;
  /** Effective annual rate, or null when the benefit is not a rate cut. */
  ratePct: number | null;
  source: string;
  sourceUrl: string;
  /** false → show a "needs confirmation" badge; never fold into headline savings. */
  verified: boolean;
  matches: (p: EligibilityProfile) => boolean;
};

export const PROGRAMS: readonly Program[] = [
  {
    code: "yoshlar",
    ratePct: CB_BASE_RATE_PCT + 4,
    text: {
      uz: {
        title: "Yoshlar tadbirkorligi",
        terms: "7 yilgacha muddat · 1 yil imtiyozli davr (asosiy qarz to'lanmaydi) · Aloqabank",
        criteria: "31 yoshgacha bo'lgan tadbirkorlar",
      },
      ru: {
        title: "Молодёжное предпринимательство",
        terms: "До 7 лет · 1 год льготного периода (основной долг не платится) · Алокабанк",
        criteria: "Предприниматели до 31 года",
      },
      en: {
        title: "Youth entrepreneurship",
        terms: "Up to 7 years · 1-year grace period (no principal repaid) · Aloqabank",
        criteria: "Entrepreneurs under 31",
      },
    },
    source: "PQ-210, 01.06.2026",
    sourceUrl:
      "https://zamin.uz/en/uzbekistan/205335-preferential-loans-for-youth-business-and-education-launch.html",
    verified: true,
    matches: (p) => p.ownerAge < 31,
  },
  {
    code: "chorvachilik",
    ratePct: 10,
    text: {
      uz: {
        title: "Chorvachilik va «tayyor biznes» dasturi",
        terms: "10 yilgacha muddat · 4 yil imtiyozli davr · Mikrokreditbank",
        criteria: "Chorvachilik, yem ishlab chiqarish va parrandachilik sohalari",
      },
      ru: {
        title: "Программа животноводства и «готового бизнеса»",
        terms: "До 10 лет · 4 года льготного периода · Микрокредитбанк",
        criteria: "Животноводство, производство кормов и птицеводство",
      },
      en: {
        title: "Livestock and «ready business» programme",
        terms: "Up to 10 years · 4-year grace period · Mikrokreditbank",
        criteria: "Livestock, feed production and poultry sectors",
      },
    },
    source: "Tiklanish va taraqqiyot jamg'armasi, 2026",
    sourceUrl: "https://www.gazeta.uz/oz/2026/07/24/parrandachilik/",
    verified: true,
    matches: (p) => p.sectorId === "chorvachilik" || p.sectorId === "parrandachilik",
  },
  {
    code: "garovsiz",
    ratePct: null,
    text: {
      uz: {
        title: "Garovsiz qism oshirildi",
        terms: "Garovsiz kredit qismi 100 mln → 200 mln so'mga oshirildi",
        criteria: "Avval mikroqarz olgan va kredit tarixi toza tadbirkorlar",
      },
      ru: {
        title: "Увеличена беззалоговая часть",
        terms: "Беззалоговая часть кредита выросла со 100 млн до 200 млн сум",
        criteria: "Предприниматели с прошлым микрозаймом и чистой кредитной историей",
      },
      en: {
        title: "Unsecured portion raised",
        terms: "The unsecured part of a loan rose from 100 mln to 200 mln so'm",
        criteria: "Entrepreneurs with a prior microloan and a clean credit history",
      },
    },
    source: "01.07.2026",
    sourceUrl: "https://www.trend.az/business/4195344.html",
    verified: true,
    matches: (p) => p.hasPriorMicroloan && !p.hasCollateral,
  },
  {
    code: "foiz_subsidiya",
    ratePct: null,
    text: {
      uz: {
        title: "Foiz stavkasi subsidiyasi",
        terms: "Foiz stavkasining bir qismi qoplanadi · Tadbirkorlikni rivojlantirish kompaniyasi",
        criteria: "5 mlrd so'mgacha bo'lgan kreditlar",
      },
      ru: {
        title: "Субсидия процентной ставки",
        terms: "Часть процентной ставки компенсируется · Компания развития предпринимательства",
        criteria: "Кредиты до 5 млрд сум",
      },
      en: {
        title: "Interest-rate subsidy",
        terms: "Part of the interest rate is covered · Entrepreneurship Development Company",
        criteria: "Loans up to 5 bln so'm",
      },
    },
    source: "2026",
    sourceUrl: "https://www.trend.az/business/4195344.html",
    verified: true,
    matches: (p) => p.annualRevenueSom <= 5_000_000_000,
  },
  {
    code: "kafolat",
    ratePct: null,
    text: {
      uz: {
        title: "Kredit kafolati",
        terms: "Kredit summasining 75% gacha kafolat · 2.5 mlrd so'mdan oshmagan holda",
        criteria: "4–5 toifadagi tumanlarda faoliyat yurituvchi kichik biznes",
      },
      ru: {
        title: "Кредитная гарантия",
        terms: "Гарантия до 75% суммы кредита · не более 2,5 млрд сум",
        criteria: "Малый бизнес в районах 4–5 категории",
      },
      en: {
        title: "Loan guarantee",
        terms: "Up to 75% of the loan guaranteed · capped at 2.5 bln so'm",
        criteria: "Small business in category 4–5 districts",
      },
    },
    source: "Tuman toifalari tizimi — amal qilish muddati tekshirilishi kerak",
    sourceUrl:
      "https://www.tashkenttimes.uz/national/10316-uzbekistan-districts-and-cities-divided-into-5-categories-where-different-tax-incentives-and-subsidies-to-be-applied",
    verified: false,
    matches: (p) => !p.hasCollateral,
  },
  {
    code: "grant",
    ratePct: null,
    text: {
      uz: {
        title: "Raqamlashtirish granti",
        terms: "300 mln so'mgacha grant · raqamlashtirish va xalqaro standartlar uchun",
        criteria: "Yiliga eng yaxshi natija ko'rsatgan 100 tadbirkor",
      },
      ru: {
        title: "Грант на цифровизацию",
        terms: "Грант до 300 млн сум · на цифровизацию и международные стандарты",
        criteria: "100 предпринимателей с лучшими результатами в год",
      },
      en: {
        title: "Digitalisation grant",
        terms: "Grant up to 300 mln so'm · for digitalisation and international standards",
        criteria: "The 100 best-performing entrepreneurs each year",
      },
    },
    source: "2026",
    sourceUrl: "https://www.trend.az/business/4195344.html",
    verified: true,
    matches: () => true,
  },
];

export function matchPrograms(profile: EligibilityProfile): readonly Program[] {
  return PROGRAMS.filter((p) => p.matches(profile));
}

/** Cheapest published market rate — the baseline a preferential rate is measured against. */
export function cheapestMarketRate(): number {
  const rates = BANK_OFFERS.map((b) => b.ratePct).filter((r): r is number => r != null);
  return Math.min(...rates);
}

export function typicalMarketRate(): number {
  const rates = BANK_OFFERS.map((b) => b.ratePct).filter((r): r is number => r != null);
  return Math.max(...rates);
}
