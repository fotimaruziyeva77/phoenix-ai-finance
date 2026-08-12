import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

/**
 * When the browser uses same-origin URLs (empty ``NEXT_PUBLIC_API_BASE_URL``),
 * ``/api/*`` must reach FastAPI. Without rewrites, Next returns 404 for ``/api/v1/health``.
 *
 * Rewrites run on the Next.js server. If Next runs inside Docker, ``127.0.0.1:8000`` is
 * the wrong target — set ``BACKEND_INTERNAL_URL`` (e.g. ``http://backend:8000``) for Compose.
 */
const backendBase =
  process.env.BACKEND_INTERNAL_URL?.replace(/\/$/, "").trim() ||
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "").trim() ||
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendBase}/api/:path*`,
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !!process.env.CI,
  telemetry: false,
  widenClientFileUpload: true,
  sourcemaps: {
    deleteSourcemapsAfterUpload: true,
  },
  disableLogger: true,
});
