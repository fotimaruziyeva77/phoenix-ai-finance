import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../sentry.server.config");
  } else if (process.env.NEXT_RUNTIME === "edge") {
    await import("../sentry.edge.config");
  }
}

export async function onRequestError(
  error: unknown,
  errorRequest: Readonly<{
    path: string;
    method: string;
    headers: NodeJS.Dict<string | string[] | undefined>;
  }>,
  errorContext: Readonly<{
    routerKind: string;
    routePath: string;
    routeType: string;
  }>,
): Promise<void> {
  Sentry.captureRequestError(error, errorRequest, errorContext);
}
