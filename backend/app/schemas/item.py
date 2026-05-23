"""Schemi Pydantic per Item.

`ItemRead` è la rappresentazione esposta dall'API. I dati di creazione arrivano
da `multipart/form-data` (form + file) e sono gestiti direttamente nel router
con i tipi nativi FastAPI (`Form`, `UploadFile`), quindi non serve un
`ItemCreate` Pydantic per quel percorso.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None
    color: str | None
    image_path: str | None
    price: float | None
    purchase_date: date | None
    classification_confidence: float | None
    description: str | None
    condition: str | None
    retired_at: datetime | None
    created_at: datetime
