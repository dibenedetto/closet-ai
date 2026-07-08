"""Schemi Pydantic per il modulo circolare (Fase 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# "nuovo" fuso in "buono" (ADR-009): su foto reali erano indistinguibili.
Condition = Literal["buono", "usurato", "danneggiato"]
ActionType = Literal["riparazione", "swap", "vendita", "donazione", "riciclo"]


class ConditionUpdate(BaseModel):
    condition: Condition


class ActionSuggestion(BaseModel):
    action_type: ActionType
    co2_saved_kg: float
    rationale: str
    priority: int


class DiagnoseResponse(BaseModel):
    item_id: int
    condition: Condition
    wear_count: int
    days_owned: int | None
    rationale: str
    # Backend usato: "clip-mlp" | "heuristic".
    source: str = "heuristic"
    confidence: float | None = None
    suggestions: list[ActionSuggestion]


class ItemActionCreate(BaseModel):
    action_type: ActionType
    notes: str | None = Field(default=None, max_length=2000)
    # Se `None`, il backend calcola la stima CO₂ dal `category`.
    co2_saved_kg: float | None = Field(default=None, ge=0)


class ItemActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    action_type: ActionType
    notes: str | None
    co2_saved_kg: float
    created_at: datetime


class ImpactStats(BaseModel):
    total_actions: int
    total_co2_saved_kg: float
    actions_by_type: dict[str, int]
    co2_by_type: dict[str, float]
    retired_items_count: int
    repaired_items_count: int
