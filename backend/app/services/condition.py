"""Diagnosi della condizione del capo, con backend selezionabile.

Due strategie, in ordine di capacità decrescente:

1. **MLP su Fashion-CLIP** (Approccio A, ADR-009): una testa addestrata da
   noi predice lo stato dalla foto. Gira su CPU.

2. **Euristica** (fallback sempre disponibile): basata su numero di utilizzi
   ed età del capo.

La selezione è guidata da ``CLOSETAI_CONDITION_BACKEND``:

- ``auto`` (default) → prova MLP, poi euristica (primo disponibile).
- ``clip-mlp`` / ``heuristic`` → forza un backend specifico (con fallback
  all'euristica se quello richiesto non è utilizzabile).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import CONDITION_BACKEND, ITEMS_DIR
from app.models import Item, WearEvent

log = logging.getLogger(__name__)

# "nuovo" è stato fuso in "buono" (vedi ADR-009): su foto reali il confine
# fra i due era artificiale e indistinguibile.
CONDITIONS = ("buono", "usurato", "danneggiato")

# Sorgenti possibili, esposte nel campo `source` del risultato.
SOURCE_MLP = "clip-mlp"
SOURCE_HEURISTIC = "heuristic"


@dataclass(frozen=True, slots=True)
class DiagnosisResult:
    condition: str
    wear_count: int
    days_owned: int | None
    rationale: str
    source: str = SOURCE_HEURISTIC
    confidence: float | None = None


# ---------------------------------------------------------------------------
# Euristica
# ---------------------------------------------------------------------------


def _age_in_days(item: Item, today: date) -> int | None:
    ref: date | None = item.purchase_date
    if ref is None and item.created_at:
        ref = item.created_at.date()
    if ref is None:
        return None
    return (today - ref).days


def _classify(wear_count: int, days_owned: int | None) -> tuple[str, str]:
    age = days_owned if days_owned is not None else 0
    if wear_count == 0 and age < 60:
        # classe "nuovo" fusa in "buono" (ADR-009)
        return "buono", f"mai indossato, posseduto da {age} giorni"
    if wear_count > 80 or age > 1825:
        return "danneggiato", f"{wear_count} utilizzi su {age} giorni: usura significativa"
    if wear_count > 30 or age > 730:
        return "usurato", f"{wear_count} utilizzi su {age} giorni: segni d'uso attesi"
    return "buono", f"{wear_count} utilizzi su {age} giorni: in buone condizioni"


def _wear_count(db: Session, item: Item) -> int:
    return db.execute(
        select(func.count(WearEvent.id)).where(WearEvent.item_id == item.id)
    ).scalar_one() or 0


def _heuristic_result(item: Item, wear_count: int, days_owned: int | None) -> DiagnosisResult:
    condition, rationale = _classify(wear_count, days_owned)
    return DiagnosisResult(
        condition=condition,
        wear_count=wear_count,
        days_owned=days_owned,
        rationale=rationale,
        source=SOURCE_HEURISTIC,
    )


# ---------------------------------------------------------------------------
# Backend visivi
# ---------------------------------------------------------------------------


def _readable_image(item: Item) -> Path | None:
    if not item.image_path:
        return None
    p = ITEMS_DIR / item.image_path
    return p if p.is_file() else None


def _try_mlp(item: Item, wear_count: int, days_owned: int | None) -> DiagnosisResult | None:
    image_path = _readable_image(item)
    if image_path is None:
        return None
    try:
        from app.ml.condition_model import get_condition_classifier

        clf = get_condition_classifier()
        if clf is None:
            return None
        pred = clf.predict_from_image(image_path)
    except Exception:
        log.warning("Diagnosi MLP fallita per item=%s", item.id, exc_info=True)
        return None

    return DiagnosisResult(
        condition=pred.condition,
        wear_count=wear_count,
        days_owned=days_owned,
        rationale=f"diagnosi dalla foto (CLIP+MLP) — confidenza {pred.confidence:.0%}",
        source=SOURCE_MLP,
        confidence=pred.confidence,
    )


# ---------------------------------------------------------------------------
# Orchestrazione
# ---------------------------------------------------------------------------

# Ordine di tentativi per la modalità "auto".
_AUTO_CHAIN = (_try_mlp,)


def diagnose(db: Session, item: Item, *, today: date | None = None) -> DiagnosisResult:
    """Diagnosi dello stato secondo la strategia ``CLOSETAI_CONDITION_BACKEND``."""
    today = today or date.today()
    wear_count = _wear_count(db, item)
    days_owned = _age_in_days(item, today)

    backend = CONDITION_BACKEND.lower().strip()

    if backend == SOURCE_HEURISTIC:
        return _heuristic_result(item, wear_count, days_owned)

    if backend == SOURCE_MLP:
        result = _try_mlp(item, wear_count, days_owned)
        return result or _heuristic_result(item, wear_count, days_owned)

    # "auto" (default) o valore non riconosciuto → cascata.
    for attempt in _AUTO_CHAIN:
        result = attempt(item, wear_count, days_owned)
        if result is not None:
            return result
    return _heuristic_result(item, wear_count, days_owned)


def now_utc() -> datetime:
    """Esposta per i router che vogliono settare `retired_at`."""
    return datetime.now(timezone.utc)
