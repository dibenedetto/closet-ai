"""Schemi Pydantic per validazione I/O dell'API."""

from app.schemas.ai import CoachOut, ItemDescriptionOut, TryOnOut, TryOnStatus
from app.schemas.circular import (
    ActionSuggestion,
    ConditionUpdate,
    DiagnoseResponse,
    ImpactStats,
    ItemActionCreate,
    ItemActionRead,
    RepairTutorialOut,
    SupportedDefects,
)
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
    "ActionSuggestion",
    "CoachOut",
    "ConditionUpdate",
    "DiagnoseResponse",
    "GhostItem",
    "ImpactStats",
    "ItemActionCreate",
    "ItemActionRead",
    "ItemDescriptionOut",
    "ItemRead",
    "ItemStats",
    "OutfitFeedbackCreate",
    "OutfitFeedbackRead",
    "OutfitSuggestResponse",
    "OutfitSuggestion",
    "RepairTutorialOut",
    "SupportedDefects",
    "TopItem",
    "TryOnOut",
    "TryOnStatus",
    "WardrobeStats",
    "WeatherSummary",
    "WearEventBatchCreate",
    "WearEventBatchItem",
    "WearEventCreate",
    "WearEventRead",
]
