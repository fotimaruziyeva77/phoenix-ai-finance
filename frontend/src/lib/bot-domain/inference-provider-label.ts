/**
 * Human-facing labels for registered inference provider ids.
 * Unknown ids fall back to the raw key so the UI stays honest as new providers ship.
 */
const INFERENCE_PROVIDER_LABELS: Record<string, string> = {
  gemini: "Built-in default",
};

export function inferenceProviderLabel(providerId: string): string {
  return INFERENCE_PROVIDER_LABELS[providerId] ?? providerId;
}
