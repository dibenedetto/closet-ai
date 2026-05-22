"""Endpoint per la registrazione e gestione degli eventi di utilizzo (wear)."""

from __future__ import annotations

import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Item, WearEvent
from app.schemas import WearEventBatchCreate, WearEventCreate, WearEventRead

router = APIRouter(tags=["wear"])
log = logging.getLogger(__name__)


def _today() -> date_type:
    return date_type.today()


def _require_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} non trovato.",
        )
    return item


@router.post(
    "/items/{item_id}/wear",
    response_model=WearEventRead,
    status_code=status.HTTP_201_CREATED,
)
def log_wear(
    item_id: int,
    payload: WearEventCreate | None = None,
    db: Session = Depends(get_db),
) -> WearEvent:
    """Registra un utilizzo del capo. Se `worn_on` non è fornita, usa oggi."""
    _require_item(db, item_id)
    payload = payload or WearEventCreate()
    event = WearEvent(
        item_id=item_id,
        worn_on=payload.worn_on or _today(),
        occasion=payload.occasion,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/items/{item_id}/wears", response_model=list[WearEventRead])
def list_wears(item_id: int, db: Session = Depends(get_db)) -> list[WearEvent]:
    _require_item(db, item_id)
    stmt = (
        select(WearEvent)
        .where(WearEvent.item_id == item_id)
        .order_by(WearEvent.worn_on.desc(), WearEvent.id.desc())
    )
    return list(db.execute(stmt).scalars())


@router.post(
    "/wear-events/batch",
    response_model=list[WearEventRead],
    status_code=status.HTTP_201_CREATED,
)
def batch_log_wears(
    payload: WearEventBatchCreate,
    db: Session = Depends(get_db),
) -> list[WearEvent]:
    """Registra più eventi in una singola transazione.

    Tutti gli `item_id` devono esistere: in caso contrario l'intera operazione
    fallisce con 404. Le date mancanti diventano oggi.
    """
    item_ids = sorted({e.item_id for e in payload.events})
    existing = (
        db.execute(select(Item.id).where(Item.id.in_(item_ids))).scalars().all()
    )
    missing = set(item_ids) - set(existing)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item non trovati: {sorted(missing)}",
        )

    today = _today()
    events = [
        WearEvent(
            item_id=e.item_id,
            worn_on=e.worn_on or today,
            occasion=e.occasion,
        )
        for e in payload.events
    ]
    db.add_all(events)
    db.commit()
    for ev in events:
        db.refresh(ev)
    return events


@router.delete("/wear-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wear(event_id: int, db: Session = Depends(get_db)) -> None:
    event = db.get(WearEvent, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WearEvent {event_id} non trovato.",
        )
    db.delete(event)
    db.commit()
