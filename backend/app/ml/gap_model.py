"""Gap analysis del guardaroba — rete neurale addestrata da noi.

Mentre Fashion-CLIP *riconosce* i capi dalle foto, questo modello lavora a
un livello superiore: dai **dati aggregati** del guardaroba (quanti capi
per categoria, copertura colori, stagionalità, frequenza d'uso) predice i
**vuoti funzionali** — es. "manca un capospalla", "troppe t-shirt", "poche
alternative invernali".

Architettura: MLP **multi-label** (un guardaroba può avere più vuoti
contemporaneamente) addestrato su un dataset tabellare sintetico ispirato
alle categorie di DeepFashion (vedi `scripts/build_wardrobe_dataset.py` e
`docs/dataset-datasheet.md`).

Questo modulo è la **fonte di verità condivisa** per:
- l'ordine delle feature (`FEATURE_NAMES`) e delle label (`GAP_LABELS`),
- il calcolo delle feature da conteggi (`features_from_counts`),
- le regole esperte di ground-truth / fallback (`rule_based_gaps`),
- la rete e l'inferenza (`GapClassifier`).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import PROJECT_ROOT

log = logging.getLogger(__name__)

# 14 categorie del progetto (coerenti con app/ml/classifier.py).
CATEGORIES = (
    "t-shirt", "camicia", "felpa", "maglione", "giacca", "cappotto",
    "jeans", "pantaloni", "shorts", "gonna", "vestito", "scarpe",
    "cappello", "sciarpa",
)

# Macro-ruolo per categoria (coerente con services/recommender.py).
ROLE_OF = {
    "t-shirt": "top", "camicia": "top", "felpa": "top", "maglione": "top",
    "jeans": "bottom", "pantaloni": "bottom", "shorts": "bottom", "gonna": "bottom",
    "giacca": "outerwear", "cappotto": "outerwear",
    "scarpe": "shoes",
    "vestito": "dress",
    "cappello": "accessory", "sciarpa": "accessory",
}

WINTER = {"maglione", "cappotto", "giacca", "sciarpa"}
FORMAL = {"camicia", "giacca", "vestito"}

# Ordine FISSO delle feature di input alla rete.
FEATURE_NAMES = (
    "n_top", "n_bottom", "n_outerwear", "n_shoes", "n_dress", "n_accessory",
    "n_total",
    "frac_tshirt", "frac_outerwear", "frac_winter", "frac_formal",
    "n_colors", "has_neutral", "ghost_ratio",
)

# Ordine FISSO delle label di output (vuoti funzionali).
GAP_LABELS = (
    "manca_capospalla",
    "manca_scarpe",
    "manca_formale",
    "manca_invernale",
    "troppe_tshirt",
    "poca_varieta_colori",
)

# Etichette leggibili per la UI.
GAP_HUMAN = {
    "manca_capospalla": "Manca un capospalla (giacca o cappotto)",
    "manca_scarpe": "Poche scarpe per variare",
    "manca_formale": "Mancano capi formali / eleganti",
    "manca_invernale": "Poche alternative invernali",
    "troppe_tshirt": "Troppe t-shirt rispetto al resto",
    "poca_varieta_colori": "Poca varietà di colori (mancano neutri)",
}

WEIGHTS_PATH = Path(
    os.environ.get(
        "CLOSETAI_GAP_WEIGHTS",
        str(PROJECT_ROOT / "ml" / "weights" / "gap_model.pt"),
    )
)

HIDDEN_DIMS = (64, 32)
DROPOUT = 0.2


# ============================================================================
# Feature engineering (condiviso generazione ↔ inferenza)
# ============================================================================


def features_from_counts(
    counts: dict[str, int], *, n_colors: int, has_neutral: bool, ghost_ratio: float
) -> dict[str, float]:
    """Calcola il dizionario di feature a partire dai conteggi per categoria.

    `counts` ha come chiavi le categorie (anche parziali: le mancanti = 0)."""
    c = {cat: int(counts.get(cat, 0)) for cat in CATEGORIES}
    n_total = sum(c.values())
    denom = max(n_total, 1)

    by_role = {"top": 0, "bottom": 0, "outerwear": 0, "shoes": 0, "dress": 0, "accessory": 0}
    for cat, n in c.items():
        by_role[ROLE_OF[cat]] += n

    n_winter = sum(c[cat] for cat in WINTER)
    n_formal = sum(c[cat] for cat in FORMAL)

    return {
        "n_top": by_role["top"],
        "n_bottom": by_role["bottom"],
        "n_outerwear": by_role["outerwear"],
        "n_shoes": by_role["shoes"],
        "n_dress": by_role["dress"],
        "n_accessory": by_role["accessory"],
        "n_total": n_total,
        "frac_tshirt": c["t-shirt"] / denom,
        "frac_outerwear": by_role["outerwear"] / denom,
        "frac_winter": n_winter / denom,
        "frac_formal": n_formal / denom,
        "n_colors": n_colors,
        "has_neutral": 1.0 if has_neutral else 0.0,
        "ghost_ratio": ghost_ratio,
    }


def features_to_vector(feats: dict[str, float]) -> list[float]:
    return [float(feats[name]) for name in FEATURE_NAMES]


def rule_based_gaps(
    counts: dict[str, int], *, n_colors: int, has_neutral: bool, ghost_ratio: float
) -> set[str]:
    """Regole esperte = ground-truth per il dataset sintetico **e** fallback
    runtime quando la rete non è addestrata."""
    c = {cat: int(counts.get(cat, 0)) for cat in CATEGORIES}
    n_total = sum(c.values())
    n_outerwear = c["giacca"] + c["cappotto"]
    n_shoes = c["scarpe"]
    n_formal = sum(c[cat] for cat in FORMAL)
    n_winter = sum(c[cat] for cat in WINTER)

    gaps: set[str] = set()
    if n_outerwear == 0 or (n_total >= 8 and n_outerwear / max(n_total, 1) < 0.10):
        gaps.add("manca_capospalla")
    if n_shoes < 2:
        gaps.add("manca_scarpe")
    if n_formal < 2:
        gaps.add("manca_formale")
    if n_total >= 6 and n_winter < 3:
        gaps.add("manca_invernale")
    if n_total >= 5 and (c["t-shirt"] / max(n_total, 1)) > 0.40:
        gaps.add("troppe_tshirt")
    if n_colors < 3 or not has_neutral:
        gaps.add("poca_varieta_colori")
    return gaps


# ============================================================================
# Rete
# ============================================================================


def build_mlp(in_dim: int = len(FEATURE_NAMES), hidden=HIDDEN_DIMS,
              n_labels: int = len(GAP_LABELS), dropout: float = DROPOUT):
    import torch.nn as nn

    layers: list = []
    prev = in_dim
    for h in hidden:
        layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
        prev = h
    layers.append(nn.Linear(prev, n_labels))  # logits (sigmoid applicata fuori)
    return nn.Sequential(*layers)


@dataclass(frozen=True, slots=True)
class GapPrediction:
    gaps: list[str]                 # label attive (probabilità > soglia)
    probabilities: dict[str, float]
    balanced: bool                  # nessun vuoto rilevato
    source: str                     # "neural-net" | "rules"


class GapClassifier:
    """Carica l'MLP addestrato e predice i vuoti da un feature vector."""

    def __init__(self, weights_path: Path = WEIGHTS_PATH) -> None:
        self.weights_path = weights_path
        self._model = None
        self._mean = None
        self._std = None
        self._labels: tuple[str, ...] = GAP_LABELS
        self._threshold = 0.5

    def is_available(self) -> bool:
        return self.weights_path.is_file()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch

        ckpt = torch.load(self.weights_path, map_location="cpu", weights_only=False)
        self._labels = tuple(ckpt.get("labels", GAP_LABELS))
        self._threshold = float(ckpt.get("threshold", 0.5))
        self._mean = torch.tensor(ckpt["feature_mean"], dtype=torch.float32)
        self._std = torch.tensor(ckpt["feature_std"], dtype=torch.float32)
        model = build_mlp(
            in_dim=len(ckpt.get("features", FEATURE_NAMES)),
            hidden=tuple(ckpt.get("hidden", HIDDEN_DIMS)),
            n_labels=len(self._labels),
            dropout=ckpt.get("dropout", DROPOUT),
        )
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        self._model = model

    def predict(self, feats: dict[str, float]) -> GapPrediction:
        import torch

        self._ensure_loaded()
        assert self._model is not None
        x = torch.tensor(features_to_vector(feats), dtype=torch.float32)
        x = (x - self._mean) / self._std
        with torch.no_grad():
            probs = torch.sigmoid(self._model(x.unsqueeze(0)))[0]
        prob_map = {lab: float(probs[i].item()) for i, lab in enumerate(self._labels)}
        active = [lab for lab, p in prob_map.items() if p >= self._threshold]
        return GapPrediction(
            gaps=active,
            probabilities=prob_map,
            balanced=len(active) == 0,
            source="neural-net",
        )


@lru_cache(maxsize=1)
def get_gap_classifier() -> GapClassifier | None:
    clf = GapClassifier()
    if not clf.is_available():
        return None
    return clf


def reset_gap_classifier_cache() -> None:
    get_gap_classifier.cache_clear()
