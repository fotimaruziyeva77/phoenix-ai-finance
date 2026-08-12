import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NicheCatalogProvider } from "@/contexts/niche-catalog-context";
import { EMERGENCY_NICHE_CATALOG_ITEMS } from "@/lib/bot-domain/niche-emergency-fallback";

import { NicheSection } from "./niche-section";

describe("NicheSection", () => {
  it("renders titles and descriptions from catalog", () => {
    render(
      <NicheCatalogProvider initialData={{ schema_version: 1, niches: EMERGENCY_NICHE_CATALOG_ITEMS }}>
        <NicheSection />
      </NicheCatalogProvider>,
    );
    expect(screen.getByText("Education")).toBeInTheDocument();
    expect(screen.getByText(/Capture learner intent/i)).toBeInTheDocument();
    expect(screen.getByText("Healthcare / Clinic")).toBeInTheDocument();
  });
});
