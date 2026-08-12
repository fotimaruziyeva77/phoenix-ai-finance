/**
 * Finance engine — client-side mirror of `app/lib/finance/` (Python).
 *
 * The Python modules are the production implementation. This port exists so the
 * advisory tools run with no backend, database, or AI dependency: the numbers an
 * entrepreneur sees are produced by arithmetic in the browser, deterministically.
 *
 * Any change to a rate, threshold, or verdict rule MUST be made in both places.
 * Sources for the 2026 figures are recorded in the Python modules.
 */

import type { Msg } from "@/i18n/finance";

export const DATA_AS_OF = "2026-08-12";

/* ------------------------------------------------------------------ sectors */

export type Sector = {
  id: string;
  labelUz: string;
  grossMarginPct: number;
  avgCheckSom: number;
  monthlyOtherCostsSom: number;
  monthlyRevenuePerEmployeeSom: number;
  preferentialSector: boolean;
};

export const SECTORS: readonly Sector[] = [
  { id: "oziq_ovqat", labelUz: "Oziq-ovqat do'koni", grossMarginPct: 18, avgCheckSom: 45_000, monthlyOtherCostsSom: 3_500_000, monthlyRevenuePerEmployeeSom: 90_000_000, preferentialSector: false },
  { id: "kafe", labelUz: "Kafe / oshxona", grossMarginPct: 35, avgCheckSom: 70_000, monthlyOtherCostsSom: 6_000_000, monthlyRevenuePerEmployeeSom: 55_000_000, preferentialSector: false },
  { id: "nonvoyxona", labelUz: "Nonvoyxona", grossMarginPct: 30, avgCheckSom: 25_000, monthlyOtherCostsSom: 5_000_000, monthlyRevenuePerEmployeeSom: 48_000_000, preferentialSector: false },
  { id: "kiyim", labelUz: "Kiyim do'koni", grossMarginPct: 40, avgCheckSom: 250_000, monthlyOtherCostsSom: 2_500_000, monthlyRevenuePerEmployeeSom: 60_000_000, preferentialSector: false },
  { id: "gozallik", labelUz: "Go'zallik saloni", grossMarginPct: 55, avgCheckSom: 120_000, monthlyOtherCostsSom: 3_000_000, monthlyRevenuePerEmployeeSom: 32_000_000, preferentialSector: false },
  { id: "avtoservis", labelUz: "Avtoservis", grossMarginPct: 45, avgCheckSom: 400_000, monthlyOtherCostsSom: 4_000_000, monthlyRevenuePerEmployeeSom: 45_000_000, preferentialSector: false },
  { id: "chorvachilik", labelUz: "Chorvachilik", grossMarginPct: 28, avgCheckSom: 2_500_000, monthlyOtherCostsSom: 4_500_000, monthlyRevenuePerEmployeeSom: 30_000_000, preferentialSector: true },
  { id: "parrandachilik", labelUz: "Parrandachilik", grossMarginPct: 25, avgCheckSom: 800_000, monthlyOtherCostsSom: 4_000_000, monthlyRevenuePerEmployeeSom: 35_000_000, preferentialSector: true },
  { id: "it_xizmat", labelUz: "IT / raqamli xizmat", grossMarginPct: 65, avgCheckSom: 3_000_000, monthlyOtherCostsSom: 2_000_000, monthlyRevenuePerEmployeeSom: 30_000_000, preferentialSector: false },
  { id: "yuk_tashish", labelUz: "Yuk tashish / dostavka", grossMarginPct: 32, avgCheckSom: 150_000, monthlyOtherCostsSom: 5_500_000, monthlyRevenuePerEmployeeSom: 40_000_000, preferentialSector: false },
];

export const getSector = (id: string) => SECTORS.find((s) => s.id === id);

/* ---------------------------------------------------------------- locations */

export type LocationIncentive = {
  code: string;
  /** Localised title and detail, keyed by language. */
  text: Record<"uz" | "ru" | "en", { title: string; detail: string }>;
  /** false → render with a "needs confirmation" badge, never sum into totals */
  verified: boolean;
};

export type BusinessLocation = {
  id: string;
  labelUz: string;
  regionUz: string;
  /** Planning assumption: typical small-business wage, not the national average. */
  avgMonthlySalarySom: number;
  utilitiesIndex: number;
  incentives: readonly LocationIncentive[];
};

export const LOCATIONS: readonly BusinessLocation[] = [
  {
    id: "toshkent",
    labelUz: "Toshkent shahri",
    regionUz: "Toshkent shahri",
    avgMonthlySalarySom: 4_500_000,
    utilitiesIndex: 1.15,
    incentives: [],
  },
  {
    id: "navoiy",
    labelUz: "Navoiy shahri",
    regionUz: "Navoiy viloyati",
    avgMonthlySalarySom: 3_400_000,
    utilitiesIndex: 0.9,
    incentives: [
      {
        code: "navoi_fez",
        text: {
          uz: {
            title: "Navoiy erkin iqtisodiy zonasi",
            detail:
              "Navoiyda erkin iqtisodiy zona faoliyat yuritadi. Rezident maqomini olgan loyihalar uchun soliq va bojxona imtiyozlari nazarda tutilgan. Shartlari loyiha turi va investitsiya hajmiga bog'liq.",
          },
          ru: {
            title: "Свободная экономическая зона Навои",
            detail:
              "В Навои действует свободная экономическая зона. Для проектов со статусом резидента предусмотрены налоговые и таможенные льготы. Условия зависят от типа проекта и объёма инвестиций.",
          },
          en: {
            title: "Navoi Free Economic Zone",
            detail:
              "Navoi hosts a free economic zone. Projects granted resident status receive tax and customs incentives. Terms depend on the project type and the investment amount.",
          },
        },
        verified: false,
      },
    ],
  },
  { id: "samarqand", labelUz: "Samarqand shahri", regionUz: "Samarqand viloyati", avgMonthlySalarySom: 3_600_000, utilitiesIndex: 0.95, incentives: [] },
  { id: "buxoro", labelUz: "Buxoro shahri", regionUz: "Buxoro viloyati", avgMonthlySalarySom: 3_400_000, utilitiesIndex: 0.92, incentives: [] },
];

export const getLocation = (id: string) => LOCATIONS.find((l) => l.id === id);

export const DEMO_COMPARISON_PAIR: readonly [string, string] = ["toshkent", "navoiy"];

/* --------------------------------------------------------------------- tax */

export const SELF_EMPLOYED_RATE_PCT = 1;
export const SELF_EMPLOYED_TURNOVER_CAP_SOM = 1_000_000_000;
export const TURNOVER_TAX_RATE_PCT = 4;
export const TURNOVER_TAX_CAP_SOM = 5_000_000_000;
export const VAT_RATE_PCT = 12;
export const PROFIT_TAX_RATE_PCT = 15;
export const SOCIAL_TAX_RATE_PCT = 12;

export type RegimeId = "self_employed" | "turnover" | "general";

export type RegimeResult = {
  regime: RegimeId;
  eligible: boolean;
  /** i18n code, or null when eligible. */
  ineligibleCode: string | null;
  annualTaxSom: number;
  monthlyTaxSom: number;
  effectiveRatePct: number;
  breakdown: readonly { code: string; amountSom: number }[];
};

export type TaxComparison = {
  annualRevenueSom: number;
  results: readonly RegimeResult[];
  cheapest: RegimeResult | null;
  savingsVsWorstSom: number;
};

export function calculateTaxRegimes(input: {
  annualRevenueSom: number;
  annualCostOfGoodsSom: number;
  annualPayrollSom: number;
  annualOtherCostsSom: number;
  isIndividualEntrepreneur?: boolean;
}): TaxComparison {
  const {
    annualRevenueSom,
    annualCostOfGoodsSom,
    annualPayrollSom,
    annualOtherCostsSom,
    isIndividualEntrepreneur = true,
  } = input;

  const socialTax = Math.round((annualPayrollSom * SOCIAL_TAX_RATE_PCT) / 100);
  const valueAdded = Math.max(annualRevenueSom - annualCostOfGoodsSom, 0);
  const operatingProfit = Math.max(
    annualRevenueSom - annualCostOfGoodsSom - annualPayrollSom - annualOtherCostsSom,
    0,
  );
  const rate = (total: number) =>
    annualRevenueSom > 0 ? Math.round((total / annualRevenueSom) * 10_000) / 100 : 0;

  const seEligible =
    isIndividualEntrepreneur && annualRevenueSom <= SELF_EMPLOYED_TURNOVER_CAP_SOM;
  const seTax = Math.round((annualRevenueSom * SELF_EMPLOYED_RATE_PCT) / 100);
  const seTotal = seTax + socialTax;

  const toEligible = annualRevenueSom <= TURNOVER_TAX_CAP_SOM;
  const toTax = Math.round((annualRevenueSom * TURNOVER_TAX_RATE_PCT) / 100);
  const toTotal = toTax + socialTax;

  const vat = Math.round((valueAdded * VAT_RATE_PCT) / 100);
  const profitTax = Math.round((operatingProfit * PROFIT_TAX_RATE_PCT) / 100);
  const generalTotal = vat + profitTax + socialTax;

  const results: RegimeResult[] = [
    {
      regime: "self_employed",
      eligible: seEligible,
      ineligibleCode: seEligible
        ? null
        : isIndividualEntrepreneur
          ? "regime.ineligible.overOneBillion"
          : "regime.ineligible.notIndividual",
      annualTaxSom: seTotal,
      monthlyTaxSom: Math.round(seTotal / 12),
      effectiveRatePct: rate(seTotal),
      breakdown: [
        { code: "tax.line.turnover1", amountSom: seTax },
        { code: "tax.line.social", amountSom: socialTax },
      ],
    },
    {
      regime: "turnover",
      eligible: toEligible,
      ineligibleCode: toEligible ? null : "regime.ineligible.overFiveBillion",
      annualTaxSom: toTotal,
      monthlyTaxSom: Math.round(toTotal / 12),
      effectiveRatePct: rate(toTotal),
      breakdown: [
        { code: "tax.line.turnover4", amountSom: toTax },
        { code: "tax.line.social", amountSom: socialTax },
      ],
    },
    {
      regime: "general",
      eligible: true,
      ineligibleCode: null,
      annualTaxSom: generalTotal,
      monthlyTaxSom: Math.round(generalTotal / 12),
      effectiveRatePct: rate(generalTotal),
      breakdown: [
        { code: "tax.line.vat", amountSom: vat },
        { code: "tax.line.profit", amountSom: profitTax },
        { code: "tax.line.social", amountSom: socialTax },
      ],
    },
  ];

  const eligible = results.filter((r) => r.eligible);
  const cheapest = eligible.length
    ? eligible.reduce((a, b) => (b.annualTaxSom < a.annualTaxSom ? b : a))
    : null;
  const worst = eligible.length
    ? eligible.reduce((a, b) => (b.annualTaxSom > a.annualTaxSom ? b : a))
    : null;

  return {
    annualRevenueSom,
    results,
    cheapest,
    savingsVsWorstSom: cheapest && worst ? worst.annualTaxSom - cheapest.annualTaxSom : 0,
  };
}

/* ------------------------------------------------------------------ credit */

export const CREDIT_LOAD_DANGER_PCT = 30;
export const CREDIT_LOAD_WARNING_PCT = 20;

export type PaymentRow = {
  month: number;
  paymentSom: number;
  principalSom: number;
  interestSom: number;
  balanceSom: number;
};

export type CreditResult = {
  principalSom: number;
  annualRatePct: number;
  months: number;
  graceMonths: number;
  monthlyPaymentSom: number;
  totalPaymentSom: number;
  totalInterestSom: number;
  overpaymentPct: number;
  schedule: readonly PaymentRow[];
};

export function calculateCredit(input: {
  principalSom: number;
  annualRatePct: number;
  months: number;
  method?: "annuity" | "differentiated";
  graceMonths?: number;
}): CreditResult {
  const { principalSom, annualRatePct, months, method = "annuity", graceMonths = 0 } = input;
  if (principalSom <= 0 || months <= 0 || graceMonths >= months) {
    throw new Error("invalid credit input");
  }

  const monthlyRate = annualRatePct / 1200;
  const repayMonths = months - graceMonths;
  const rows: PaymentRow[] = [];
  let balance = principalSom;

  for (let m = 1; m <= graceMonths; m += 1) {
    const interest = balance * monthlyRate;
    rows.push({
      month: m,
      paymentSom: Math.round(interest),
      principalSom: 0,
      interestSom: Math.round(interest),
      balanceSom: Math.round(balance),
    });
  }

  if (method === "annuity") {
    const factor = (1 + monthlyRate) ** repayMonths;
    const annuity =
      monthlyRate === 0
        ? principalSom / repayMonths
        : (principalSom * monthlyRate * factor) / (factor - 1);
    for (let i = 1; i <= repayMonths; i += 1) {
      const interest = balance * monthlyRate;
      const last = i === repayMonths;
      const principalPart = last ? balance : annuity - interest;
      const payment = last ? principalPart + interest : annuity;
      balance -= principalPart;
      rows.push({
        month: graceMonths + i,
        paymentSom: Math.round(payment),
        principalSom: Math.round(principalPart),
        interestSom: Math.round(interest),
        balanceSom: Math.round(Math.max(balance, 0)),
      });
    }
  } else {
    const part = principalSom / repayMonths;
    for (let i = 1; i <= repayMonths; i += 1) {
      const interest = balance * monthlyRate;
      const principalPart = i === repayMonths ? balance : part;
      balance -= principalPart;
      rows.push({
        month: graceMonths + i,
        paymentSom: Math.round(principalPart + interest),
        principalSom: Math.round(principalPart),
        interestSom: Math.round(interest),
        balanceSom: Math.round(Math.max(balance, 0)),
      });
    }
  }

  const totalPayment = rows.reduce((s, r) => s + r.paymentSom, 0);
  const totalInterest = rows.reduce((s, r) => s + r.interestSom, 0);

  return {
    principalSom,
    annualRatePct,
    months,
    graceMonths,
    monthlyPaymentSom: rows[graceMonths]?.paymentSom ?? rows[0]!.paymentSom,
    totalPaymentSom: totalPayment,
    totalInterestSom: totalInterest,
    overpaymentPct: Math.round((totalInterest / principalSom) * 10_000) / 100,
    schedule: rows,
  };
}

export type CreditLoad = {
  loadPct: number;
  level: "safe" | "warning" | "danger";
  /** i18n code; render with msg({ code, params: { pct: loadPct } }). */
  code: string;
};

export function evaluateCreditLoad(monthlyPaymentSom: number, monthlyRevenueSom: number): CreditLoad {
  if (monthlyRevenueSom <= 0) {
    return { loadPct: 100, level: "danger", code: "load.noRevenue" };
  }
  const loadPct = Math.round((monthlyPaymentSom / monthlyRevenueSom) * 1000) / 10;
  const level: CreditLoad["level"] =
    loadPct >= CREDIT_LOAD_DANGER_PCT
      ? "danger"
      : loadPct >= CREDIT_LOAD_WARNING_PCT
        ? "warning"
        : "safe";
  return { loadPct, level, code: `load.${level}` };
}

/* ----------------------------------------------------------- business plan */

export const REALISTIC_RAMP = 0.8;
export const UTILISATION_VIABLE_MAX = 60;
export const UTILISATION_TIGHT_MAX = 90;
export const PAYBACK_TIGHT_MONTHS = 24;
export const PAYBACK_BAD_MONTHS = 48;
export const WORKING_DAYS_PER_MONTH = 26;

export type Verdict = "viable" | "tight" | "unprofitable";

export type BusinessPlanInput = {
  businessName: string;
  sectorId: string;
  locationId: string;
  initialCapitalSom: number;
  employeeCount: number;
  monthlyRentSom: number;
  productDescription?: string;
  goal?: string;
  expectedMonthlyRevenueSom?: number | null;
  isIndividualEntrepreneur?: boolean;
};

export type Assumption = {
  key: string;
  labelCode: string;
  labelParams?: Record<string, string | number>;
  /** Raw amount for locale formatting, or null when valueText is already final. */
  valueSom: number | null;
  valueText: string;
};

export type BusinessPlanResult = {
  businessName: string;
  sector: Sector;
  location: BusinessLocation;
  monthlyFixedCostsSom: number;
  monthlyRentSom: number;
  monthlyPayrollSom: number;
  monthlyOtherCostsSom: number;
  breakEvenRevenueSom: number;
  breakEvenUnits: number;
  breakEvenCustomersPerDay: number;
  capacityRevenueSom: number;
  plannedRevenueSom: number;
  utilisationPct: number;
  monthlyGrossProfitSom: number;
  monthlyNetProfitSom: number;
  paybackMonths: number | null;
  tax: TaxComparison;
  verdict: Verdict;
  /** i18n code for the headline verdict, e.g. "verdict.viable". */
  verdictCode: string;
  verdictReasons: readonly Msg[];
  recommendations: readonly Msg[];
  assumptions: readonly Assumption[];
};

export function buildBusinessPlan(data: BusinessPlanInput): BusinessPlanResult {
  const sector = getSector(data.sectorId);
  const location = getLocation(data.locationId);
  if (!sector) throw new Error(`unknown sector: ${data.sectorId}`);
  if (!location) throw new Error(`unknown location: ${data.locationId}`);

  const payroll = data.employeeCount > 0 ? location.avgMonthlySalarySom * data.employeeCount : 0;
  const other = Math.round(sector.monthlyOtherCostsSom * location.utilitiesIndex);
  const fixed = data.monthlyRentSom + payroll + other;

  const marginRate = sector.grossMarginPct / 100;
  const breakEvenRevenue = marginRate > 0 ? Math.round(fixed / marginRate) : 0;
  const breakEvenUnits = sector.avgCheckSom ? Math.floor(breakEvenRevenue / sector.avgCheckSom) : 0;
  const breakEvenPerDay = Math.ceil(breakEvenUnits / WORKING_DAYS_PER_MONTH);

  const effectivePeople = Math.max(data.employeeCount, 1);
  const capacityRevenue = effectivePeople * sector.monthlyRevenuePerEmployeeSom;
  const plannedRevenue =
    data.expectedMonthlyRevenueSom != null
      ? data.expectedMonthlyRevenueSom
      : Math.round(capacityRevenue * REALISTIC_RAMP);

  const utilisation = capacityRevenue
    ? Math.round((breakEvenRevenue / capacityRevenue) * 1000) / 10
    : 999;

  const grossProfit = Math.round(plannedRevenue * marginRate);
  const netProfit = grossProfit - fixed;

  const tax = calculateTaxRegimes({
    annualRevenueSom: plannedRevenue * 12,
    annualCostOfGoodsSom: Math.round(plannedRevenue * (1 - marginRate)) * 12,
    annualPayrollSom: payroll * 12,
    annualOtherCostsSom: (data.monthlyRentSom + other) * 12,
    isIndividualEntrepreneur: data.isIndividualEntrepreneur ?? true,
  });
  const monthlyTax = tax.cheapest?.monthlyTaxSom ?? 0;
  const netAfterTax = netProfit - monthlyTax;

  const payback =
    netAfterTax > 0 && data.initialCapitalSom > 0
      ? Math.ceil(data.initialCapitalSom / netAfterTax)
      : null;

  const reasons: Msg[] = [];
  const recommendations: Msg[] = [];
  let verdict: Verdict;

  if (netAfterTax <= 0) {
    verdict = "unprofitable";
    reasons.push({ code: "reason.loss", params: { amount: Math.abs(netAfterTax) } });
  } else if (utilisation > UTILISATION_TIGHT_MAX) {
    verdict = "unprofitable";
    reasons.push({ code: "reason.overCapacity", params: { util: utilisation } });
  } else if (utilisation > UTILISATION_VIABLE_MAX) {
    verdict = "tight";
    reasons.push({ code: "reason.tightCapacity", params: { util: utilisation } });
  } else if (payback != null && payback > PAYBACK_TIGHT_MONTHS) {
    verdict = "tight";
    reasons.push({ code: "reason.slowPayback", params: { util: utilisation, months: payback } });
  } else {
    verdict = "viable";
    reasons.push({ code: "reason.viable", params: { util: utilisation } });
  }

  reasons.push({
    code: "reason.dailyCustomers",
    params: { count: breakEvenPerDay, check: sector.avgCheckSom },
  });

  if (payback == null) {
    reasons.push({ code: "reason.noPayback" });
    recommendations.push({ code: "rec.reviewCosts" });
  } else if (payback > PAYBACK_BAD_MONTHS) {
    reasons.push({ code: "reason.longPayback", params: { months: payback } });
    recommendations.push({ code: "rec.reduceCapital" });
  } else {
    reasons.push({ code: "reason.payback", params: { months: payback } });
  }

  if (tax.cheapest && tax.savingsVsWorstSom > 0) {
    recommendations.push({
      code: "rec.taxRegime",
      params: { regime: `regime.${tax.cheapest.regime}`, amount: tax.savingsVsWorstSom },
    });
  }
  if (data.monthlyRentSom > fixed * 0.4) {
    recommendations.push({ code: "rec.rentHeavy" });
  }
  if (sector.preferentialSector) {
    recommendations.push({ code: "rec.preferentialSector" });
  }

  return {
    businessName: data.businessName,
    sector,
    location,
    monthlyFixedCostsSom: fixed,
    monthlyRentSom: data.monthlyRentSom,
    monthlyPayrollSom: payroll,
    monthlyOtherCostsSom: other,
    breakEvenRevenueSom: breakEvenRevenue,
    breakEvenUnits,
    breakEvenCustomersPerDay: breakEvenPerDay,
    capacityRevenueSom: capacityRevenue,
    plannedRevenueSom: plannedRevenue,
    utilisationPct: utilisation,
    monthlyGrossProfitSom: grossProfit,
    monthlyNetProfitSom: netAfterTax,
    paybackMonths: payback,
    tax,
    verdict,
    verdictCode: `verdict.${verdict}`,
    verdictReasons: reasons,
    recommendations,
    assumptions: [
      {
        key: "avg_salary",
        labelCode: "assume.salary",
        labelParams: { city: location.id },
        valueSom: location.avgMonthlySalarySom,
        valueText: "",
      },
      {
        key: "gross_margin",
        labelCode: "assume.margin",
        valueSom: null,
        valueText: `${sector.grossMarginPct}%`,
      },
      { key: "avg_check", labelCode: "assume.check", valueSom: sector.avgCheckSom, valueText: "" },
      { key: "other_costs", labelCode: "assume.other", valueSom: other, valueText: "" },
      {
        key: "capacity",
        labelCode: "assume.capacity",
        valueSom: sector.monthlyRevenuePerEmployeeSom,
        valueText: "",
      },
    ],
  };
}

export type LocationComparison = {
  plans: readonly BusinessPlanResult[];
  bestLocationId: string;
  otherLocationId: string;
  verdictDiffers: boolean;
};

export function compareLocations(
  data: BusinessPlanInput,
  locationIds: readonly string[],
): LocationComparison {
  const plans = locationIds.map((locationId) => buildBusinessPlan({ ...data, locationId }));
  const rank: Record<Verdict, number> = { viable: 0, tight: 1, unprofitable: 2 };
  const best = plans.reduce((a, b) => {
    const ra = rank[a.verdict];
    const rb = rank[b.verdict];
    if (rb !== ra) return rb < ra ? b : a;
    return (b.paybackMonths ?? 10_000) < (a.paybackMonths ?? 10_000) ? b : a;
  });
  const other = plans.find((p) => p.location.id !== best.location.id) ?? best;

  return {
    plans,
    bestLocationId: best.location.id,
    otherLocationId: other.location.id,
    verdictDiffers: new Set(plans.map((p) => p.verdict)).size > 1,
  };
}

