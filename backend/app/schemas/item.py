"""Schemi Pydantic per Item.

`ItemRead` è la rappresentazione esposta dall'API. I dati di creazione arrivano
da `multipart/form-data` (form + file) e sono gestiti direttamente nel router
con i tipi nativi FastAPI (`Form`, `UploadFile`), quindi non serve un
`ItemCreate` Pydantic per quel percorso.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemUpdate(BaseModel):
    """Campi modificabili di un capo.

    Tutti i campi sono opzionali per supportare PATCH; ``model_fields_set``
    permette al router di distinguere un campo omesso da un valore ``null``
    esplicito, usato per cancellare i metadati nullable.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=32)
    price: float | None = Field(default=None, ge=0)
    purchase_date: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("Il nome non può essere nullo o vuoto.")
        return value.strip()


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
