#!/usr/bin/env bash
# Avvia il backend FastAPI in modalità reload su http://localhost:8000
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/../backend" && pwd )"

cd "$BACKEND_DIR"
exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
