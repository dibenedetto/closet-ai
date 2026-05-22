"""Modello per i feedback degli utenti sulle proposte di outfit.

NB: niente `from __future__ import annotations` (vedi nota in `item.py`).

`item_ids` viene salvato come JSON (lista di interi serializzata). Per
l'MVP è sufficiente: non servono query "quali outfit contengono X". Se
diventerà necessario, si introdurrà una tabella di join `outfit_items`.
"""

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OutfitFeedback(Base):
    __tablename__ = "outfit_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # JSON array, es. "[1,2,3]". Non FK perché un capo eliminato non invalida
    # la storia dei feedback ricevuti.
    item_ids_json: Mapped[str] = mapped_column(String(1024), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 like / -1 dislike
    occasion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    @property
    def item_ids(self) -> list[int]:
        try:
            return list(json.loads(self.item_ids_json))
        except Exception:
            return []
