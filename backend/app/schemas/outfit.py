"""Schemi Pydantic per outfit recommender."""

from __future__ import annotations

from datetime import date as date_type, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.item import ItemRead


class WeatherSummary(BaseModel):
    target_date: date_type
    temperature_c: float
    precipitation_mm: float
    wind_kmh: float
    weather_code: int
    source: str  # "open-meteo" o "fallback"


class OutfitSuggestion(BaseModel):
    items: list[ItemRead]
    score: float
    color_score: float
    weather_score: float
    ghost_bonus: float
    rationale: str


class OutfitSuggestResponse(BaseModel):
    target_date: date_type
    weather: WeatherSummary
    outfits: list[OutfitSuggestion]


class OutfitFeedbackCreate(BaseModel):
    item_ids: list[int] = Field(..., min_length=1, max_length=10)
    rating: int = Field(..., ge=-1, le=1)
    occasion: str | None = Field(default=None, max_length=64)


class OutfitFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_ids: list[int]
    rating: int
    occasion: str | None
    created_at: datetime
