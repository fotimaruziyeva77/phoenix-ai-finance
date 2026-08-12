#!/usr/bin/env bash
# Pull a published API image and restart backend + knowledge-worker via Compose.
# Records current/previous image refs under .deploy/ for scripts/deploy/rollback-staging.sh
#
# Usage:
#   export BOTFORGE_API_IMAGE=ghcr.io/your-org/your-repo/api:abc1234
#   ./scripts/deploy/staging-deploy.sh
# Or pass the image as the first argument:
#   ./scripts/deploy/staging-deploy.sh ghcr.io/your-org/your-repo/api:staging
#
# Preconditions: docker compose v2, .env on the host, deps (postgres/redis/minio) healthy.
# After upgrade, run Alembic if the release includes migrations: ./scripts/deploy/migrate.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

IMAGE="${1:-${BOTFORGE_API_IMAGE:-}}"
if [[ -z "$IMAGE" ]]; then
  echo "Set BOTFORGE_API_IMAGE or pass image:tag as first argument." >&2
  exit 1
fi

STATE_DIR="${BOTFORGE_DEPLOY_STATE_DIR:-$ROOT/.deploy}"
mkdir -p "$STATE_DIR"
if [[ -f "$STATE_DIR/staging-current" ]]; then
  cp "$STATE_DIR/staging-current" "$STATE_DIR/staging-previous"
fi
echo "$IMAGE" >"$STATE_DIR/staging-current"

export BOTFORGE_API_IMAGE="$IMAGE"
docker compose pull backend knowledge-worker
docker compose up -d --no-build backend knowledge-worker

PORT="${APP_PUBLISH_PORT:-8000}"
echo "Waiting for http://127.0.0.1:${PORT}/api/v1/health ..."
for _ in $(seq 1 60); do
  if curl -fsS --max-time 10 "http://127.0.0.1:${PORT}/api/v1/health" >/dev/null; then
    echo "Health check OK"
    exit 0
  fi
  sleep 2
done
echo "Health check failed" >&2
exit 1
