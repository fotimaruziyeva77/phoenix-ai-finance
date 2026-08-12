# Release process

Practical promotion path for BotForge AI without coupling to a single cloud vendor.

## 1. Preconditions

- **CI green** on the commit you intend to release (see `.github/workflows/ci.yml`): lint, unit tests, **PostgreSQL integration tests** (`pytest -m integration`), frontend/widget build, migration sanity, and the aggregate **CI status gate**. Configure branch protection to require the gate or the integration job (see [docs/qa/CI_INTEGRATION.md](../qa/CI_INTEGRATION.md)).
- **Changelog / version**: tag or release notes as your team prefers (`APP_VERSION` / `SENTRY_RELEASE` can track the same SHA).

## 2. Staging

1. Merge to your **staging branch** (or trigger deploy from a known SHA after CI passes).
2. Apply **staging** secrets and URLs (separate DB, buckets, OAuth redirect URIs, optional Sentry project).
3. Set `APP_ENVIRONMENT=staging` and required variables (see [PRODUCTION_ENV.md](./PRODUCTION_ENV.md)).
4. **Build** images/artifacts for staging (API, frontend, widget) with staging public env vars.
5. Run **migrations** against the staging database (**after backup**), **before** routing users to app versions that require the new schema (see [RUNBOOK.md](./RUNBOOK.md) § Migrate for ordering). Then deploy or roll traffic to the new build.
6. **Smoke test**: health endpoint, auth, one critical user flow, Telegram webhook if used.

### GitHub Actions staging (implemented)

See **[CI_CD_STAGING.md](./CI_CD_STAGING.md)** for secrets, variables, and safety notes.

- **Deploy staging** (`.github/workflows/deploy-staging.yml`): on push to `staging` or `workflow_dispatch` — builds and **pushes** `ghcr.io/<repo>/api:staging` and `:<sha>`, optional **SSH** rollout to a VM running Compose, optional **health** poll on `GET /api/v1/health`.
- **Release image** (`.github/workflows/release-image.yml`): on git tag **`v*`** — pushes **semver** and **SHA** tags (immutable release artifacts).

Optional: GitHub **Environment** `staging` with required reviewers protects SSH rollout secrets.

**Versioning:** [VERSIONING_AND_TAGS.md](./VERSIONING_AND_TAGS.md).

## 3. Production

1. Promote the **same artifact** (image digest or build SHA) that passed staging—avoid rebuilding without replaying CI.
2. Set `APP_ENVIRONMENT=production` (or `prod`).
3. **Backup database**, then **migrate** (before or as part of the same change window as the new app revision—see [RUNBOOK.md](./RUNBOOK.md) § Migrate), then roll out the new processes/containers.
4. Monitor logs and error tracking; be ready to **roll back** the app to the prior image (see [RUNBOOK.md](./RUNBOOK.md)).

## 4. Emergency rollback

- **App:** redeploy previous image / revision.
- **DB:** only downgrade or restore with a written plan; do not assume `alembic downgrade` is always safe.

## 5. What this repo does not automate

- TLS certificates, DNS, WAF, or CDN
- Secret rotation playbooks
- Database failover

Document those in your org’s internal runbooks as you adopt a provider.
