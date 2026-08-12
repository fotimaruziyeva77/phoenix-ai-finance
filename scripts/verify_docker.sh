#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example to .env first." >&2
  exit 1
fi

echo "== docker compose ps =="
docker compose ps

echo ""
echo "== postgres (pg_isready) =="
docker compose exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo ""
echo "== redis (PING) =="
docker compose exec -T redis redis-cli ping

echo ""
echo "== backend: in-container stack script =="
docker compose exec -T backend python scripts/verify_stack.py

PUBLISH_PORT="$(grep -E '^APP_PUBLISH_PORT=' .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" | head -1 || true)"
PUBLISH_PORT="${PUBLISH_PORT:-8000}"
HEALTH="http://127.0.0.1:${PUBLISH_PORT}/api/v1/health"
echo ""
echo "== API health (${HEALTH}) =="
curl -fsS "$HEALTH" | grep -q '"status":"ok"' || { curl -fsS "$HEALTH"; exit 1; }
echo "api_health: ok"

echo ""
echo "All checks passed."
