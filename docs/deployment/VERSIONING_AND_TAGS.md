# Release versioning and image tags

## Git tags (semver)

- Create an annotated or lightweight tag on the commit you intend to ship: `vMAJOR.MINOR.PATCH` (examples: `v1.0.0`, `v1.12.3`).
- Pushing `v*` triggers **Release image** (`.github/workflows/release-image.yml`), which publishes:
  - `ghcr.io/<repo>/api:<tag>` — e.g. `v1.12.3`
  - `ghcr.io/<repo>/api:<git-sha>` — immutable pointer to the same build

**`latest`:** this repository does **not** auto-push a `latest` tag to avoid accidental production pulls of an arbitrary build. Pin by **SHA** or **semver** tag.

## Staging-moving tag

- The **Deploy staging** workflow always updates `ghcr.io/<repo>/api:staging` to the **current** `staging` branch head (or the commit of a manual dispatch). Use for convenience; for audits prefer the **SHA** tag from the same workflow run.

## Application version strings

- Optional: align `APP_VERSION` / observability release fields with the git tag or SHA in your tier env files ([PRODUCTION_ENV.md](./PRODUCTION_ENV.md)).

## Rollback reference

- Keep a short log (ticket or runbook note) of **image digest or SHA tag** deployed to each environment so rollback does not depend only on `.deploy/staging-previous`.
