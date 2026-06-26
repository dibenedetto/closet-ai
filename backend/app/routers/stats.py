"""Endpoint per le statistiche di utilizzo: per item, per guardaroba, ghosts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Item
from app.schemas import (
    GapAnalysisOut,
    GhostItem,
    ImpactStats,
    ItemStats,
    WardrobeStats,
)
from app.services.gap_analysis import analyze_wardrobe
from app.services.stats import (
    DEFAULT_GHOST_AFTER_DAYS,
    compute_impact_stats,
    compute_item_stats,
    compute_wardrobe_stats,
    list_ghost_items,
)

router = APIRouter(tags=["stats"])


@router.get("/items/{item_id}/stats", response_model=ItemStats)
def get_item_stats(
    item_id: int,
    ghost_after_days: int = Query(DEFAULT_GHOST_AFTER_DAYS, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} non trovato.",
        )
    return compute_item_stats(db, item, ghost_after_days=ghost_after_days)


@router.get("/stats/wardrobe", response_model=WardrobeStats)
def get_wardrobe_stats(
    ghost_after_days: int = Query(DEFAULT_GHOST_AFTER_DAYS, ge=1, le=365),
    top_n: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:
    return compute_wardrobe_stats(db, ghost_after_days=ghost_after_days, top_n=top_n)


@router.get("/stats/ghosts", response_model=list[GhostItem])
def get_ghost_items(
    ghost_after_days: int = Query(DEFAULT_GHOST_AFTER_DAYS, ge=1, le=365),
    db: Session = Depends(get_db),
) -> list[dict]:
    return list_ghost_items(db, ghost_after_days=ghost_after_days)


@router.get("/stats/impact", response_model=ImpactStats)
def get_impact_stats(db: Session = Depends(get_db)) -> dict:
    """Statistiche aggregate del modulo circolare: totale azioni eseguite,
    kg CO₂ evitati, breakdown per tipo di azione, capi ritirati e riparati."""
    return compute_impact_stats(db)


@router.get("/stats/gap-analysis", response_model=GapAnalysisOut)
def get_gap_analysis(db: Session = Depends(get_db)) -> GapAnalysisOut:
    """Analizza la composizione del guardaroba con la rete neurale addestrata
    (fallback a regole se i pesi non ci sono) e individua i vuoti funzionali
    con raccomandazioni d'acquisto consapevole."""
    a = analyze_wardrobe(db)
    return GapAnalysisOut(
        total_items=a.total_items,
        counts_by_category=a.counts_by_category,
        n_colors=a.n_colors,
        has_neutral=a.has_neutral,
        ghost_ratio=a.ghost_ratio,
        balanced=a.balanced,
        gaps=[
            {"code": g.code, "label": g.label, "advice": g.advice, "probability": g.probability}
            for g in a.gaps
        ],
        source=a.source,
    )
