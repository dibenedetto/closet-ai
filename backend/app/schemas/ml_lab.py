"""Schemi Pydantic per la pagina tecnica ML Lab (training / test / eval)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Stato di un modello addestrato da noi."""

    key: str                      # "condition-mlp" | "gap-mlp"
    name: str
    nature: str                   # "own" — per il codice colore in UI
    task: str                     # descrizione breve del compito
    available: bool               # pesi/adapter presenti su disco
    architecture: str | None = None
    metrics: dict | None = None   # metriche salvate nel checkpoint al training
    labels: list[str] | None = None


class DatasetInfo(BaseModel):
    key: str                      # "garment_condition" | "wardrobe"
    name: str
    available: bool
    n_samples: int | None = None
    detail: str | None = None


class MlLabStatus(BaseModel):
    models: list[ModelInfo]
    datasets: list[DatasetInfo]


class ConditionPredictOut(BaseModel):
    condition: str
    confidence: float
    probabilities: dict[str, float]


class GapPredictIn(BaseModel):
    """Conteggi per categoria + contesto colore/uso, per il simulatore what-if."""

    counts: dict[str, int] = Field(default_factory=dict)
    n_colors: int = Field(3, ge=0, le=20)
    has_neutral: bool = True
    ghost_ratio: float = Field(0.2, ge=0.0, le=1.0)


class GapPredictOut(BaseModel):
    gaps: list[str]                    # codici label attive
    labels: dict[str, str]             # code -> etichetta leggibile
    probabilities: dict[str, float]    # vuote se fallback a regole
    balanced: bool
    source: str                        # "neural-net" | "rules"
