"""Configurazione globale dell'app.

Espone path canonici (root del progetto, cartella dati, DB SQLite) calcolati a
partire dalla posizione di questo file, così che siano indipendenti dal cwd
con cui viene lanciato uvicorn.
"""

from __future__ import annotations

import os
from pathlib import Path

# backend/app/config.py  ->  backend/app  ->  backend  ->  <root>
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

DATA_DIR: Path = Path(os.environ.get("CLOSETAI_DATA_DIR", PROJECT_ROOT / "data"))
ITEMS_DIR: Path = DATA_DIR / "items"
DB_PATH: Path = Path(os.environ.get("CLOSETAI_DB_PATH", DATA_DIR / "closetai.db"))

DATABASE_URL: str = os.environ.get(
    "CLOSETAI_DATABASE_URL",
    f"sqlite:///{DB_PATH.as_posix()}",
)

# Origini CORS consentite (frontend di sviluppo Vite + eventuali alias locali).
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def ensure_dirs() -> None:
    """Crea le directory necessarie per lo storage locale."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
