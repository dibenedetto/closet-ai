"""Setup SQLAlchemy per SQLite.

Per l'MVP usiamo `Base.metadata.create_all()` invece di Alembic: il modello dati
è ancora in evoluzione e l'overhead delle migrazioni non è giustificato. Quando
lo schema si stabilizza si introdurrà Alembic.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, ensure_dirs

# `check_same_thread=False` è richiesto da SQLite quando l'engine è condiviso
# tra i thread del pool di FastAPI.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Base dichiarativa condivisa da tutti i modelli ORM."""


def init_db() -> None:
    """Crea le directory dati e tutte le tabelle mancanti."""
    ensure_dirs()
    # Import differito per assicurare che i modelli siano registrati su Base.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency FastAPI: fornisce una sessione e la chiude a fine richiesta."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
