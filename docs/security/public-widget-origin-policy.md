# Public widget origin and allowlist policy

This document describes how the embeddable **public widget** decides whether a browser request (bootstrap `GET` or chat `POST`) is allowed, based on `Origin` / `Referer` and the per-bot **allowed domains** list (`allowed_domains_json`).

Implementation references: `app/lib/widget_origin_policy.py`, `app/lib/widget_allowed_domains.py`, `app/services/widget_public_gate.py`, `app/core/config.py` (`Settings`).

## Request hostname

The server derives a single hostname string from the request:

1. Prefer the `Origin` header (unless it is missing or the literal `null`).
2. Otherwise use `Referer` and extract the host.

Parsing is best-effort and tolerant; unknown or missing host behaves like “no host” for **non-empty** allowlists (deny). See `extract_hostname_from_origin_or_referer`.

## Stored allowlist entries

When an owner saves domains via `PATCH /api/v1/bots/{bot_id}/widget`, values are normalized with `normalize_allowed_domains`:

- **Exact host** — e.g. `www.example.com`.
- **Subdomain wildcard** — `*.example.com` matches `app.example.com` but not the apex `example.com`. Over-broad entries like `*.com` are rejected.
- **Apex + subdomains** — `.example.com` matches `example.com` and all subdomains.

Wildcard-style entries (`*.` and leading `.`) can be **disabled** by configuration (see below); then only explicit hostnames are accepted.

## Empty allowlist

| Environment | Default behavior | Override |
|-------------|------------------|----------|
| **Strict** (`APP_ENVIRONMENT` in `staging`, `production`, `prod`) | **Deny** all embeds until at least one domain is configured | Set `APP_PUBLIC_WIDGET_ALLOW_EMPTY_ORIGIN_ALLOWLIST=true` to allow any origin (unsafe; logged at warning) |
| **Non-strict** (e.g. `local`, `docker`) | **Allow** any origin (including missing `Origin`/`Referer`) for developer convenience | Set `APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST=true` to mimic strict deny-empty locally or in tests |

The effective flag is `Settings.public_widget_deny_empty_origin_allowlist_effective`, wired into `WidgetOriginPolicyOptions.deny_empty_allowlist` for bootstrap and chat.

## Non-empty allowlist

- The request host must match at least one allowlist entry (pattern or loopback rule).
- If no host can be derived from headers, the request is **denied**.

## Loopback equivalence

When `APP_PUBLIC_WIDGET_ORIGIN_LOOPBACK_EQUIVALENT` is true (default), `localhost`, `127.0.0.1`, `::1`, and `[::1]` are treated as interchangeable **if** any loopback host appears in the allowlist.

## Wildcard patterns in strict tiers

- Default in strict tiers: **wildcard patterns are not allowed** in saved allowlists unless ops explicitly sets `APP_PUBLIC_WIDGET_ALLOW_ALLOWLIST_WILDCARD_PATTERNS=true`.
- Default in non-strict: wildcard patterns are allowed unless explicitly set to `false`.

Effective flag: `Settings.public_widget_allow_allowlist_wildcard_patterns_effective`.

## Client-visible errors (sanitized)

Embedding denied for policy reasons (wrong origin, missing headers when required, empty allowlist under deny-empty, etc.) returns **HTTP 403** with a single generic message for all such cases:

- Code: `widget_origin_forbidden`
- Message: `This widget cannot be loaded from this site.`

Do not rely on message text to distinguish sub-causes; use server logs and metrics.

Owner dashboard validation errors for invalid allowlist payloads use `widget_config_validation_error` and may include field-specific detail (authenticated routes only).

## Related environment variables

| Variable | Role |
|----------|------|
| `APP_PUBLIC_WIDGET_ALLOW_EMPTY_ORIGIN_ALLOWLIST` | Strict only: opt into “open” empty allowlist (unsafe) |
| `APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST` | Non-strict only: deny when allowlist empty |
| `APP_PUBLIC_WIDGET_ALLOW_ALLOWLIST_WILDCARD_PATTERNS` | Explicit enable/disable of `*.` / `.` patterns in saved allowlists |
| `APP_PUBLIC_WIDGET_ORIGIN_LOOPBACK_EQUIVALENT` | Loopback hostname equivalence |

See also [ENV_CONFIG_CHECKLIST.md](../release/ENV_CONFIG_CHECKLIST.md) and `app/core/config.py` field descriptions.
