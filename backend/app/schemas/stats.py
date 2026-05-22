"""Schemi Pydantic per le statistiche di wear log."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ItemStats(BaseModel):
    item_id: int
    wear_count: int
    last_worn: date | None
    days_since_last_worn: int | None
    cost_per_wear: float | None
    is_ghost: bool
    ghost_after_days: int


class TopItem(BaseModel):
    item_id: int
    name: str
    wear_count: int


class WardrobeStats(BaseModel):
    total_items: int
    total_wears: int
    avg_wears_per_item: float
    ghost_count: int
    ghost_after_days: int
    total_investment: float | None
    avg_cost_per_wear: float | None
    top_worn: list[TopItem]


class GhostItem(BaseModel):
    item_id: int
    name: str
    category: str | None
    purchase_date: date | None
    days_owned: int | None
    price: float | None
