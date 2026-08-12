const STORAGE_KEY = "botforge_correlation_id";

function randomId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `bf-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/**
 * Browser: stable correlation id per tab (sessionStorage). Server / non-browser: new id per call.
 */
export function getOrCreateCorrelationId(): string {
  if (typeof window === "undefined") {
    return randomId();
  }
  try {
    const existing = sessionStorage.getItem(STORAGE_KEY);
    if (existing) {
      return existing;
    }
    const id = randomId();
    sessionStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    return randomId();
  }
}
