"""Genera la descrizione narrativa di un capo via LLM.

La descrizione è breve (1-2 frasi), in italiano, e riassume gli attributi
essenziali del capo per aiutare l'utente a riconoscerlo a colpo d'occhio
nella lista. Viene salvata su `Item.description`.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Item
from app.services import llm

log = logging.getLogger(__name__)

_SYSTEM = (
    "Sei un assistente che descrive capi di abbigliamento per un'app di "
    "guardaroba. Le tue descrizioni sono brevi (1-2 frasi, massimo 220 "
    "caratteri), in italiano, neutre e fattuali. Niente claim di brand. "
    "Concentrati su silhouette, occasione d'uso e abbinamenti tipici."
)


def generate_item_description(item: Item, db: Session) -> str | None:
    """Ritorna una descrizione testuale per il capo, oppure `None` se l'LLM
    non è raggiungibile."""
    attributes = []
    if item.category:
        attributes.append(f"categoria: {item.category}")
    if item.color:
        attributes.append(f"colore: {item.color}")
    if item.price is not None:
        attributes.append(f"prezzo d'acquisto: € {item.price:.2f}")
    if item.condition:
        attributes.append(f"condizione: {item.condition}")

    user = (
        f"Genera una descrizione di **{item.name}**.\n"
        + ("Attributi: " + "; ".join(attributes) if attributes else "Nessun attributo noto.")
        + "\n\nRispondi *solo* con il testo della descrizione, senza prefissi né virgolette."
    )

    result = llm.generate(user, system=_SYSTEM, db=db, max_tokens=160)
    if result is None:
        return None
    text = result.text.strip().strip('"').strip("«»").strip()
    if len(text) > 1024:
        text = text[:1020] + "…"
    return text or None
