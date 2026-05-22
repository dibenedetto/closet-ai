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
CHROMA_DIR: Path = Path(os.environ.get("CLOSETAI_CHROMA_DIR", DATA_DIR / "chroma"))
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

# Coordinate di default per il meteo (Pisa, IT). Sovrascrivibili via env o
# query parameter su `GET /outfits/suggest`.
DEFAULT_LAT: float = float(os.environ.get("CLOSETAI_DEFAULT_LAT", "43.7228"))
DEFAULT_LON: float = float(os.environ.get("CLOSETAI_DEFAULT_LON", "10.4017"))

# Vincoli upload immagini
MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
ALLOWED_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp"}
)


def ensure_dirs() -> None:
    """Crea le directory necessarie per lo storage locale."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
