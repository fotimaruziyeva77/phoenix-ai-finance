import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { NicheCatalogProvider } from "@/contexts/niche-catalog-context";
import { createDefaultDraft } from "@/lib/create-bot-wizard/default-draft";
import { EMERGENCY_NICHE_CATALOG_ITEMS } from "@/lib/bot-domain/niche-emergency-fallback";

import { StepNiche } from "./step-niche";

const CATALOG_FIXTURE = { schema_version: 1 as const, niches: EMERGENCY_NICHE_CATALOG_ITEMS };

describe("StepNiche", () => {
  it("renders niches from catalog provider with stable test ids", () => {
    const html = renderToStaticMarkup(
      <NicheCatalogProvider initialData={CATALOG_FIXTURE}>
        <StepNiche draft={createDefaultDraft()} updateDraft={vi.fn()} />
      </NicheCatalogProvider>,
    );
    expect(EMERGENCY_NICHE_CATALOG_ITEMS).toHaveLength(4);
    for (const opt of EMERGENCY_NICHE_CATALOG_ITEMS) {
      expect(html).toContain(`data-testid="niche-card-${opt.id}"`);
      expect(html).toContain(opt.display_name);
      expect(html).toContain(opt.wizard_hint);
    }
  });

  it("reflects selected niche state", () => {
    const draft = {
      ...createDefaultDraft(),
      nicheId: "services",
    };
    const html = renderToStaticMarkup(
      <NicheCatalogProvider initialData={CATALOG_FIXTURE}>
        <StepNiche draft={draft} updateDraft={vi.fn()} />
      </NicheCatalogProvider>,
    );
    expect(html).toContain('value="services"');
    expect(html).toContain("checked");
    expect(html).toContain('data-selected="true"');
  });
});
