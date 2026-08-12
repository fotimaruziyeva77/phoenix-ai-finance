/**
 * Dashboard embed snippet for the Preact IIFE widget (`embed/widget`).
 * Script URL is configurable; API base comes from the same env the dashboard uses for API calls.
 */

export function getDashboardApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
}

/** Where customers host `dist/botforge-widget.js`. Optional env for a copy-paste-ready snippet. */
export function getWidgetScriptSrcForSnippet(): string {
  const u = (process.env.NEXT_PUBLIC_WIDGET_SCRIPT_URL ?? "").trim();
  return u || "https://YOUR_CDN_OR_STATIC_HOST/botforge-widget.js";
}

export function buildWidgetEmbedSnippet(opts: {
  publicWidgetKey: string;
  apiBaseUrl: string;
  scriptSrc: string;
}): string {
  const { publicWidgetKey, apiBaseUrl, scriptSrc } = opts;
  const api = apiBaseUrl || "https://YOUR_API_BASE_URL";
  return `<script src="${scriptSrc}" async></script>
<script>
  window.addEventListener("load", function () {
    if (window.BotforgeWidget) {
      window.BotforgeWidget.init({
        publicKey: "${publicWidgetKey}",
        apiBaseUrl: "${api}",
        position: "bottom-right",
        zIndex: 2147482000,
      });
    }
  });
</script>`;
}
