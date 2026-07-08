"""Endpoint per le feature di AI generativa (Fase 6+):

- `POST /items/{id}/describe` → genera descrizione narrativa LLM
- `POST /items/{id}/try-on`    → try-on virtuale via diffusion (multipart)
- `GET  /items/{id}/try-on/{filename}` → serve l'immagine generata
- `GET  /tryon/status`         → ispeziona il backend try-on
- `GET  /stats/coach`          → messaggio AI sostenibilità
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ITEMS_DIR,
    LLM_MODEL,
    MAX_UPLOAD_SIZE,
    TRYON_BACKEND,
    TRYON_DIR,
    TRYON_MODEL,
)
from app.db import get_db
from app.models import Item
from app.schemas import CoachOut, ItemDescriptionOut, TryOnOut, TryOnStatus
from app.services import coach as coach_service
from app.services import descriptions, llm, tryon

router = APIRouter(tags=["ai"])
log = logging.getLogger(__name__)


def _require_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} non trovato.",
        )
    return item


# ============================================================================
# Descrizione narrativa
# ============================================================================


@router.post("/items/{item_id}/describe", response_model=ItemDescriptionOut)
def describe_item(
    item_id: int,
    regenerate: bool = Query(False, description="Forza la rigenerazione anche se presente"),
    db: Session = Depends(get_db),
) -> ItemDescriptionOut:
    item = _require_item(db, item_id)

    if item.description and not regenerate:
        return ItemDescriptionOut(
            item_id=item.id,
            description=item.description,
            generated=False,
            model=None,
        )

    text = descriptions.generate_item_description(item, db)
    if text is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "LLM non configurato o non raggiungibile. Imposta una API key "
                "(ANTHROPIC_API_KEY / OPENAI_API_KEY) oppure CLOSETAI_LLM_MODEL=ollama/<m>."
            ),
        )

    item.description = text
    db.commit()
    db.refresh(item)
    return ItemDescriptionOut(
        item_id=item.id,
        description=item.description,
        generated=True,
        model=LLM_MODEL,
    )


# ============================================================================
# Coach AI sostenibilità
# ============================================================================


@router.get("/stats/coach", response_model=CoachOut)
def get_coach(
    ghost_after_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> CoachOut:
    msg = coach_service.generate_coach_message(db, ghost_after_days=ghost_after_days)
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM non configurato. Vedi docs/architecture.md (ADR-008).",
        )
    return CoachOut(
        text=msg.text, facts=msg.facts, model=msg.model, cached=msg.cached
    )


# ============================================================================
# Try-on virtuale
# ============================================================================


@router.get("/tryon/status", response_model=TryOnStatus)
def get_tryon_status() -> TryOnStatus:
    backend = tryon.get_backend()
    return TryOnStatus(
        backend=backend.name,
        available=backend.is_available(),
        model=TRYON_MODEL if backend.is_available() else None,
    )


@router.post("/items/{item_id}/try-on", response_model=TryOnOut)
def try_on(
    item_id: int,
    portrait: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TryOnOut:
    item = _require_item(db, item_id)
    if not item.image_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item {item_id} non ha un'immagine associata.",
        )

    if portrait.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Formato ritratto non supportato: {portrait.content_type!r}. "
                f"Ammessi: {sorted(ALLOWED_IMAGE_CONTENT_TYPES)}."
            ),
        )

    portrait_bytes = portrait.file.read(MAX_UPLOAD_SIZE + 1)
    if len(portrait_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Ritratto troppo grande: limite {MAX_UPLOAD_SIZE} byte.",
        )

    garment_path = ITEMS_DIR / item.image_path
    if not garment_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File immagine del capo mancante sul filesystem.",
        )

    try:
        result = tryon.run_tryon(
            portrait_bytes,
            garment_path,
            item_name=item.name,
            category=item.category,
            color=item.color,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        log.exception("Errore try-on per item=%s", item.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generazione fallita: {e}",
        ) from e

    return TryOnOut(
        item_id=item.id,
        filename=result.filename,
        url=f"/api/v1/items/{item.id}/try-on/{result.filename}",
        backend=result.backend,
        prompt=result.prompt,
        elapsed_ms=result.elapsed_ms,
    )


@router.get("/items/{item_id}/try-on/{filename}")
def get_tryon_image(
    item_id: int, filename: str, db: Session = Depends(get_db)
) -> FileResponse:
    """Serve l'immagine try-on. Senza tracking esplicito DB: il filename UUID
    funge da capability token."""
    _ = _require_item(db, item_id)
    # Defense in depth: il filename viene da UUID generato server-side, ma
    # rifiutiamo path traversal per sicurezza.
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename non valido."
        )
    file_path = TRYON_DIR / filename
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Immagine try-on non trovata.",
        )
    return FileResponse(file_path, media_type="image/png")


# ============================================================================
# Introspection LLM (debug / UI)
# ============================================================================


@router.get("/llm/status")
def get_llm_status() -> dict:
    """Stato dell'integrazione LLM (per la UI: 'Coach' e bottoni AI visibili
    solo se configurato)."""
    return {
        "configured": llm.is_llm_configured(),
        "model": LLM_MODEL,
        "tryon_backend": TRYON_BACKEND,
    }
