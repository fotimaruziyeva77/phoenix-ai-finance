# BotForge embeddable web chat widget

Isolated from the Next.js dashboard (`frontend/`). **Preact + Vite** IIFE bundle with **Shadow DOM** so host-site CSS does not leak in or out.

## Public API integration

| Action | Method | Path |
|--------|--------|------|
| Bootstrap | `GET` | `{apiBase}/api/v1/public/widget/{public_widget_key}/bootstrap` |
| Send turn | `POST` | `{apiBase}/api/v1/public/widget/{public_widget_key}/chat` |

Types mirror `WidgetPublicBootstrapResponse` and `PublicWidgetChatRequest` / `PublicChatResponse` in the Python API. Errors use `StandardErrorResponse` (`error.message`, `error.code`).

## Styling approach

- **Scoped**: all rules live under `.bfw-root` inside Shadow DOM (`src/styles.css`).
- **Theming**: `data-bfw-theme="light" | "dark"` is derived from bootstrap `theme` (substring `dark` → dark). CSS variables (`--bfw-accent`, `--bfw-surface`, …) are the extension point for **branding** without touching dashboard code.
- **Layout**: fixed launcher + panel; `position` option flips left/right; mobile uses full-width panel (see media query).

## Tests

```bash
cd embed/widget
npm install
npm test
```

- **Component / behavior**: `src/WidgetApp.test.tsx` (mocked `fetch` — real URL shapes, no fake transcript).
- **Layout contract**: `src/styles.contract.test.ts` (responsive CSS markers).
- **Smoke**: end-to-end user journey with mocks in the same file.

## Build

```bash
cd embed/widget
npm install
npm run build
```

Outputs `dist/botforge-widget.js` (single IIFE; CSS inlined as a string in JS).

## Embed snippet (production)

Host the built script on your CDN or static file server. **CORS**: the API must allow the customer `Origin` (widget allowlist on the server already enforces domain policy for bootstrap/chat).

```html
<script src="https://your-cdn.example.com/botforge-widget.js" async></script>
<script>
  window.addEventListener("load", function () {
    if (window.BotforgeWidget) {
      window.BotforgeWidget.init({
        publicKey: "YOUR_PUBLIC_WIDGET_KEY",
        apiBaseUrl: "https://api.yourcompany.com",
        position: "bottom-right",
        zIndex: 2147482000,
      });
    }
  });
</script>
```

Optional prefetch (real HTTP, no UI):

```js
BotforgeWidget.prefetchBootstrap({ publicKey: "…", apiBaseUrl: "…" });
```

## Local dev

Create `embed/widget/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_PUBLIC_WIDGET_KEY=your_key_from_dashboard
```

```bash
npm run dev
```

Open the shown URL; the widget mounts on a blank page.

## Future-ready (not implemented)

See `src/future/extensions.md` for notes on typing indicator, reconnect, and streaming transports.
