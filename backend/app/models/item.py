"""Modello ORM per un capo del guardaroba.

NB: niente `from __future__ import annotations` qui — SQLAlchemy 2.0 fa
introspection runtime delle annotazioni `Mapped[...]` e su Python 3.14 le
stringhe deferred di `__future__.annotations` non risolvono correttamente.
"""

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Descrizione narrativa generata dall'LLM (vedi `services/descriptions.py`).
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Condizione del capo: 'buono', 'usurato', 'danneggiato'.
    condition: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    # Quando un capo viene "ritirato" (donato/venduto/riciclato) cessa di
    # essere disponibile per outfit e wear log. La riparazione NON lo ritira.
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Forward ref "WearEvent": SQLAlchemy lo risolve via registry interno; non
    # serve importare il modello concreto qui (evita il circular import).
    wear_events: Mapped[list["WearEvent"]] = relationship(  # noqa: F821
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WearEvent.worn_on.desc()",
    )
    actions: Mapped[list["ItemAction"]] = relationship(  # noqa: F821
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ItemAction.created_at.desc()",
    )
