# MVP release checklist

Use this for **final go / no-go** before exposing a tier to real users. Check boxes in your run (copy to issue/PR or spreadsheet). **Honest bar:** MVP means core journeys work with known limitations documented in [ARCHITECTURE_MVP.md](./ARCHITECTURE_MVP.md).

## 1. Code quality and CI

- [ ] Default branch **CI green** (`.github/workflows/ci.yml`): Ruff, pytest **non-integration**, frontend lint/test/build, embed widget build, Alembic upgrade against CI Postgres.
- [ ] **Integration tests** run on a host with **Python 3.12** (aligned with CI) and **host-reachable Postgres** (`TEST_DATABASE_URL` or non–`@postgres:` `DATABASE_URL`) for critical paths you care about this release (see [docs/qa/MVP_E2E_VERIFICATION.md](../qa/MVP_E2E_VERIFICATION.md)).
- [ ] **No committed secrets**; `.env` and keys only in secret stores.

## 2. Environment and config (target tier)

- [ ] `APP_ENVIRONMENT` matches tier (`staging` / `production` / `prod` for strict validation).
- [ ] Strict-tier **required** vars satisfied: DB URL, JWT secret (≥32 chars), unsafe dev flags off — see [ENV_CONFIG_CHECKLIST.md](./ENV_CONFIG_CHECKLIST.md).
- [ ] **CORS** (`APP_CORS_ORIGINS`) includes dashboard and any widget parent origins you allow.
- [ ] **Object storage** configured if knowledge PDF upload is in scope for this launch.
- [ ] **Gemini** (or configured provider) key present if AI features are live for users.
- [ ] **Telegram** (if used): bot token(s), webhook base URL (`APP_PUBLIC_API_BASE_URL`), optional Fernet key for stored tokens — see [PRODUCTION_ENV.md](../deployment/PRODUCTION_ENV.md).
- [ ] **Frontend** built with correct `NEXT_PUBLIC_API_BASE_URL` for this tier.
- [ ] **OAuth** (if enabled): redirect URIs registered per tier (Google/GitHub).

## 3. Database

- [ ] **Backup** taken before migrate (staging/prod).
- [ ] **Migrations** applied per [MIGRATION_AND_PROMOTION_ORDER.md](./MIGRATION_AND_PROMOTION_ORDER.md).
- [ ] Smoke query: app connects; no migration errors in deploy logs.

## 4. Smoke tests (after deploy)

- [ ] `GET /api/v1/health` → `{"status":"ok"}` (or documented liveness contract).
- [ ] **Register / login** (email path); session works from dashboard.
- [ ] **Create bot** (wizard or API); appears in list.
- [ ] **Widget**: bootstrap + one chat turn from an allowed origin (or open allowlist in dev only — document prod allowlist policy).
- [ ] **Knowledge**: upload a small PDF if S3/MinIO configured; status moves past upload error.
- [ ] **Sales bot** (if lead capture in scope): manual or scripted path to **lead row** in CRM — full automation is optional; see QA doc.
- [ ] **Telegram** (if enabled): inbound message → response; lead path if sales bots are live.
- [ ] **Superadmin**: platform session + overview (role-gated); non–superadmin denied.
- [ ] **Moderation** (if ops use it): suspend/activate smoke on staging first.

## 5. Security and abuse (MVP baseline)

- [ ] TLS terminates in front of API and dashboard in non-local tiers.
- [ ] Rate limiting and widget abuse behavior understood (in-memory limits = **per process**; multi-worker = distributed limits not in MVP).
- [ ] Error responses do not leak stack traces in strict tiers (`APP_EXPOSE_ERROR_DETAILS` false).

## 6. Observability

- [ ] Logs reachable (platform or file tail); **JSON logs** optional but recommended (`APP_LOG_JSON`).
- [ ] **Sentry** (or equivalent) DSN set if you rely on it for production signal.
- [ ] Release identifier in deploy (`SENTRY_RELEASE` / `APP_VERSION`) for correlation.

## 7. Rollback readiness

- [ ] Previous **container image / artifact** tag recorded.
- [ ] Team agrees: **app rollback** = redeploy prior image; **DB rollback** = restore/forward-fix only with a written plan ([RUNBOOK.md](../deployment/RUNBOOK.md)).

## 8. Go / no-go sign-off

- [ ] Product: MVP scope and known limitations accepted.
- [ ] Engineering: checklist above complete for target tier.
- [ ] On-call / owner: knows where [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) and RUNBOOK live.

**No-go examples:** CI red; strict env validation failing; migrations untested; no backup before prod migrate; critical auth or payment-adjacent flow broken on staging.
