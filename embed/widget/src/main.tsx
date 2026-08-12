import { render } from "preact";
import { fetchWidgetBootstrap } from "./api/publicWidgetApi";
import { WidgetApp } from "./WidgetApp";
import type { WidgetInitOptions } from "./types";
import css from "./styles.css?inline";

export type { WidgetInitOptions };

function normalizeOptions(raw: WidgetInitOptions): WidgetInitOptions {
  const apiBaseUrl = raw.apiBaseUrl.replace(/\/+$/, "");
  if (!raw.publicKey?.trim()) {
    throw new Error("BotforgeWidget.init: publicKey is required.");
  }
  return {
    publicKey: raw.publicKey.trim(),
    apiBaseUrl,
    position: raw.position ?? "bottom-right",
    zIndex: raw.zIndex ?? 2147482000,
  };
}

/**
 * Mount the widget into the page (Shadow DOM + scoped CSS).
 * Call once per embed. Uses real bootstrap + chat HTTP APIs only.
 */
export function init(options: WidgetInitOptions): void {
  const opts = normalizeOptions(options);

  const host = document.createElement("div");
  host.id = `bfw-embed-${Math.random().toString(36).slice(2, 10)}`;
  host.setAttribute("data-botforge-widget", "true");
  host.style.cssText = [
    "position:fixed",
    "inset:0",
    "width:0",
    "height:0",
    `z-index:${opts.zIndex}`,
    "pointer-events:none",
    "overflow:visible",
  ].join(";");

  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: "open" });
  const styleEl = document.createElement("style");
  styleEl.textContent = css;
  shadow.appendChild(styleEl);

  const mount = document.createElement("div");
  mount.className = "bfw-mount";
  mount.style.cssText = "pointer-events:none;width:100%;height:100%;";
  shadow.appendChild(mount);

  const inner = document.createElement("div");
  inner.style.cssText = "pointer-events:auto;";
  mount.appendChild(inner);

  render(<WidgetApp {...opts} />, inner);
}

/** Optional: prefetch bootstrap for snappier first open (still real HTTP). */
export function prefetchBootstrap(options: { apiBaseUrl: string; publicKey: string }): Promise<void> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const publicKey = options.publicKey.trim();
  if (!publicKey) {
    return Promise.reject(new Error("BotforgeWidget.prefetchBootstrap: publicKey is required."));
  }
  return fetchWidgetBootstrap(apiBaseUrl, publicKey).then(() => undefined);
}

const globalApi = { init, prefetchBootstrap };

declare global {
  interface Window {
    BotforgeWidget?: typeof globalApi;
  }
}

window.BotforgeWidget = globalApi;
