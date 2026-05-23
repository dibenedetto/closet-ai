"""Setup SQLAlchemy per SQLite.

Per l'MVP usiamo `Base.metadata.create_all()` invece di Alembic: il modello dati
è ancora in evoluzione e l'overhead delle migrazioni non è giustificato. Quando
lo schema si stabilizza si introdurrà Alembic.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, ensure_dirs

# `check_same_thread=False` è richiesto da SQLite quando l'engine è condiviso
# tra i thread del pool di FastAPI.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
    """Abilita ON DELETE CASCADE per SQLite (di default è OFF)."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    """Base dichiarativa condivisa da tutti i modelli ORM."""


def init_db() -> None:
    """Crea le directory dati, tutte le tabelle mancanti, e applica le
    micro-migrazioni idempotenti per i DB esistenti (vedi ADR-002)."""
    ensure_dirs()
    # Import differito per assicurare che i modelli siano registrati su Base.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


# Colonne aggiunte dopo Fase 1, gestite con ALTER TABLE idempotente
# fino all'introduzione di Alembic (vedi ADR-002).
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "items": [
        ("classification_confidence", "FLOAT"),
        ("condition", "VARCHAR(16)"),
        ("retired_at", "DATETIME"),
        ("description", "VARCHAR(1024)"),
    ],
}


def _apply_lightweight_migrations() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, cols in _ADDED_COLUMNS.items():
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, sql_type in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


def get_db() -> Generator[Session, None, None]:
    """Dependency FastAPI: fornisce una sessione e la chiude a fine richiesta."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
