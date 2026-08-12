import { apiFetch, apiFetchWithAuth } from "@/lib/api/client";

export type PlanDto = {
  slug: string;
  name: string;
  price_cents: number;
  price_dollars: number;
  tagline: string;
  is_popular: boolean;
  conversations_per_month: number | null;
  bots_max: number | null;
  pdf_files_max: number | null;
  storage_mb: number | null;
  telegram_allowed: boolean;
  analytics_detailed: boolean;
  show_branding: boolean;
};

export type SubscriptionDto = {
  plan_slug: string;
  plan_name: string;
  status: "active" | "trialing" | "past_due" | "canceled" | "expired";
  price_cents: number;
  price_dollars: number;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  canceled_at: string | null;
};

export type CheckoutResponse = {
  checkout_url: string;
};

export type PortalResponse = {
  portal_url: string;
};

/** Fetch all available plans (public, no auth). */
export async function fetchPlans(): Promise<PlanDto[]> {
  return apiFetch<PlanDto[]>("/api/v1/billing/plans", { method: "GET" });
}

/** Fetch the current user's subscription. */
export async function fetchSubscription(accessToken: string | null): Promise<SubscriptionDto> {
  return apiFetchWithAuth<SubscriptionDto>("/api/v1/billing/subscription", accessToken, {
    method: "GET",
  });
}

/** Create a Stripe Checkout session and return the redirect URL. */
export async function createCheckoutSession(
  accessToken: string | null,
  planSlug: string,
): Promise<CheckoutResponse> {
  return apiFetchWithAuth<CheckoutResponse>("/api/v1/billing/checkout", accessToken, {
    method: "POST",
    body: JSON.stringify({ plan_slug: planSlug }),
    headers: { "Content-Type": "application/json" },
  });
}

/** Create a Stripe Customer Portal session and return the redirect URL. */
export async function createPortalSession(accessToken: string | null): Promise<PortalResponse> {
  return apiFetchWithAuth<PortalResponse>("/api/v1/billing/portal", accessToken, {
    method: "POST",
  });
}

/** Format a limit value: null = "Unlimited", number = formatted string */
export function formatLimit(value: number | null, unit = ""): string {
  if (value === null) return "Unlimited";
  return `${value.toLocaleString()}${unit ? ` ${unit}` : ""}`;
}
