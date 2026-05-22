"""Schemi Pydantic per wear events.

NB: il campo è `worn_on`, non `date`, per evitare di schermare il tipo
`datetime.date` nelle annotazioni (Python 3.14 + Pydantic).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WearEventCreate(BaseModel):
    """Payload per registrare un utilizzo. `worn_on` default = oggi."""

    worn_on: date | None = None
    occasion: str | None = Field(default=None, max_length=64)


class WearEventBatchItem(BaseModel):
    item_id: int = Field(..., ge=1)
    worn_on: date | None = None
    occasion: str | None = Field(default=None, max_length=64)


class WearEventBatchCreate(BaseModel):
    events: list[WearEventBatchItem] = Field(..., min_length=1, max_length=200)


class WearEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    worn_on: date
    occasion: str | None
    created_at: datetime
