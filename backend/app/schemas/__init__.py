"""Schemi Pydantic per validazione I/O dell'API."""

from app.schemas.item import ItemRead
from app.schemas.outfit import (
    OutfitFeedbackCreate,
    OutfitFeedbackRead,
    OutfitSuggestResponse,
    OutfitSuggestion,
    WeatherSummary,
)
from app.schemas.stats import GhostItem, ItemStats, TopItem, WardrobeStats
from app.schemas.wear import (
    WearEventBatchCreate,
    WearEventBatchItem,
    WearEventCreate,
    WearEventRead,
)

__all__ = [
    "GhostItem",
    "ItemRead",
    "ItemStats",
    "OutfitFeedbackCreate",
    "OutfitFeedbackRead",
    "OutfitSuggestResponse",
    "OutfitSuggestion",
    "TopItem",
    "WardrobeStats",
    "WeatherSummary",
    "WearEventBatchCreate",
    "WearEventBatchItem",
    "WearEventCreate",
    "WearEventRead",
]
