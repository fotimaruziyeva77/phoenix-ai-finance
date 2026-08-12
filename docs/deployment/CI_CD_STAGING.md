# CI/CD: staging images, rollout, health checks, rollback

This document describes the **automated staging pipeline** in `.github/workflows/` and the **on-host scripts** under `scripts/deploy/`. It is written for operators, release managers, and engineers wiring secrets.

## Workflows (summary)

| Workflow | Trigger | What it does |
|----------|---------|----------------|
| **CI** (`.github/workflows/ci.yml`) | PR / `main` | Lint, tests, integration tests, frontend/widget builds, migration sanity — **required gate** before release. |
| **Deploy staging** (`.github/workflows/deploy-staging.yml`) | Push to `staging` branch **or** `workflow_dispatch` | Builds the API `Dockerfile`, pushes to **GHCR**, optional SSH Compose rollout, optional HTTP health verification. |
| **Release image** (`.github/workflows/release-image.yml`) | Git tag `v*` (e.g. `v1.4.0`) | Pushes immutable images tagged with **semver** and **git SHA** (no deploy). |
| **E2E real stack** (`.github/workflows/e2e-real-stack.yml`) | `workflow_dispatch` / schedule | Playwright against a disposable stack — optional signal, not the default PR gate. |

## Image naming (GHCR)

Images are pushed to:

`ghcr.io/<lowercase-github-repository>/api:<tag>`

Examples:

- Every staging workflow: `:staging` and `:<full-git-sha>`
- Release workflow: `:<tag>` (e.g. `v1.4.0`) and `:<full-git-sha>`

Set on the deployment host:

```bash
export BOTFORGE_API_IMAGE=ghcr.io/myorg/botforge_ai/api:7a8b9c0d1e2f3...
```

`docker-compose.yml` uses `BOTFORGE_API_IMAGE` for **backend** and **knowledge-worker** (same image, different commands).

## GitHub Actions: secrets and variables

### Required for GHCR push (default)

- **`GITHUB_TOKEN`** — provided by Actions; workflow sets `permissions: packages: write`.

**Package visibility:** first push may create a private package under the org/user. Adjust visibility in GitHub → Packages if the image should be readable by staging hosts (pull) without extra auth.

### Optional — SSH rollout (`workflow_dispatch` → *Run remote rollout* = true)

Create a GitHub **Environment** named `staging` (Settings → Environments) and add **required reviewers** if you want a manual approval before any SSH access.

| Type | Name | Purpose |
|------|------|---------|
| Secret | `STAGING_SSH_HOST` | Hostname or IP of the staging VM |
| Secret | `STAGING_SSH_USER` | SSH user (e.g. `deploy`) |
| Secret | `STAGING_SSH_KEY` | Private key (PEM) for that user — **never** commit |
| Variable | `STAGING_REPO_PATH` | Absolute path to the repo clone on the host (e.g. `/home/deploy/botforge_ai`) |

The remote step runs:

```bash
cd "$STAGING_REPO_PATH"
export BOTFORGE_API_IMAGE=<image from this workflow run>
docker compose pull backend knowledge-worker
docker compose up -d --no-build backend knowledge-worker
```

**Migrations:** not run automatically — run `scripts/deploy/migrate.sh` (or equivalent) against staging DB when the release includes schema changes.

### Optional — health verification

| Input / variable | When |
|------------------|------|
| `workflow_dispatch` → **Base URL** | Polls `GET {url}/api/v1/health` after the workflow. If **SSH rollout** is enabled, verification runs **after** SSH completes. |
| Variable `STAGING_HEALTH_URL` | Used only when **push** to `staging` **and** `STAGING_AUTO_VERIFY` is set to `true` — see warning below. |

**Warning:** Post-push HTTP verification passes if *something* at that URL is healthy; it does **not** prove the **new** digest is live unless your platform deploys immediately on every GHCR push. Prefer `workflow_dispatch` with URL + SSH, or verify manually.

## On-host deploy and rollback (scripts)

From the server that runs Compose. If GHCR packages are **private**, log in once per host (PAT or org token with `read:packages`):

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u YOUR_USER --password-stdin
```

Then:

```bash
./scripts/deploy/staging-deploy.sh ghcr.io/org/repo/api:staging
# or
export BOTFORGE_API_IMAGE=ghcr.io/org/repo/api:abc1234
./scripts/deploy/staging-deploy.sh
```

Rollback one step (uses `.deploy/staging-previous`):

```bash
./scripts/deploy/rollback-staging.sh
```

Pin a specific previous image:

```bash
ROLLBACK_IMAGE=ghcr.io/org/repo/api:deadbeef ./scripts/deploy/rollback-staging.sh
```

State files live under `.deploy/` (gitignored). They store **image references only**, not secrets.

## Operational checklist (staging)

1. CI green on the commit you are promoting.
2. Image pushed (`Deploy staging` workflow success) — note the **SHA tag** digest.
3. Run DB **backup**, then **migrate** if needed, then **pull + up** (CI SSH step or `staging-deploy.sh`).
4. Confirm `GET /api/v1/health` (workflow verification or curl).
5. Smoke: auth, one critical path, webhooks if applicable.

## Production safety

- These workflows **do not** target production. Production promotion should reuse the **same digest** that passed staging, plus your org’s approvals ([RELEASE_PROCESS.md](./RELEASE_PROCESS.md)).
- Do not store long-lived registry passwords in the repo; use GHCR with `GITHUB_TOKEN` in CI and a read-only **PAT** or **machine user** token on hosts for `docker pull` if packages are private.

## Related docs

- [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) — promotion and versioning narrative
- [PRODUCTION_ENV.md](./PRODUCTION_ENV.md) — env and secrets model
- [RUNBOOK.md](./RUNBOOK.md) — migrate, start, rollback context
