#!/usr/bin/env bash
# Roll back staging to the last image recorded before the previous ./staging-deploy.sh run.
#
# Usage:
#   ./scripts/deploy/rollback-staging.sh
#
# Or pin explicitly (e.g. from GHCR history):
#   ROLLBACK_IMAGE=ghcr.io/org/repo/api:<previous-sha> ./scripts/deploy/rollback-staging.sh
#
# Deep rollback: deploy a known-good tag manually:
#   ./scripts/deploy/staging-deploy.sh ghcr.io/org/repo/api:v1.2.3
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE_DIR="${BOTFORGE_DEPLOY_STATE_DIR:-$ROOT/.deploy}"
PREV_FILE="$STATE_DIR/staging-previous"

if [[ -n "${ROLLBACK_IMAGE:-}" ]]; then
  exec "$ROOT/scripts/deploy/staging-deploy.sh" "$ROLLBACK_IMAGE"
fi

if [[ ! -f "$PREV_FILE" ]]; then
  echo "No $PREV_FILE — set ROLLBACK_IMAGE=ghcr.io/.../api:<tag> or deploy a tag manually." >&2
  exit 1
fi

IMAGE="$(tr -d '\r\n' <"$PREV_FILE")"
if [[ -z "$IMAGE" ]]; then
  echo "staging-previous is empty." >&2
  exit 1
fi

echo "Rolling back to: $IMAGE"
exec "$ROOT/scripts/deploy/staging-deploy.sh" "$IMAGE"
