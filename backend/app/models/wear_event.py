"""Modello ORM per un evento di utilizzo (wear) di un capo.

NB: niente `from __future__ import annotations` qui — vedi nota in `item.py`.
"""

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WearEvent(Base):
    __tablename__ = "wear_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # `worn_on`, non `date`: evita lo shadow del tipo `datetime.date` nelle
    # annotazioni di altri moduli (es. schemi Pydantic).
    worn_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    occasion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    item: Mapped["Item"] = relationship(back_populates="wear_events")  # noqa: F821
