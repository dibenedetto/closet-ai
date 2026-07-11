"""Schemi Pydantic per validazione I/O dell'API."""

from app.schemas.ai import CoachOut, ItemDescriptionOut, TryOnOut, TryOnStatus
from app.schemas.circular import (
    ActionSuggestion,
    ConditionUpdate,
    DiagnoseResponse,
    ImpactStats,
    ItemActionCreate,
    ItemActionRead,
)
from app.schemas.item import ItemRead, ItemUpdate
from app.schemas.outfit import (
    OutfitFeedbackCreate,
    OutfitFeedbackRead,
    OutfitSuggestResponse,
    OutfitSuggestion,
    WeatherSummary,
)
from app.schemas.stats import (
    GapAnalysisOut,
    GapItemOut,
    GhostItem,
    ItemStats,
    TopItem,
    WardrobeStats,
)
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
    "GapAnalysisOut",
    "GapItemOut",
    "GhostItem",
    "ImpactStats",
    "ItemActionCreate",
    "ItemActionRead",
    "ItemDescriptionOut",
    "ItemRead",
    "ItemUpdate",
    "ItemStats",
    "OutfitFeedbackCreate",
    "OutfitFeedbackRead",
    "OutfitSuggestResponse",
    "OutfitSuggestion",
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
