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

# AI generativa via litellm: supporta provider cloud (Anthropic, OpenAI) e
# locali (Ollama, vLLM, HF Inference). Vedi ADR-008 in docs/architecture.md.
LLM_MODEL: str = os.environ.get("CLOSETAI_LLM_MODEL", "claude-haiku-4-5")
LLM_TIMEOUT: float = float(os.environ.get("CLOSETAI_LLM_TIMEOUT", "20"))
LLM_MAX_TOKENS: int = int(os.environ.get("CLOSETAI_LLM_MAX_TOKENS", "800"))
LLM_CACHE_TTL_HOURS: int = int(os.environ.get("CLOSETAI_LLM_CACHE_TTL_HOURS", "24"))

# Diagnosi stato del capo. Strategia di selezione del backend:
#   "auto" (default) → prova clip-mlp, poi heuristic (primo disponibile)
#   "clip-mlp"       → forza la testa MLP su embedding CLIP (richiede pesi)
#   "heuristic"      → forza l'euristica wear_count + età (sempre disponibile)
# Vedi ADR-009 in docs/architecture.md.
CONDITION_BACKEND: str = os.environ.get("CLOSETAI_CONDITION_BACKEND", "auto")

# Try-on virtuale via diffusers: backend "diffusers" (locale) o "disabled".
# Default disabled per non scaricare ~5GB di pesi senza richiesta esplicita.
TRYON_BACKEND: str = os.environ.get("CLOSETAI_TRYON_BACKEND", "disabled")
TRYON_MODEL: str = os.environ.get(
    "CLOSETAI_TRYON_MODEL", "stabilityai/stable-diffusion-2-inpainting"
)
TRYON_DIR: Path = Path(os.environ.get("CLOSETAI_TRYON_DIR", DATA_DIR / "tryon"))

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
    TRYON_DIR.mkdir(parents=True, exist_ok=True)
