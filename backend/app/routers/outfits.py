"""Endpoint per le proposte di outfit e per il feedback utente."""

from __future__ import annotations

import json
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import DEFAULT_LAT, DEFAULT_LON
from app.db import get_db
from app.models import Item, OutfitFeedback
from app.schemas import (
    OutfitFeedbackCreate,
    OutfitFeedbackRead,
    OutfitSuggestion,
    OutfitSuggestResponse,
    WeatherSummary,
)
from app.services import weather as weather_service
from app.services.recommender import suggest_outfits

router = APIRouter(prefix="/outfits", tags=["outfits"])


def _today() -> date_type:
    return date_type.today()


@router.get("/suggest", response_model=OutfitSuggestResponse)
def suggest(
    target_date: date_type | None = Query(default=None, alias="date"),
    count: int = Query(3, ge=1, le=10),
    latitude: float = Query(default=DEFAULT_LAT, ge=-90, le=90, alias="lat"),
    longitude: float = Query(default=DEFAULT_LON, ge=-180, le=180, alias="lon"),
    db: Session = Depends(get_db),
) -> OutfitSuggestResponse:
    """Suggerisce `count` outfit per la data indicata (default oggi),
    condizionati dal meteo alle coordinate richieste (default: Pisa)."""
    target = target_date or _today()
    weather = weather_service.fetch_weather(
        target, latitude=latitude, longitude=longitude
    )
    proposals = suggest_outfits(db, weather, count=count)

    # Mappiamo gli item_id a record Item con un singolo round-trip.
    all_ids: set[int] = set()
    for p in proposals:
        all_ids.update(p.item_ids)
    items_by_id: dict[int, Item] = {
        i.id: i
        for i in db.query(Item).filter(Item.id.in_(all_ids)).all()  # type: ignore[arg-type]
    } if all_ids else {}

    outfits = [
        OutfitSuggestion(
            items=[items_by_id[i] for i in p.item_ids if i in items_by_id],  # type: ignore[list-item]
            score=p.score,
            color_score=p.color_score,
            weather_score=p.weather_score,
            ghost_bonus=p.ghost_bonus,
            rationale=p.rationale,
        )
        for p in proposals
    ]

    return OutfitSuggestResponse(
        target_date=target,
        weather=WeatherSummary(
            target_date=weather.target_date,
            temperature_c=weather.temperature_c,
            precipitation_mm=weather.precipitation_mm,
            wind_kmh=weather.wind_kmh,
            weather_code=weather.weather_code,
            source=weather.source,
        ),
        outfits=outfits,
    )


@router.post(
    "/feedback",
    response_model=OutfitFeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    payload: OutfitFeedbackCreate, db: Session = Depends(get_db)
) -> OutfitFeedbackRead:
    """Salva un like/dislike su un outfit (lista di `item_ids`).

    Nessun controllo di esistenza degli item: se un capo viene eliminato in
    futuro, i feedback storici restano comunque interpretabili.
    """
    if payload.rating == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="rating deve essere +1 (like) o -1 (dislike), non 0.",
        )
    fb = OutfitFeedback(
        item_ids_json=json.dumps(sorted(set(payload.item_ids))),
        rating=payload.rating,
        occasion=payload.occasion,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return OutfitFeedbackRead(
        id=fb.id,
        item_ids=fb.item_ids,
        rating=fb.rating,
        occasion=fb.occasion,
        created_at=fb.created_at,
    )


@router.get("/feedback", response_model=list[OutfitFeedbackRead])
def list_feedback(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[OutfitFeedbackRead]:
    rows = (
        db.query(OutfitFeedback)
        .order_by(OutfitFeedback.id.desc())
        .limit(limit)
        .all()
    )
    return [
        OutfitFeedbackRead(
            id=r.id,
            item_ids=r.item_ids,
            rating=r.rating,
            occasion=r.occasion,
            created_at=r.created_at,
        )
        for r in rows
    ]
