"""Coach AI per la sostenibilità del guardaroba.

Combina `WardrobeStats` + `ImpactStats` + lista capi fantasma e genera un
messaggio personalizzato che aiuta l'utente a:
- celebrare i progressi (CO₂ evitata, capi salvati);
- evidenziare i capi fantasma da indossare di più;
- proporre il prossimo step (riparare? scambiare? ridurre acquisti?).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.services import llm
from app.services.stats import (
    DEFAULT_GHOST_AFTER_DAYS,
    compute_impact_stats,
    compute_wardrobe_stats,
    list_ghost_items,
)

log = logging.getLogger(__name__)

_SYSTEM = (
    "Sei un coach AI per la moda sostenibile. Parli italiano, sei diretto, "
    "concreto e mai moralista. I tuoi messaggi sono di 4-6 frasi al massimo. "
    "Combini i numeri dell'utente con un suggerimento di azione specifica "
    "(es. 'prima di comprare un'altra t-shirt, prova a indossare X')."
)


@dataclass(frozen=True, slots=True)
class CoachMessage:
    text: str
    facts: dict[str, Any]
    model: str | None
    cached: bool


def _build_facts(db: Session, ghost_after_days: int) -> dict[str, Any]:
    wardrobe = compute_wardrobe_stats(db, ghost_after_days=ghost_after_days, top_n=3)
    impact = compute_impact_stats(db)
    ghosts = list_ghost_items(db, ghost_after_days=ghost_after_days)
    return {
        "wardrobe": wardrobe,
        "impact": impact,
        "ghosts_top3": [
            {"name": g["name"], "category": g["category"], "days_owned": g["days_owned"]}
            for g in ghosts[:3]
        ],
    }


def generate_coach_message(
    db: Session, *, ghost_after_days: int = DEFAULT_GHOST_AFTER_DAYS
) -> CoachMessage | None:
    """Genera un consiglio del coach via LLM. `None` se LLM non disponibile."""
    facts = _build_facts(db, ghost_after_days)
    if facts["wardrobe"]["total_items"] == 0:
        return CoachMessage(
            text=(
                "Il tuo guardaroba è ancora vuoto. Aggiungi qualche capo per "
                "iniziare a tracciare i tuoi utilizzi e ottenere consigli "
                "personalizzati. Ti basta una foto."
            ),
            facts=facts,
            model=None,
            cached=False,
        )

    import json

    user = (
        "Ecco lo stato del guardaroba dell'utente:\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
        + "\n\nScrivi un messaggio coach in italiano, 4-6 frasi, che:\n"
        "1. cita una metrica concreta (CO₂ evitata o capi salvati o utilizzi);\n"
        "2. menziona uno specifico capo fantasma (se presente) e suggerisce di indossarlo;\n"
        "3. propone un'azione realistica per il prossimo step.\n"
        "Niente liste puntate, solo prosa. Massimo 600 caratteri."
    )

    result = llm.generate(user, system=_SYSTEM, db=db, max_tokens=400)
    if result is None:
        return None

    return CoachMessage(
        text=result.text,
        facts=facts,
        model=result.model,
        cached=result.cached,
    )
