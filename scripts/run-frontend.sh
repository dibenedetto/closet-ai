#!/usr/bin/env bash
# Avvia il frontend Vite in modalità dev (default http://localhost:5173)
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRONTEND_DIR="$( cd "$SCRIPT_DIR/../frontend" && pwd )"

if [ ! -f "$FRONTEND_DIR/package.json" ]; then
  echo "!! Frontend non inizializzato in $FRONTEND_DIR (manca package.json)."
  echo "   Esegui prima ./scripts/setup.sh oppure inizializza Vite+React."
  exit 1
fi

cd "$FRONTEND_DIR"
exec npm run dev
