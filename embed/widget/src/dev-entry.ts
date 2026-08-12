/**
 * Vite dev server entry only (not shipped in IIFE build).
 */
import { init } from "./main";

const key = import.meta.env.VITE_PUBLIC_WIDGET_KEY || "";
const base = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

if (!key) {
  console.warn(
    "[bfw] Set VITE_PUBLIC_WIDGET_KEY and VITE_API_BASE_URL in embed/widget/.env.local",
  );
} else {
  init({
    publicKey: key,
    apiBaseUrl: base,
    position: "bottom-right",
  });
}
