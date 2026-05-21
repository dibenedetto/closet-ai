"""Fixture pytest comuni.

Imposta path isolati per storage e DB *prima* che i moduli dell'app vengano
importati, e fornisce un `client` FastAPI per ogni test con DB SQLite dedicato
e cartella `items/` dedicata.
"""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

# Isolamento di sessione: si scrive solo dentro la tempdir, mai nel repo.
# Eseguito al collection-time del conftest, prima di qualunque import di `app`.
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="closetai_pytest_"))
os.environ.setdefault("CLOSETAI_DATA_DIR", str(_TEST_ROOT))
os.environ.setdefault("CLOSETAI_DB_PATH", str(_TEST_ROOT / "closetai.db"))
os.environ.setdefault(
    "CLOSETAI_DATABASE_URL",
    f"sqlite:///{(_TEST_ROOT / 'closetai.db').as_posix()}",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@pytest.fixture
def items_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cartella `items/` isolata per il test; sostituisce `ITEMS_DIR` nel router."""
    d = tmp_path / "items"
    d.mkdir()
    monkeypatch.setattr("app.routers.items.ITEMS_DIR", d)
    return d


@pytest.fixture
def client(tmp_path: Path, items_dir: Path) -> Iterator[TestClient]:
    """TestClient con DB SQLite isolato e cartella immagini isolata."""
    from app.db import Base, get_db
    from app.main import app

    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def png() -> Callable[..., bytes]:
    """Factory che genera bytes PNG con colore e dimensione configurabili."""

    def _make(
        rgb: tuple[int, int, int] = (40, 80, 200),
        size: tuple[int, int] = (64, 64),
    ) -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", size, rgb).save(buf, format="PNG")
        return buf.getvalue()

    return _make
