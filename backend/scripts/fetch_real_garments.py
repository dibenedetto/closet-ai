"""Scarica immagini *reali* di capi per il dataset di diagnosi stato.

Usa **FashionMNIST** (Xiao et al., 2017) — 70.000 foto reali di capi in 10
categorie — l'unico dataset di abbigliamento servito nativamente da
torchvision. Le immagini originali sono 28×28 in scala di grigi (silhouette
del capo su sfondo nero); le trasformiamo in basi utilizzabili dal nostro
builder:

1. upscale a 256×256,
2. estrazione della silhouette del capo,
3. ricolorazione con un colore della palette, **preservando** ombre e pieghe
   dell'immagine originale (così restano dettagli reali del capo),
4. composizione su sfondo chiaro coerente con `build_condition_dataset.py`.

Il risultato sono forme di capi **reali e varie** (non sagome disegnate a
mano), pronte per essere degradate dal builder.

Uso::

    uv run python scripts/fetch_real_garments.py --count 240
    # poi:
    uv run python scripts/build_condition_dataset.py --per-class 150
    uv run python scripts/train_condition_model.py --no-cache

Le immagini finiscono in ``ml/datasets/source/`` → il builder le rileva
automaticamente come sorgente reale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.color import NAMED_COLORS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_DIR = ROOT / "ml" / "datasets" / "source"
CACHE_DIR = ROOT / "ml" / "datasets" / "_cache"

IMG_SIZE = 256
BG_COLOR = (244, 244, 246)  # coerente con build_condition_dataset.py

# FashionMNIST label → nome categoria. Escludiamo "Bag" (8): non è un capo.
FASHION_MNIST_LABELS = {
    0: "t-shirt",
    1: "pantaloni",
    2: "maglione",
    3: "vestito",
    4: "giacca",
    5: "scarpe",
    6: "camicia",
    7: "scarpe",
    9: "scarpe",
}
EXCLUDED_LABELS = {8}  # Bag


def _colorize(gray_28: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    """Upscale + ricolora la silhouette preservando le ombre originali."""
    gray = np.asarray(
        gray_28.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS), dtype=np.float32
    )
    mask = gray > 30  # il capo (FashionMNIST: capo chiaro su sfondo nero)

    canvas = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.float32)
    canvas[:] = BG_COLOR

    # Modula il colore base con la luminosità originale (0.45–1.0) per
    # mantenere texture, pieghe e bordi reali del capo.
    shade = 0.45 + 0.55 * (gray / 255.0)
    base = np.array(rgb, dtype=np.float32)
    colored = base[None, None, :] * shade[:, :, None]
    canvas[mask] = colored[mask]

    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB")


def fetch(count: int, seed: int) -> None:
    try:
        from torchvision import datasets
    except ImportError:
        print("!! torchvision non installato. Esegui: uv add torchvision")
        sys.exit(1)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    print("==> Scarico FashionMNIST (prima volta ~30MB)…")
    try:
        ds = datasets.FashionMNIST(str(CACHE_DIR), train=True, download=True)
    except Exception as e:
        print(f"!! Download fallito: {e}")
        print("   Verifica la connessione o scarica manualmente in", CACHE_DIR)
        sys.exit(1)

    rng = np.random.default_rng(seed)
    color_names = list(NAMED_COLORS.keys())

    # Indici validi (escludo le borse), mescolati.
    indices = [i for i in range(len(ds)) if int(ds.targets[i]) not in EXCLUDED_LABELS]
    rng.shuffle(indices)
    indices = indices[:count]

    # Pulisci eventuali immagini reali precedenti (mantieni README/.gitkeep)
    for old in SOURCE_DIR.glob("fmnist_*.png"):
        old.unlink()

    from collections import Counter
    cat_counter: Counter[str] = Counter()
    for n, idx in enumerate(indices):
        img, label = ds[idx]
        category = FASHION_MNIST_LABELS.get(int(label), "capo")
        color = color_names[rng.integers(len(color_names))]
        out = _colorize(img, NAMED_COLORS[color])
        out.save(SOURCE_DIR / f"fmnist_{n:04d}_{category}_{color}.png")
        cat_counter[category] += 1

    print(f"==> Salvate {len(indices)} immagini reali in {SOURCE_DIR.relative_to(ROOT)}")
    print(f"    Categorie: {dict(cat_counter)}")
    print("\n    Prossimi passi:")
    print("      uv run python scripts/build_condition_dataset.py --per-class 150")
    print("      uv run python scripts/train_condition_model.py --no-cache")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=240,
                        help="numero di immagini base da estrarre (default 240)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    fetch(count=args.count, seed=args.seed)
