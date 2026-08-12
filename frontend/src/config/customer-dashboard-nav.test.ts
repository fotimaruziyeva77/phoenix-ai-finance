import { describe, expect, it } from "vitest";

import {
  CUSTOMER_DASHBOARD_NAV,
  matchCustomerDashboardNav,
} from "./customer-dashboard-nav";

describe("matchCustomerDashboardNav", () => {
  it("resolves exact /dashboard to Overview", () => {
    const m = matchCustomerDashboardNav("/dashboard");
    expect(m.href).toBe("/dashboard");
    expect(m.pageTitle).toBe("Overview");
  });

  it("prefers longest prefix for nested paths", () => {
    expect(matchCustomerDashboardNav("/dashboard/settings").pageTitle).toBe("Settings");
    expect(matchCustomerDashboardNav("/dashboard/settings/team").pageTitle).toBe("Settings");
    expect(matchCustomerDashboardNav("/dashboard/bots").pageTitle).toBe("Bots");
  });

  it("does not treat /dashboard-bots as under /dashboard", () => {
    const m = matchCustomerDashboardNav("/dashboard-bots");
    expect(m).toEqual(CUSTOMER_DASHBOARD_NAV[0]);
  });

  it("falls back to Overview for unknown paths under app", () => {
    const m = matchCustomerDashboardNav("/dashboard/unknown-route");
    expect(m.href).toBe("/dashboard");
  });

  it("nav list has expected labels in order", () => {
    expect(CUSTOMER_DASHBOARD_NAV.map((i) => i.label)).toEqual([
      "Overview",
      "Bots",
      "Leads",
      "Analytics",
      "Billing",
      "Settings",
    ]);
  });
});
