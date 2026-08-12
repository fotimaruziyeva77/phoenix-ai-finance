#!/usr/bin/env bash
# Start the API via main.py (Uvicorn). All behaviour is driven by environment / .env.
# For staging/production set APP_RELOAD=false (enforced by Settings when APP_ENVIRONMENT is staging or production).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec python main.py
