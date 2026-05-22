"""Estrazione del colore dominante.

Versione di Fase 2 (più robusta del semplice averaging di Fase 1):

1. Riduce l'immagine a una thumbnail per velocità.
2. Quantizza i pixel in `N_COLORS` cluster usando l'algoritmo MEDIANCUT di
   Pillow (~equivalente a k-means su un istogramma RGB).
3. Filtra il cluster con luminanza più alta se è "vicino al bianco" e domina
   per frequenza: euristica per ignorare lo sfondo chiaro tipico delle foto
   da app di catalogazione.
4. Restituisce il nome più vicino dalla palette `NAMED_COLORS`.

Sostituibile da Real KMeans (`scikit-learn`) o background-removal (`rembg`)
in Fase 6 se la qualità non basta.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

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

N_COLORS: int = 5
THUMB_SIZE: tuple[int, int] = (128, 128)
# Soglia oltre la quale un cluster chiaro viene considerato "sfondo" e scartato
# se la sua frequenza è dominante.
BG_LUMINANCE_THRESHOLD: int = 220
BG_DOMINANCE_THRESHOLD: float = 0.40


def closest_name(rgb: tuple[int, int, int]) -> str:
    """Restituisce il nome di `NAMED_COLORS` più vicino in distanza euclidea RGB."""
    return min(
        NAMED_COLORS,
        key=lambda name: sum((c - ref) ** 2 for c, ref in zip(rgb, NAMED_COLORS[name])),
    )


def _luminance(rgb: tuple[int, int, int]) -> float:
    """Luminanza percepita (BT.601). 0–255."""
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def dominant_rgb(image_path: str | Path) -> tuple[int, int, int]:
    """Estrae il colore dominante (RGB intero) ignorando lo sfondo chiaro."""
    with Image.open(image_path) as im:
        rgb = im.convert("RGB").resize(THUMB_SIZE, Image.LANCZOS)
        quantized = rgb.quantize(colors=N_COLORS, method=Image.Quantize.MEDIANCUT)

    # `getcolors()` ritorna [(count, palette_idx), ...] per i soli colori usati.
    # Per immagini con pochi colori distinti la palette può non essere piena:
    # itero quindi solo sugli indici realmente presenti nell'istogramma.
    counts = quantized.getcolors(maxcolors=256) or []
    palette = quantized.getpalette() or []
    total = sum(count for count, _ in counts) or 1

    clusters: list[tuple[tuple[int, int, int], float]] = []
    for count, idx in counts:
        base = idx * 3
        if base + 3 > len(palette):
            continue
        rgb_tuple = (palette[base], palette[base + 1], palette[base + 2])
        clusters.append((rgb_tuple, count / total))

    if not clusters:
        # Fallback: campiono il pixel centrale della thumbnail.
        return rgb.getpixel((THUMB_SIZE[0] // 2, THUMB_SIZE[1] // 2))[:3]

    clusters.sort(key=lambda c: c[1], reverse=True)
    top_rgb, top_freq = clusters[0]
    if (
        _luminance(top_rgb) > BG_LUMINANCE_THRESHOLD
        and top_freq > BG_DOMINANCE_THRESHOLD
        and len(clusters) > 1
    ):
        return clusters[1][0]
    return top_rgb


def dominant_color_name(image_path: str | Path) -> str:
    """Pipeline completa: nome del colore dominante."""
    return closest_name(dominant_rgb(image_path))
