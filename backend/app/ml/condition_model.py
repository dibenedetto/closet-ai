"""Rete neurale addestrata da noi per la diagnosi dello stato del capo.

Architettura (Approccio A): **testa MLP su embedding Fashion-CLIP**.

    foto ──▶ Fashion-CLIP (frozen) ──▶ embedding 512d ──▶ MLP ──▶ stato (4 classi)
            [pre-addestrato]                              [addestrato da noi]

La parte "addestrata da noi" è il piccolo MLP a valle: leggero (~170k
parametri), gira su CPU in millisecondi. Fashion-CLIP funge da estrattore
di feature congelato.

I pesi sono salvati in ``ml/weights/condition_head.pt`` dallo script
``backend/scripts/train_condition_model.py``. Se i pesi non esistono,
`get_condition_classifier()` ritorna ``None`` e il backend ricade
sull'euristica (vedi `services/condition.py`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import PROJECT_ROOT

log = logging.getLogger(__name__)

# Etichette in ordine di indice (devono combaciare con il training).
CONDITION_LABELS: tuple[str, ...] = ("nuovo", "buono", "usurato", "danneggiato")

WEIGHTS_PATH = Path(
    __import__("os").environ.get(
        "CLOSETAI_CONDITION_WEIGHTS",
        str(PROJECT_ROOT / "ml" / "weights" / "condition_head.pt"),
    )
)

EMBED_DIM = 512
HIDDEN_DIMS = (256, 128)
DROPOUT = 0.3


def build_mlp(in_dim: int = EMBED_DIM, hidden=HIDDEN_DIMS,
              n_classes: int = len(CONDITION_LABELS), dropout: float = DROPOUT):
    """Costruisce il MLP. Import di torch differito (pesante)."""
    import torch.nn as nn

    layers: list = []
    prev = in_dim
    for h in hidden:
        layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
        prev = h
    layers.append(nn.Linear(prev, n_classes))
    return nn.Sequential(*layers)


@dataclass(frozen=True, slots=True)
class ConditionPrediction:
    condition: str
    confidence: float
    probabilities: dict[str, float]


class ConditionVisionClassifier:
    """Carica il MLP addestrato e predice lo stato da una foto."""

    def __init__(self, weights_path: Path = WEIGHTS_PATH) -> None:
        self.weights_path = weights_path
        self._model = None
        self._labels: tuple[str, ...] = CONDITION_LABELS

    def is_available(self) -> bool:
        return self.weights_path.is_file()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch

        ckpt = torch.load(self.weights_path, map_location="cpu", weights_only=False)
        self._labels = tuple(ckpt.get("labels", CONDITION_LABELS))
        model = build_mlp(
            in_dim=ckpt.get("in_dim", EMBED_DIM),
            hidden=tuple(ckpt.get("hidden", HIDDEN_DIMS)),
            n_classes=len(self._labels),
            dropout=ckpt.get("dropout", DROPOUT),
        )
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        self._model = model
        log.info("Modello condizione caricato da %s (val_acc=%.3f)",
                 self.weights_path, ckpt.get("val_accuracy", float("nan")))

    def predict_from_embedding(self, embedding: list[float]) -> ConditionPrediction:
        import torch

        self._ensure_loaded()
        assert self._model is not None
        with torch.no_grad():
            x = torch.tensor(embedding, dtype=torch.float32).unsqueeze(0)
            logits = self._model(x)
            probs = logits.softmax(dim=-1)[0]
            top = int(probs.argmax().item())
        return ConditionPrediction(
            condition=self._labels[top],
            confidence=float(probs[top].item()),
            probabilities={lab: float(probs[i].item()) for i, lab in enumerate(self._labels)},
        )

    def predict_from_image(self, image_path: str | Path) -> ConditionPrediction:
        """Pipeline completa: foto → embedding Fashion-CLIP → MLP → stato."""
        from app.ml.classifier import FashionClipClassifier, get_classifier

        clf = get_classifier()
        if isinstance(clf, FashionClipClassifier):
            embedding = clf.embed_image(image_path)
        else:
            # Il classifier attivo è il Mock (no embedding): carichiamo
            # Fashion-CLIP direttamente come feature extractor.
            embedding = FashionClipClassifier().embed_image(image_path)
        return self.predict_from_embedding(embedding)


@lru_cache(maxsize=1)
def get_condition_classifier() -> ConditionVisionClassifier | None:
    """Singleton. Ritorna ``None`` se i pesi non sono stati addestrati."""
    clf = ConditionVisionClassifier()
    if not clf.is_available():
        log.info("Pesi modello condizione assenti (%s): uso euristica.", clf.weights_path)
        return None
    return clf


def reset_condition_classifier_cache() -> None:
    get_condition_classifier.cache_clear()
