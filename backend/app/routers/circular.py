"""Endpoint per il modulo circolare (Fase 5):

- diagnosi condizione (heuristic + override manuale)
- suggerimenti azioni circolari + stima CO₂
- registrazione esecuzione di un'azione (ritira il capo se applicabile)
- tutorial di riparazione per difetti comuni
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ACTION_TYPES, Item, ItemAction
from app.schemas import (
    ActionSuggestion,
    ConditionUpdate,
    DiagnoseResponse,
    ItemActionCreate,
    ItemActionRead,
    RepairTutorialOut,
    SupportedDefects,
)
from app.services import circular as circular_service
from app.services import repair_tutorials
from app.services.condition import CONDITIONS, diagnose, now_utc

router = APIRouter(tags=["circular"])


def _require_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} non trovato.",
        )
    return item


@router.post("/items/{item_id}/diagnose", response_model=DiagnoseResponse)
def diagnose_item(item_id: int, db: Session = Depends(get_db)) -> DiagnoseResponse:
    """Esegue la diagnosi euristica e persistela su `Item.condition` (se non era
    già settata manualmente). Ritorna anche le azioni suggerite e la stima CO₂."""
    item = _require_item(db, item_id)
    result = diagnose(db, item)

    if item.condition is None:
        item.condition = result.condition
        db.commit()
        db.refresh(item)

    # Le suggestion usano la condition *attuale* (che può essere stata override).
    suggestions = [
        ActionSuggestion(
            action_type=s.action_type,  # type: ignore[arg-type]
            co2_saved_kg=s.co2_saved_kg,
            rationale=s.rationale,
            priority=s.priority,
        )
        for s in circular_service.suggest_actions(item.category, item.condition)
    ]

    return DiagnoseResponse(
        item_id=item.id,
        condition=item.condition,  # type: ignore[arg-type]
        wear_count=result.wear_count,
        days_owned=result.days_owned,
        rationale=result.rationale,
        source=result.source,
        confidence=result.confidence,
        defect=result.defect,
        tutorial=result.tutorial,
        suggestions=suggestions,
    )


@router.put("/items/{item_id}/condition", response_model=DiagnoseResponse)
def set_condition(
    item_id: int, payload: ConditionUpdate, db: Session = Depends(get_db)
) -> DiagnoseResponse:
    """Override manuale della condizione del capo."""
    if payload.condition not in CONDITIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"condition non valida: {payload.condition!r}",
        )
    item = _require_item(db, item_id)
    item.condition = payload.condition
    db.commit()
    db.refresh(item)
    return diagnose_item(item_id, db)


@router.post(
    "/items/{item_id}/actions",
    response_model=ItemActionRead,
    status_code=status.HTTP_201_CREATED,
)
def register_action(
    item_id: int, payload: ItemActionCreate, db: Session = Depends(get_db)
) -> ItemAction:
    """Registra l'esecuzione di un'azione circolare sul capo.

    Se l'azione è "di ritiro" (donazione/swap/vendita/riciclo) il capo viene
    marcato come `retired_at = now`. La riparazione non ritira il capo.
    """
    item = _require_item(db, item_id)
    if payload.action_type not in ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"action_type non valido: {payload.action_type!r}",
        )

    co2 = (
        payload.co2_saved_kg
        if payload.co2_saved_kg is not None
        else circular_service.estimate_co2_saved(item.category, payload.action_type)
    )

    action = ItemAction(
        item_id=item.id,
        action_type=payload.action_type,
        notes=payload.notes,
        co2_saved_kg=co2,
    )
    db.add(action)

    if circular_service.is_retiring(payload.action_type) and item.retired_at is None:
        item.retired_at = now_utc()

    db.commit()
    db.refresh(action)
    return action


@router.get("/items/{item_id}/actions", response_model=list[ItemActionRead])
def list_actions(item_id: int, db: Session = Depends(get_db)) -> list[ItemAction]:
    _require_item(db, item_id)
    stmt = (
        select(ItemAction)
        .where(ItemAction.item_id == item_id)
        .order_by(ItemAction.created_at.desc(), ItemAction.id.desc())
    )
    return list(db.execute(stmt).scalars())


@router.delete("/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action(action_id: int, db: Session = Depends(get_db)) -> None:
    """Elimina un'azione. Se era l'ultima azione "di ritiro" sul capo, il capo
    viene riattivato (`retired_at = NULL`)."""
    action = db.get(ItemAction, action_id)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} non trovata.",
        )
    item_id = action.item_id
    was_retiring = circular_service.is_retiring(action.action_type)
    db.delete(action)

    if was_retiring:
        # Se non resta nessuna altra azione di ritiro su questo item, riattiva.
        remaining = db.execute(
            select(ItemAction).where(
                ItemAction.item_id == item_id,
                ItemAction.action_type.in_(list(circular_service.RETIRING_ACTIONS)),
                ItemAction.id != action_id,
            )
        ).first()
        if remaining is None:
            item = db.get(Item, item_id)
            if item is not None:
                item.retired_at = None

    db.commit()


@router.get("/repair-tutorials/defects", response_model=SupportedDefects)
def list_defects() -> SupportedDefects:
    return SupportedDefects(defects=list(repair_tutorials.DEFECTS))


@router.get("/repair-tutorials", response_model=RepairTutorialOut)
def get_repair_tutorial(
    defect: str | None = Query(default=None),
    category: str | None = Query(default=None),
) -> RepairTutorialOut:
    t = repair_tutorials.get_tutorial(defect, category=category)
    return RepairTutorialOut(
        defect=t.defect,
        category=t.category,
        title=t.title,
        difficulty=t.difficulty,
        time_minutes=t.time_minutes,
        materials=list(t.materials),
        steps=list(t.steps),
        source=t.source,
        llm_enrichment_available=repair_tutorials.llm_enrichment_available(),
    )
