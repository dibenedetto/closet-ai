"""Diagnosi della condizione del capo.

Per la Fase 5 MVP usiamo un'**euristica deterministica** basata su:
- numero di utilizzi registrati (`wear_count`)
- età del capo (giorni da `purchase_date` o, in fallback, `created_at`)

Una versione più sofisticata (Fase 6+) può sostituire `diagnose()` con un
classifier visivo zero-shot su Fashion-CLIP, mantenendo l'interfaccia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Item, WearEvent

CONDITIONS = ("nuovo", "buono", "usurato", "danneggiato")


@dataclass(frozen=True, slots=True)
class DiagnosisResult:
    condition: str
    wear_count: int
    days_owned: int | None
    rationale: str


def _age_in_days(item: Item, today: date) -> int | None:
    ref: date | None = item.purchase_date
    if ref is None and item.created_at:
        ref = item.created_at.date()
    if ref is None:
        return None
    return (today - ref).days


def _classify(wear_count: int, days_owned: int | None) -> tuple[str, str]:
    """Regole soglia. Tunabili da `docs/architecture.md` (ADR futuro)."""
    age = days_owned if days_owned is not None else 0

    # Mai indossato + recente → "nuovo"
    if wear_count == 0 and age < 60:
        return "nuovo", f"mai indossato, posseduto da {age} giorni"

    # Molto vecchio + molto usato → "danneggiato"
    if wear_count > 80 or age > 1825:
        return "danneggiato", f"{wear_count} utilizzi su {age} giorni: usura significativa"

    # Usato spesso o capo maturo → "usurato"
    if wear_count > 30 or age > 730:
        return "usurato", f"{wear_count} utilizzi su {age} giorni: segni d'uso attesi"

    # Caso intermedio
    return "buono", f"{wear_count} utilizzi su {age} giorni: in buone condizioni"


def diagnose(db: Session, item: Item, *, today: date | None = None) -> DiagnosisResult:
    """Restituisce la diagnosi euristica per il capo indicato."""
    today = today or date.today()
    wear_count: int = db.execute(
        select(func.count(WearEvent.id)).where(WearEvent.item_id == item.id)
    ).scalar_one() or 0
    days_owned = _age_in_days(item, today)
    condition, rationale = _classify(wear_count, days_owned)
    return DiagnosisResult(
        condition=condition,
        wear_count=wear_count,
        days_owned=days_owned,
        rationale=rationale,
    )


def now_utc() -> datetime:
    """Esposta per i router che vogliono settare `retired_at`."""
    return datetime.now(timezone.utc)
