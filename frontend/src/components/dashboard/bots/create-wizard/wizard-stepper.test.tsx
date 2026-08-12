import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { WIZARD_STEPS } from "@/lib/create-bot-wizard/steps-config";

import { WizardStepper } from "./wizard-stepper";

describe("WizardStepper", () => {
  it("renders all configured steps", () => {
    const html = renderToStaticMarkup(<WizardStepper stepIndex={0} />);
    expect(html).toContain('data-testid="wizard-stepper"');
    for (const step of WIZARD_STEPS) {
      expect(html).toContain(step.label);
    }
  });

  it("marks current step with aria-current=step", () => {
    const html = renderToStaticMarkup(<WizardStepper stepIndex={2} />);
    expect(html).toContain('aria-current="step"');
    expect(html).toContain("Basics");
  });
});
