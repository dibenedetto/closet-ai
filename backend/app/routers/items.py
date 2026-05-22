"""CRUD endpoints per i capi del guardaroba."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
    ITEMS_DIR,
    MAX_UPLOAD_SIZE,
)
from app.db import get_db
from app.ml.classifier import ClassificationResult, get_classifier
from app.models import Item
from app.schemas import ItemRead
from app.services.embeddings import get_embedding_store

router = APIRouter(prefix="/items", tags=["items"])
log = logging.getLogger(__name__)

_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _validate_and_persist_upload(upload: UploadFile) -> str:
    """Valida l'upload e lo scrive in `ITEMS_DIR`. Ritorna il filename salvato."""
    if upload.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tipo file non supportato: {upload.content_type!r}. "
                f"Ammessi: {sorted(ALLOWED_IMAGE_CONTENT_TYPES)}."
            ),
        )

    original_ext = Path(upload.filename or "").suffix.lower()
    if original_ext and original_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Estensione non supportata: {original_ext!r}. "
                f"Ammesse: {sorted(ALLOWED_IMAGE_EXTENSIONS)}."
            ),
        )

    ext = original_ext or _CONTENT_TYPE_TO_EXT[upload.content_type]
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = ITEMS_DIR / filename

    written = 0
    chunk_size = 1024 * 1024
    try:
        with dest.open("wb") as out:
            while True:
                chunk = upload.file.read(chunk_size)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_SIZE:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"File troppo grande: limite {MAX_UPLOAD_SIZE} byte.",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    finally:
        upload.file.close()

    return filename


def _safe_classify(image_path: Path) -> ClassificationResult:
    """Wrapper attorno al classifier che non solleva: in caso di errore
    ritorna un risultato vuoto e logga. Mantiene il POST robusto."""
    try:
        return get_classifier().classify(image_path)
    except Exception:
        log.warning("Classificazione fallita per %s", image_path.name, exc_info=True)
        return ClassificationResult(category=None, color=None, embedding=None, confidence=None)


def _upsert_embedding(item: Item, embedding: list[float] | None) -> None:
    """Salva l'embedding nella collection ChromaDB se presente."""
    if embedding is None:
        return
    try:
        get_embedding_store().upsert(
            item.id,
            embedding,
            metadata={"category": item.category, "color": item.color},
        )
    except Exception:
        log.warning("Upsert embedding fallito per item=%s", item.id, exc_info=True)


def _delete_embedding(item_id: int) -> None:
    try:
        get_embedding_store().delete(item_id)
    except Exception:
        log.warning("Delete embedding fallito per item=%s", item_id, exc_info=True)


def _get_item_or_404(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} non trovato.",
        )
    return item


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    name: str = Form(..., min_length=1, max_length=200),
    price: float | None = Form(default=None, ge=0),
    purchase_date: date | None = Form(default=None),
    category: str | None = Form(default=None, max_length=64),
    color: str | None = Form(default=None, max_length=32),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Item:
    filename = _validate_and_persist_upload(image)
    file_path = ITEMS_DIR / filename

    result = _safe_classify(file_path)

    item = Item(
        name=name,
        category=category or result.category,
        color=color or result.color,
        image_path=filename,
        price=price,
        purchase_date=purchase_date,
        classification_confidence=result.confidence,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    _upsert_embedding(item, result.embedding)
    return item


@router.get("", response_model=list[ItemRead])
def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Item]:
    stmt = select(Item).order_by(Item.created_at.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    return _get_item_or_404(db, item_id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> Response:
    item = _get_item_or_404(db, item_id)

    image_filename = item.image_path
    db.delete(item)
    db.commit()

    if image_filename:
        file_path = ITEMS_DIR / image_filename
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            log.warning("Impossibile eliminare il file %s", file_path, exc_info=True)

    _delete_embedding(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{item_id}/image")
def get_item_image(item_id: int, db: Session = Depends(get_db)) -> FileResponse:
    item = _get_item_or_404(db, item_id)
    if not item.image_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} non ha un'immagine associata.",
        )

    file_path = ITEMS_DIR / item.image_path
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File immagine mancante sul filesystem.",
        )

    return FileResponse(file_path)


@router.post("/{item_id}/reclassify", response_model=ItemRead)
def reclassify_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    """Ri-esegue la classificazione del capo e aggiorna `category`, `color`,
    `classification_confidence` e l'embedding in ChromaDB."""
    item = _get_item_or_404(db, item_id)
    if not item.image_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item {item_id} non ha un'immagine: impossibile classificare.",
        )

    file_path = ITEMS_DIR / item.image_path
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File immagine mancante sul filesystem.",
        )

    result = _safe_classify(file_path)
    item.category = result.category
    item.color = result.color
    item.classification_confidence = result.confidence
    db.commit()
    db.refresh(item)

    _upsert_embedding(item, result.embedding)
    return item
