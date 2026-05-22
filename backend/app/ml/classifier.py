"""Classificatore capi: interfaccia comune + due implementazioni.

- `MockClassifier`: categoria casuale + colore dominante migliorato. Sempre
  disponibile, default nei test, fallback se il modello reale non si carica.
- `FashionClipClassifier`: Fashion-CLIP (HuggingFace `patrickjohncyh/fashion-clip`).
  Zero-shot su `CATEGORIES`, produce embedding 512d e una confidenza softmax.

La selezione è guidata dall'env var `CLOSETAI_CLASSIFIER` (default `fashion-clip`).
Vedi `docs/architecture.md` (ADR-003) per la motivazione.
"""

from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.ml.color import dominant_color_name

log = logging.getLogger(__name__)

CATEGORIES: tuple[str, ...] = (
    "t-shirt",
    "camicia",
    "felpa",
    "maglione",
    "giacca",
    "cappotto",
    "jeans",
    "pantaloni",
    "shorts",
    "gonna",
    "vestito",
    "scarpe",
    "cappello",
    "sciarpa",
)

# Prompt EN per Fashion-CLIP — il modello è addestrato su captions inglesi,
# usare prompt italiani degrada la classificazione. La label restituita è
# comunque quella italiana di `CATEGORIES`, allineata posizionalmente.
CATEGORY_PROMPTS_EN: tuple[str, ...] = (
    "a t-shirt",
    "a button-up shirt",
    "a sweatshirt or hoodie",
    "a knitted sweater",
    "a jacket",
    "a long coat",
    "a pair of jeans",
    "a pair of trousers",
    "a pair of shorts",
    "a skirt",
    "a dress",
    "a pair of shoes",
    "a hat",
    "a scarf",
)

assert len(CATEGORIES) == len(CATEGORY_PROMPTS_EN), (
    "CATEGORIES e CATEGORY_PROMPTS_EN devono essere allineati posizionalmente"
)


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Output di un classificatore. Tutti i campi opzionali per uniformità."""

    category: str | None
    color: str | None
    embedding: list[float] | None
    confidence: float | None


class Classifier(Protocol):
    def classify(self, image_path: str | Path) -> ClassificationResult: ...


# ============================================================================
# Mock
# ============================================================================


class MockClassifier:
    """Classificatore di fallback / test: categoria casuale + colore reale."""

    def __init__(self, *, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def classify(self, image_path: str | Path) -> ClassificationResult:
        return ClassificationResult(
            category=self._rng.choice(CATEGORIES),
            color=dominant_color_name(image_path),
            embedding=None,
            confidence=None,
        )


# ============================================================================
# Fashion-CLIP
# ============================================================================


class FashionClipClassifier:
    """Wrapper attorno a `patrickjohncyh/fashion-clip` (CLIP fine-tunato).

    Strategia zero-shot: precomputiamo gli embedding testuali dei prompt EN al
    primo uso, poi per ogni immagine calcoliamo il suo embedding e prendiamo
    la categoria con similarità più alta (softmax → confidenza).
    """

    MODEL_NAME = "patrickjohncyh/fashion-clip"

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._text_features = None  # tensor [num_classes, dim]

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import CLIPModel, CLIPProcessor

        log.info("Carico Fashion-CLIP (%s) — primo run ~600MB", self.MODEL_NAME)
        self._processor = CLIPProcessor.from_pretrained(self.MODEL_NAME)
        model = CLIPModel.from_pretrained(self.MODEL_NAME)
        model.eval()
        self._model = model

        # Precomputo i text embedding (proiettati e normalizzati) per le
        # CATEGORY_PROMPTS_EN. In transformers 5 i wrapper `get_text_features` /
        # `get_image_features` di alcuni checkpoint ritornano un ModelOutput
        # non-tensor: usiamo quindi `text_model + text_projection` direttamente,
        # equivalente alla pipeline CLIP standard.
        with torch.no_grad():
            text_inputs = self._processor(
                text=list(CATEGORY_PROMPTS_EN),
                return_tensors="pt",
                padding=True,
            )
            text_outputs = model.text_model(**text_inputs)
            pooled = text_outputs.pooler_output
            text_features = model.text_projection(pooled)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            self._text_features = text_features

    def classify(self, image_path: str | Path) -> ClassificationResult:
        from PIL import Image
        import torch

        self._ensure_loaded()
        assert self._model is not None
        assert self._processor is not None
        assert self._text_features is not None

        with Image.open(image_path) as im:
            rgb_image = im.convert("RGB")
            image_inputs = self._processor(images=rgb_image, return_tensors="pt")

        with torch.no_grad():
            vision_outputs = self._model.vision_model(**image_inputs)
            image_features = self._model.visual_projection(vision_outputs.pooler_output)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            # Logits scalati come in CLIP paper (temperatura 100)
            logits = 100.0 * image_features @ self._text_features.T
            probs = logits.softmax(dim=-1)[0]
            top = int(probs.argmax().item())
            confidence = float(probs[top].item())
            embedding = image_features[0].tolist()

        return ClassificationResult(
            category=CATEGORIES[top],
            color=dominant_color_name(image_path),
            embedding=embedding,
            confidence=confidence,
        )


# ============================================================================
# Factory
# ============================================================================


@lru_cache(maxsize=1)
def get_classifier() -> Classifier:
    """Restituisce il classifier singleton selezionato via env."""
    kind = os.environ.get("CLOSETAI_CLASSIFIER", "fashion-clip").lower().strip()
    if kind == "mock":
        return MockClassifier()
    if kind in {"fashion-clip", "fashionclip"}:
        try:
            return FashionClipClassifier()
        except ImportError:
            log.warning(
                "torch/transformers non disponibili, fallback su MockClassifier"
            )
            return MockClassifier()
    raise ValueError(
        f"CLOSETAI_CLASSIFIER non valido: {kind!r} "
        "(valori ammessi: 'mock', 'fashion-clip')"
    )


def reset_classifier_cache() -> None:
    """Pulisce il singleton — utile per i test."""
    get_classifier.cache_clear()


def classify(
    image_path: str | Path, *, rng: random.Random | None = None
) -> ClassificationResult:
    """Shortcut funzionale. Se `rng` è passato si usa un Mock dedicato,
    utile per i test deterministici sul fallback."""
    if rng is not None:
        return MockClassifier(rng=rng).classify(image_path)
    return get_classifier().classify(image_path)
