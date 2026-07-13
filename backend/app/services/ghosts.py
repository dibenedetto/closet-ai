"""Regola condivisa per identificare i capi fantasma.

Un capo diventa fantasma solo se non è mai stato indossato *e* il periodo
minimo di possesso è trascorso. Questo modulo centralizza la seconda parte
della regola; i servizi che lo usano verificano anche l'assenza di wear event.
"""

from __future__ import annotations

from datetime import date

from app.models import Item

DEFAULT_GHOST_AFTER_DAYS = 30


def ghost_reference_date(item: Item) -> date | None:
    """Data da cui misurare il possesso: acquisto, poi registrazione nell'app."""
    if item.purchase_date is not None:
        return item.purchase_date
    if item.created_at is not None:
        return item.created_at.date()
    return None


def is_ghost_eligible(
    item: Item,
    *,
    today: date | None = None,
    ghost_after_days: int = DEFAULT_GHOST_AFTER_DAYS,
) -> bool:
    """True se il capo è posseduto da almeno ``ghost_after_days`` giorni.

    Il nome ``eligible`` è intenzionale: per essere davvero fantasma il capo
    deve anche non avere alcun utilizzo registrato.
    """
    reference = ghost_reference_date(item)
    if reference is None:
        return False
    current_day = today or date.today()
    return (current_day - reference).days >= ghost_after_days
