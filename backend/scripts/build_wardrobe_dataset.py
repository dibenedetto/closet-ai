"""Genera il dataset tabellare per la gap analysis del guardaroba.

Ogni riga è un **guardaroba simulato**: conteggi di capi per categoria
(ispirati alle categorie di DeepFashion), copertura colori, stagionalità e
frequenza d'uso. Le **etichette** (vuoti funzionali) sono assegnate da
regole esperte (`gap_model.rule_based_gaps`) con un pizzico di rumore, così
la rete deve *imparare* le soglie invece di memorizzarle.

Profili di guardaroba campionati (per varietà realistica):
- `minimal`    — pochi capi, spesso incompleto
- `balanced`   — distribuzione sana fra le categorie
- `tshirt_heavy` — sbilanciato su t-shirt / casual
- `summer_only`  — niente capi invernali
- `formal`     — molti capi eleganti
- `random`     — campionamento libero

Output: ``ml/datasets/wardrobe/wardrobe_dataset.csv`` (+ stats).

Uso::

    uv run python scripts/build_wardrobe_dataset.py --rows 4000
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.gap_model import (  # noqa: E402
    CATEGORIES, FEATURE_NAMES, GAP_LABELS, features_from_counts,
    rule_based_gaps,
)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "ml" / "datasets" / "wardrobe"
OUT_CSV = OUT_DIR / "wardrobe_dataset.csv"

# Colori "neutri" (coerenti con app/ml/color.py).
NEUTRALS = {"nero", "bianco", "grigio", "beige", "marrone"}
ALL_COLORS = list(NEUTRALS) + ["rosso", "blu", "verde", "giallo", "rosa", "viola", "azzurro", "arancione"]

PROFILES = ("minimal", "balanced", "tshirt_heavy", "summer_only", "formal", "random")


def _sample_counts(profile: str, rng: np.random.Generator) -> dict[str, int]:
    """Campiona i conteggi per categoria secondo il profilo."""
    counts = {cat: 0 for cat in CATEGORIES}

    def pois(lam: float) -> int:
        return int(rng.poisson(lam))

    if profile == "minimal":
        counts["t-shirt"] = pois(2)
        counts["jeans"] = pois(1)
        counts["scarpe"] = pois(1)
        counts["camicia"] = pois(0.5)
    elif profile == "balanced":
        counts["t-shirt"] = pois(5)
        counts["camicia"] = pois(3)
        counts["felpa"] = pois(2)
        counts["maglione"] = pois(3)
        counts["giacca"] = pois(2)
        counts["cappotto"] = pois(1)
        counts["jeans"] = pois(3)
        counts["pantaloni"] = pois(3)
        counts["scarpe"] = pois(4)
        counts["vestito"] = pois(1)
        counts["sciarpa"] = pois(2)
    elif profile == "tshirt_heavy":
        counts["t-shirt"] = pois(15)
        counts["jeans"] = pois(3)
        counts["felpa"] = pois(4)
        counts["scarpe"] = pois(3)
        counts["shorts"] = pois(4)
    elif profile == "summer_only":
        counts["t-shirt"] = pois(8)
        counts["shorts"] = pois(5)
        counts["gonna"] = pois(3)
        counts["vestito"] = pois(3)
        counts["scarpe"] = pois(3)
    elif profile == "formal":
        counts["camicia"] = pois(8)
        counts["giacca"] = pois(4)
        counts["pantaloni"] = pois(6)
        counts["vestito"] = pois(4)
        counts["scarpe"] = pois(4)
        counts["cappotto"] = pois(2)
    else:  # random
        for cat in CATEGORIES:
            counts[cat] = pois(rng.uniform(0, 4))
    return counts


def _sample_colors(counts: dict[str, int], rng: np.random.Generator) -> tuple[int, bool]:
    """Numero di colori distinti + presenza di neutri, plausibile col n. capi."""
    n_total = sum(counts.values())
    if n_total == 0:
        return 0, False
    max_colors = min(len(ALL_COLORS), max(1, n_total))
    n_colors = int(rng.integers(1, max_colors + 1))
    chosen = rng.choice(ALL_COLORS, size=n_colors, replace=False)
    has_neutral = any(col in NEUTRALS for col in chosen)
    return n_colors, has_neutral


def generate(rows: int, seed: int, noise: float) -> None:
    rng = np.random.default_rng(seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    header = list(FEATURE_NAMES) + list(GAP_LABELS) + ["profile"]
    label_counter = {lab: 0 for lab in GAP_LABELS}
    balanced_count = 0

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for _ in range(rows):
            profile = str(rng.choice(PROFILES))
            counts = _sample_counts(profile, rng)
            n_colors, has_neutral = _sample_colors(counts, rng)
            ghost_ratio = float(rng.beta(2, 5))  # tipicamente 0.1-0.4

            feats = features_from_counts(
                counts, n_colors=n_colors, has_neutral=has_neutral, ghost_ratio=ghost_ratio
            )
            gaps = rule_based_gaps(
                counts, n_colors=n_colors, has_neutral=has_neutral, ghost_ratio=ghost_ratio
            )

            # Rumore: con prob `noise` flippa una label a caso (etichettatura imperfetta).
            label_vec = {lab: (1 if lab in gaps else 0) for lab in GAP_LABELS}
            if rng.random() < noise:
                flip = str(rng.choice(GAP_LABELS))
                label_vec[flip] = 1 - label_vec[flip]

            for lab, v in label_vec.items():
                label_counter[lab] += v
            if sum(label_vec.values()) == 0:
                balanced_count += 1

            row = [round(feats[name], 4) for name in FEATURE_NAMES]
            row += [label_vec[lab] for lab in GAP_LABELS]
            row.append(profile)
            w.writerow(row)

    print(f"==> Dataset generato: {OUT_CSV.relative_to(ROOT)}  ({rows} righe)")
    print("    Frequenza vuoti (label positive):")
    for lab, n in label_counter.items():
        print(f"      {lab:22s} {n:5d}  ({n / rows:.0%})")
    print(f"    Guardaroba equilibrati (nessun vuoto): {balanced_count} ({balanced_count / rows:.0%})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--noise", type=float, default=0.08,
                        help="prob. di flip di una label (etichettatura imperfetta)")
    args = parser.parse_args()
    generate(rows=args.rows, seed=args.seed, noise=args.noise)
