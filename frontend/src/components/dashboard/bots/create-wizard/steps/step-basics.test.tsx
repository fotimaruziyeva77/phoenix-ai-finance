import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { createDefaultDraft } from "@/lib/create-bot-wizard/default-draft";
import { LANGUAGE_OPTIONS, TONE_OPTIONS } from "@/lib/create-bot-wizard/options";

import { StepBasics } from "./step-basics";

describe("StepBasics", () => {
  it("renders required and optional fields with helper text", () => {
    const html = renderToStaticMarkup(
      <StepBasics draft={createDefaultDraft()} updateDraft={vi.fn()} />,
    );
    expect(html).toContain("Bot name");
    expect(html).toContain("Shown in your workspace and future channel settings.");
    expect(html).toContain("Opening line");
    expect(html).toContain("Short description");
    expect(html).toContain("Language");
    expect(html).toContain("Tone is optional.");
  });

  it("renders all configured tone and language options", () => {
    const html = renderToStaticMarkup(
      <StepBasics draft={createDefaultDraft()} updateDraft={vi.fn()} />,
    );
    const unescaped = html.replaceAll("&amp;", "&");
    for (const tone of TONE_OPTIONS) {
      expect(unescaped).toContain(tone.label);
    }
    for (const lang of LANGUAGE_OPTIONS) {
      expect(unescaped).toContain(lang.label);
    }
  });

  it("reflects persisted values for form state hydration", () => {
    const draft = {
      ...createDefaultDraft(),
      basics: {
        displayName: "Onboarding Bot",
        languageCode: "es",
        toneId: "professional" as const,
        welcomeMessage: "Hola! Como puedo ayudarte hoy?",
        shortDescription: "Guides prospects through onboarding.",
      },
    };
    const html = renderToStaticMarkup(<StepBasics draft={draft} updateDraft={vi.fn()} />);
    expect(html).toContain('value="Onboarding Bot"');
    expect(html).toContain('value="es"');
    expect(html).toContain("Guides prospects through onboarding.");
    expect(html).toContain("Hola! Como puedo ayudarte hoy?");
  });
});
