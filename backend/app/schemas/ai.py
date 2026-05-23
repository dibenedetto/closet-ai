"""Schemi Pydantic per gli endpoint di AI generativa (Fase 6+)."""

from __future__ import annotations

from pydantic import BaseModel


class ItemDescriptionOut(BaseModel):
    item_id: int
    description: str | None
    generated: bool  # True se appena generata; False se solo letta dal DB
    model: str | None  # nome del modello usato (es. "claude-haiku-4-5")


class CoachOut(BaseModel):
    text: str
    facts: dict
    model: str | None
    cached: bool


class TryOnOut(BaseModel):
    item_id: int
    filename: str
    url: str
    backend: str
    prompt: str
    elapsed_ms: int


class TryOnStatus(BaseModel):
    """Esposto da `GET /tryon/status` per il frontend.

    Permette al frontend di decidere se mostrare il pulsante "Try-on virtuale"
    senza dover prima fare upload."""

    backend: str
    available: bool
    model: str | None
