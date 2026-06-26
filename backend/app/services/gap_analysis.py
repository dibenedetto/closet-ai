"""Gap analysis del guardaroba reale dell'utente.

Estrae le feature aggregate dal guardaroba (dai record `Item` + `WearEvent`
nel DB), le passa alla rete neurale addestrata (`app/ml/gap_model.py`) e
produce i **vuoti funzionali** con raccomandazioni d'acquisto consapevole.

Se i pesi della rete non esistono, ricade sulle stesse **regole esperte**
usate per generare il dataset (fallback fail-safe).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml.gap_model import (
    GAP_HUMAN,
    features_from_counts,
    get_gap_classifier,
    rule_based_gaps,
)
from app.models import Item, WearEvent

log = logging.getLogger(__name__)

NEUTRALS = {"nero", "bianco", "grigio", "beige", "marrone"}

# Per ogni vuoto: consiglio d'azione (preferendo il second-hand).
GAP_ADVICE = {
    "manca_capospalla": "Cerca una giacca o un cappotto versatile, meglio se second-hand: è il capo che ti manca per completare più outfit.",
    "manca_scarpe": "Un secondo paio di scarpe amplierebbe molto le combinazioni. Valuta l'usato in buono stato.",
    "manca_formale": "Aggiungi un capo formale (camicia, giacca o vestito) per coprire le occasioni eleganti.",
    "manca_invernale": "Il guardaroba è scoperto sul freddo: un maglione o un cappotto second-hand farebbe la differenza.",
    "troppe_tshirt": "Hai molte t-shirt: prima di comprarne altre, prova a variare con i capi che già possiedi.",
    "poca_varieta_colori": "Pochi colori (o nessun neutro): un capo neutro versatile si abbina con quasi tutto.",
}


@dataclass(frozen=True, slots=True)
class GapItem:
    code: str
    label: str
    advice: str
    probability: float | None


@dataclass(frozen=True, slots=True)
class WardrobeGapAnalysis:
    total_items: int
    counts_by_category: dict[str, int]
    n_colors: int
    has_neutral: bool
    ghost_ratio: float
    balanced: bool
    gaps: list[GapItem]
    source: str  # "neural-net" | "rules"


def _collect_features(db: Session) -> tuple[dict[str, int], int, bool, float]:
    """Aggrega il guardaroba attivo (esclude i capi ritirati)."""
    rows = db.execute(
        select(Item.category, func.count(Item.id))
        .where(Item.retired_at.is_(None))
        .group_by(Item.category)
    ).all()
    counts: dict[str, int] = {}
    for category, n in rows:
        if category:
            counts[category] = int(n)

    # Colori distinti + presenza neutri.
    color_rows = db.execute(
        select(Item.color)
        .where(Item.retired_at.is_(None), Item.color.is_not(None))
        .distinct()
    ).scalars().all()
    colors = {c.lower() for c in color_rows if c}
    n_colors = len(colors)
    has_neutral = bool(colors & NEUTRALS)

    # Ghost ratio: capi attivi senza alcun wear event / totale attivi.
    total_active = db.execute(
        select(func.count(Item.id)).where(Item.retired_at.is_(None))
    ).scalar_one() or 0
    worn_ids = db.execute(
        select(WearEvent.item_id).distinct()
    ).scalars().all()
    worn = set(worn_ids)
    active_ids = db.execute(
        select(Item.id).where(Item.retired_at.is_(None))
    ).scalars().all()
    never_worn = sum(1 for i in active_ids if i not in worn)
    ghost_ratio = (never_worn / total_active) if total_active else 0.0

    return counts, n_colors, has_neutral, ghost_ratio


def analyze_wardrobe(db: Session) -> WardrobeGapAnalysis:
    counts, n_colors, has_neutral, ghost_ratio = _collect_features(db)
    total = sum(counts.values())

    feats = features_from_counts(
        counts, n_colors=n_colors, has_neutral=has_neutral, ghost_ratio=ghost_ratio
    )

    clf = get_gap_classifier()
    if clf is not None:
        try:
            pred = clf.predict(feats)
            gap_codes = pred.gaps
            probs = pred.probabilities
            source = "neural-net"
        except Exception:
            log.warning("Predizione gap fallita, uso le regole", exc_info=True)
            gap_codes = sorted(rule_based_gaps(
                counts, n_colors=n_colors, has_neutral=has_neutral, ghost_ratio=ghost_ratio
            ))
            probs = {}
            source = "rules"
    else:
        gap_codes = sorted(rule_based_gaps(
            counts, n_colors=n_colors, has_neutral=has_neutral, ghost_ratio=ghost_ratio
        ))
        probs = {}
        source = "rules"

    gaps = [
        GapItem(
            code=code,
            label=GAP_HUMAN.get(code, code),
            advice=GAP_ADVICE.get(code, ""),
            probability=round(probs[code], 3) if code in probs else None,
        )
        for code in gap_codes
    ]

    return WardrobeGapAnalysis(
        total_items=total,
        counts_by_category=counts,
        n_colors=n_colors,
        has_neutral=has_neutral,
        ghost_ratio=round(ghost_ratio, 3),
        balanced=len(gaps) == 0,
        gaps=gaps,
        source=source,
    )
