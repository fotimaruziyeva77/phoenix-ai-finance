#!/usr/bin/env bash
# Build the API Docker image. No secrets required.
# Default tag matches docker-compose.yml when BOTFORGE_API_IMAGE is unset.
#
# Optional env: APP_VERSION (default 0.1.0), SENTRY_RELEASE (git SHA or semver) for Sentry grouping.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
TAG="${1:-botforge-ai-api:local}"
VER="${APP_VERSION:-0.1.0}"
REL="${SENTRY_RELEASE:-}"
docker build -t "$TAG" \
  --build-arg "APP_VERSION=$VER" \
  --build-arg "SENTRY_RELEASE=$REL" \
  .
