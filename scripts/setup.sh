#!/usr/bin/env bash
# Setup ClosetAI su macOS / Linux:
#   - installa uv se mancante
#   - installa Python 3.14 via uv
#   - sincronizza le dipendenze del backend
#   - installa le dipendenze del frontend (se presente)
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "==> ClosetAI setup (root: $ROOT_DIR)"

if ! command -v uv >/dev/null 2>&1; then
  echo "==> uv non trovato, installo via script ufficiale"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Aggiunge uv al PATH della sessione corrente
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
else
  echo "==> uv già installato: $(uv --version)"
fi

echo "==> Installo Python 3.14 via uv"
uv python install 3.14

if [ -f "$BACKEND_DIR/pyproject.toml" ]; then
  echo "==> Sincronizzo dipendenze backend"
  ( cd "$BACKEND_DIR" && uv sync )
else
  echo "==> Backend non ancora inizializzato (manca pyproject.toml) — salto uv sync"
fi

if [ -f "$FRONTEND_DIR/package.json" ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "==> Installo dipendenze frontend"
    ( cd "$FRONTEND_DIR" && npm install )
  else
    echo "!! npm non trovato. Installa Node.js >= 20 da https://nodejs.org/ e riesegui."
    exit 1
  fi
else
  echo "==> Frontend non ancora inizializzato (manca package.json) — salto npm install"
fi

echo "==> Setup completato."
