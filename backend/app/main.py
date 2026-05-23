"""Entry point FastAPI di ClosetAI.

Espone tutte le API sotto il prefisso `/api/v1`. Il DB SQLite viene inizializzato
all'avvio tramite il context manager `lifespan`. Su `/test/` è montata una
pagina HTML di test che esercita le API CRUD.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS
from app.db import init_db
from app.routers import circular, health, items, outfits, stats, wear

API_PREFIX = "/api/v1"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ClosetAI",
    description="Backend API di ClosetAI — catalogazione capi e tracking utilizzo.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(items.router, prefix=API_PREFIX)
app.include_router(wear.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(outfits.router, prefix=API_PREFIX)
app.include_router(circular.router, prefix=API_PREFIX)

if STATIC_DIR.is_dir():
    app.mount("/test", StaticFiles(directory=STATIC_DIR, html=True), name="test")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Comodo redirect dalla root verso la pagina di test."""
    return RedirectResponse(url="/test/")
