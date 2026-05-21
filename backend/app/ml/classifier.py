"""Classificatore *mock* per la Fase 1.

Restituisce una categoria casuale da una lista fissa e un nome di colore
ricavato in modo deterministico dall'immagine. Sostituibile in Fase 2 da
un modello CLIP / fashion classifier reale che esponga la stessa interfaccia
`classify(image_path) -> dict`.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

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

# Palette di colori "nominabili" con RGB di riferimento. Il colore più vicino
# (distanza euclidea nello spazio RGB) viene scelto come etichetta.
NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "nero": (20, 20, 20),
    "bianco": (240, 240, 240),
    "grigio": (128, 128, 128),
    "rosso": (200, 30, 30),
    "arancione": (230, 130, 30),
    "giallo": (240, 220, 30),
    "verde": (60, 160, 60),
    "azzurro": (90, 170, 230),
    "blu": (40, 80, 200),
    "viola": (140, 60, 180),
    "rosa": (240, 130, 170),
    "marrone": (110, 70, 40),
    "beige": (220, 200, 170),
}


def _dominant_color_name(image_path: Path) -> str:
    """Stima il colore dominante dell'immagine e lo mappa al nome più vicino.

    Il resize a 1×1 con LANCZOS produce la media ponderata dei pixel: per il
    mock di Fase 1 è sufficiente. La Fase 2 sostituirà questa funzione con
    quantizzazione (k-means / `Image.quantize`) che ignora lo sfondo.
    """
    with Image.open(image_path) as im:
        pixel = im.convert("RGB").resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    return _closest_name(pixel)


def _closest_name(rgb: tuple[int, int, int]) -> str:
    return min(
        NAMED_COLORS,
        key=lambda name: sum((c - ref) ** 2 for c, ref in zip(rgb, NAMED_COLORS[name])),
    )


def classify(image_path: str | Path, *, rng: random.Random | None = None) -> dict[str, str]:
    """Restituisce `{category, color}` per l'immagine indicata.

    `rng` permette di iniettare un `random.Random` deterministico nei test;
    di default usa il modulo `random` globale (non riproducibile).
    """
    rng = rng or random.Random()
    return {
        "category": rng.choice(CATEGORIES),
        "color": _dominant_color_name(Path(image_path)),
    }
