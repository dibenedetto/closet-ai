"""Modello ORM per un'azione circolare registrata su un capo.

NB: niente `from __future__ import annotations` (vedi nota in `item.py`).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Tipi di azione consentiti. Validati lato schema, non con Enum SQL.
ACTION_TYPES = ("riparazione", "swap", "vendita", "donazione", "riciclo")


class ItemAction(Base):
    __tablename__ = "item_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    co2_saved_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    item: Mapped["Item"] = relationship(back_populates="actions")  # noqa: F821
