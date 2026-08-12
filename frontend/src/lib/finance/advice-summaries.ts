/**
 * Compact, language-neutral digests of computed results, handed to Gemini so it
 * can phrase an explanation. Labels stay English on purpose — the model answers
 * in the user's language; only the NUMBERS matter, and they come verbatim from
 * the engine.
 */

import type { computeCredit } from "@/components/dashboard/finance/credit-view";
import type {
  BusinessPlanResult,
  LocationComparison,
  TaxComparison,
} from "@/lib/finance/engine";

export function summarizePlan(
  plan: BusinessPlanResult,
  comparison: LocationComparison,
): string {
  return [
    `Business plan result. Sector: ${plan.sector.id}, city: ${plan.location.id}.`,
    `Verdict: ${plan.verdict}. Break-even revenue: ${plan.breakEvenRevenueSom} som/month.`,
    `Customers needed per day: ${plan.breakEvenCustomersPerDay}.`,
    `Monthly net profit: ${plan.monthlyNetProfitSom} som. Payback: ${plan.paybackMonths ?? "never"} months.`,
    `Monthly fixed costs: ${plan.monthlyFixedCostsSom} som (rent ${plan.monthlyRentSom}, payroll ${plan.monthlyPayrollSom}).`,
    `City comparison winner: ${comparison.bestLocationId} (verdicts differ: ${comparison.verdictDiffers}).`,
    plan.tax.cheapest
      ? `Cheapest tax regime: ${plan.tax.cheapest.regime}; wrong regime costs ${plan.tax.savingsVsWorstSom} som/year extra.`
      : "",
  ].join(" ");
}

export function summarizeCredit(credit: ReturnType<typeof computeCredit>): string {
  return [
    `Loan check. Principal: ${credit.base.principalSom} som, ${credit.base.months} months at ${credit.enteredRate}%.`,
    `Monthly payment: ${credit.base.monthlyPaymentSom} som. Total repaid: ${credit.base.totalPaymentSom} som (overpayment ${credit.base.overpaymentPct}%).`,
    credit.load ? `Credit load: ${credit.load.loadPct}% of monthly revenue (level: ${credit.load.level}).` : "",
    credit.bestProgram
      ? `Eligible state programme "${credit.bestProgram.program.code}" at ${credit.bestProgram.program.ratePct}% would save ${credit.bestProgram.savings} som in total.`
      : "No cheaper state programme matched this profile.",
  ].join(" ");
}

export function summarizeTax(tax: TaxComparison): string {
  return [
    `Tax regime comparison. Annual revenue: ${tax.annualRevenueSom} som.`,
    tax.cheapest
      ? `Cheapest eligible regime: ${tax.cheapest.regime} at ${tax.cheapest.annualTaxSom} som/year (${tax.cheapest.effectiveRatePct}% of revenue).`
      : "No eligible regime.",
    `Picking the wrong regime costs ${tax.savingsVsWorstSom} som per year.`,
  ].join(" ");
}
