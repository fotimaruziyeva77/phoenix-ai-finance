#!/usr/bin/env bash
# Run Alembic migrations. Requires DATABASE_URL (or APP_DATABASE_URL) in the environment.
# Prefer: export from a secret manager, or `set -a; source /secure/path/envfile; set +a` (file not in git),
# or `docker run --env-file` — avoid typing passwords into shell history.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
if [[ -z "${DATABASE_URL:-}" && -z "${APP_DATABASE_URL:-}" ]]; then
  echo "migrate.sh: set DATABASE_URL or APP_DATABASE_URL" >&2
  exit 1
fi
exec alembic upgrade head
