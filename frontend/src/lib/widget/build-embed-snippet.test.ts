import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildWidgetEmbedSnippet,
  getDashboardApiBaseUrl,
  getWidgetScriptSrcForSnippet,
} from "./build-embed-snippet";

describe("build-embed-snippet", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses env API base and script URL when set", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com/");
    vi.stubEnv("NEXT_PUBLIC_WIDGET_SCRIPT_URL", "https://cdn.example.com/w.js");
    expect(getDashboardApiBaseUrl()).toBe("https://api.example.com");
    expect(getWidgetScriptSrcForSnippet()).toBe("https://cdn.example.com/w.js");
    const snippet = buildWidgetEmbedSnippet({
      publicWidgetKey: "pk_abc",
      apiBaseUrl: getDashboardApiBaseUrl(),
      scriptSrc: getWidgetScriptSrcForSnippet(),
    });
    expect(snippet).toContain("pk_abc");
    expect(snippet).toContain("https://api.example.com");
    expect(snippet).toContain("https://cdn.example.com/w.js");
    expect(snippet).toContain("BotforgeWidget.init");
  });

  it("falls back to placeholders when env is empty", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_WIDGET_SCRIPT_URL", "");
    const snippet = buildWidgetEmbedSnippet({
      publicWidgetKey: "pk_x",
      apiBaseUrl: getDashboardApiBaseUrl(),
      scriptSrc: getWidgetScriptSrcForSnippet(),
    });
    expect(snippet).toContain("YOUR_API_BASE_URL");
    expect(snippet).toContain("YOUR_CDN_OR_STATIC_HOST");
  });
});
