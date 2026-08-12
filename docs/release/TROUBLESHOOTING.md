# Incident response and basic troubleshooting

First-line reference when something breaks in **local**, **staging**, or **production**. Escalate to full [RUNBOOK.md](../deployment/RUNBOOK.md) for build/migrate/rollback detail.

## Immediate triage

1. **Scope:** API only, frontend only, widget, Telegram, or DB?
2. **Tier:** `APP_ENVIRONMENT` and recent deploy / migration?
3. **Logs:** API stderr/stdout or JSON logs; browser network tab for dashboard; Telegram webhook delivery in BotFather / provider logs.
4. **Health:** `GET /api/v1/health` — if this fails, fix liveness before deeper debugging.

## Symptom → likely causes → actions

### API won’t start (strict tier)

- **Validation error at boot** — Check `DATABASE_URL`, `JWT_SECRET_KEY` length, forbidden `APP_RELOAD` / `APP_LOG_REQUEST_BODY` / `APP_EXPOSE_ERROR_DETAILS` in staging/prod ([ENV_CONFIG_CHECKLIST.md](./ENV_CONFIG_CHECKLIST.md)).
- **DB connection refused** — Wrong host/port from container network; DSN must resolve from **where the process runs**.

### 401 / 403 everywhere after deploy

- **JWT secret rotated** — All existing sessions invalid; users must re-login; ensure single secret across all API instances.
- **CORS** — Browser calls blocked; verify `APP_CORS_ORIGINS` includes exact scheme + host + port.

### Widget: 403 origin / chat unavailable

- **Allowlist** — `PATCH` widget `allowed_domains_json` to include embed parent host; remember localhost vs 127.0.0.1 loopback rules (`Settings.public_widget_origin_loopback_equivalent`).
- **Owner suspended / bot platform-suspended** — Moderation blocks public widget; check admin APIs and `users.is_active` / `bots.platform_suspended_at`.

### Telegram: no replies

- **Webhook** — URL must match `APP_PUBLIC_API_BASE_URL` and TLS; re-set webhook after URL change.
- **Token** — Invalid or revoked bot token in DB vs BotFather.
- **Fernet key** — If token encryption enabled, wrong `APP_TELEGRAM_TOKEN_FERNET_KEY` prevents decrypt.

### Knowledge PDF upload fails

- **Storage** — Bucket/credentials/endpoint; region and addressing style for S3-compatible stores.
- **Validation** — Not a PDF or magic bytes fail; size limits.

### Leads not appearing

- **Not a sales bot** — Lead creation gates require sales goal and funnel readiness ([lead_creation_service](../../app/services/lead_creation_service.py)).
- **Missing phone / required niche fields** — Creation skipped with logged reason; check integration test docs for expected rules.
- **Duplicate rules** — Open pipeline duplicate phone may block second lead.

### Rate limit / 429 spikes

- **In-memory limits** — Per process; multiple workers multiply effective capacity; attackers can hit one worker — document and consider Redis later ([ARCHITECTURE_MVP.md](./ARCHITECTURE_MVP.md)).

### Database migration failed mid-way

- **Do not guess** — Inspect Alembic version table; consult DBA; restore backup if data partially migrated; prefer forward-fix migration after root cause.

## Frontend / Next.js local

- **`.next` readlink errors on OneDrive** — Clone outside sync folder or exclude `.next` from sync.
- **API 404 from browser** — Next rewrites: set `BACKEND_INTERNAL_URL` in Docker or ensure backend listens on URL in `next.config.ts`.

## Who to page

- **Security / data breach** — Follow org incident process; rotate secrets; preserve logs.
- ** prolonged outage** — App rollback first; DB only with runbook + backup.

## Post-incident

- Log timeline and root cause in your tracker.
- Add a test or checklist item if this class of failure was preventable.
