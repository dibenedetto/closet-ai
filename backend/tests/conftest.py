"""Fixture pytest comuni.

Imposta path isolati per storage e DB *prima* che i moduli dell'app vengano
importati, forza il classificatore mock (i test non devono scaricare 600MB
di pesi né dipendere dalla GPU), e fornisce un `client` FastAPI per ogni
test con DB SQLite dedicato, cartella `items/` dedicata e collection
ChromaDB isolata.
"""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

# Isolamento di sessione, eseguito al collection-time del conftest, prima di
# qualunque `import app.*`.
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="closetai_pytest_"))
os.environ.setdefault("CLOSETAI_DATA_DIR", str(_TEST_ROOT))
os.environ.setdefault("CLOSETAI_DB_PATH", str(_TEST_ROOT / "closetai.db"))
os.environ.setdefault("CLOSETAI_CHROMA_DIR", str(_TEST_ROOT / "chroma"))
os.environ.setdefault(
    "CLOSETAI_DATABASE_URL",
    f"sqlite:///{(_TEST_ROOT / 'closetai.db').as_posix()}",
)
# I test usano il classificatore mock: deterministico, niente download.
os.environ["CLOSETAI_CLASSIFIER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@pytest.fixture
def items_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cartella `items/` isolata per il test; sostituisce `ITEMS_DIR` in tutti
    i moduli che la importano."""
    d = tmp_path / "items"
    d.mkdir()
    monkeypatch.setattr("app.routers.items.ITEMS_DIR", d)
    monkeypatch.setattr("app.routers.ai.ITEMS_DIR", d)
    return d


@pytest.fixture
def chroma_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Collection ChromaDB isolata per il test, con singleton resettato."""
    from app.services import embeddings

    d = tmp_path / "chroma"
    d.mkdir()
    monkeypatch.setattr(embeddings, "CHROMA_DIR", d)
    embeddings.reset_embedding_store_cache()
    yield d
    embeddings.reset_embedding_store_cache()


@pytest.fixture(autouse=True)
def _reset_classifier_singleton() -> Iterator[None]:
    """Forza la ricreazione del classifier per ogni test, così il monkeypatch
    di env var ha effetto anche dopo la prima invocazione."""
    from app.ml import classifier

    classifier.reset_classifier_cache()
    yield
    classifier.reset_classifier_cache()


@pytest.fixture(autouse=True)
def _reset_tryon_singleton() -> Iterator[None]:
    """Reset del backend try-on tra test (evita leak del FakeBackend)."""
    from app.services import tryon

    tryon.reset_backend_cache()
    yield
    tryon.reset_backend_cache()


@pytest.fixture
def tryon_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cartella try-on isolata per test; patch su entrambi i moduli che la usano."""
    d = tmp_path / "tryon"
    d.mkdir()
    monkeypatch.setattr("app.services.tryon.TRYON_DIR", d)
    monkeypatch.setattr("app.routers.ai.TRYON_DIR", d)
    return d


@pytest.fixture
def client(tmp_path: Path, items_dir: Path, chroma_dir: Path) -> Iterator[TestClient]:
    """TestClient con DB SQLite isolato, cartella immagini e Chroma isolate."""
    from app.db import Base, get_db
    from app.main import app

    # `items_dir`/`chroma_dir` sono dipendenze implicite delle fixture: l'argomento
    # non è usato direttamente ma garantisce il setup. Suppress linter.
    _ = items_dir, chroma_dir

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
