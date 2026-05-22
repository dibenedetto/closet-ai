"""Score di compatibilità cromatica fra due colori del guardaroba.

Regole (intuizioni dalla color theory, non un'esposizione formale):

- I colori **neutri** (saturazione bassa → nero, bianco, grigio, beige,
  marrone) hanno score alto con qualunque altro colore: sono i "jolly".
- I colori **analoghi** (differenza di hue ≤ 30°) hanno buona compatibilità.
- I colori **complementari** (differenza di hue ≈ 180°, finestra ±25°)
  hanno buona compatibilità "contrastante".
- Le **split-complementari** (≈ 150° / ≈ 210°) hanno score medio.
- Combinazioni intermedie ricevono score basso.

Lo score finale è in [0, 1]; valori più alti = maggior compatibilità.
"""

from __future__ import annotations

from colorsys import rgb_to_hls

from app.ml.color import NAMED_COLORS

# Whitelist nominale dei neutri: copre casi come "beige" e "marrone" che
# hanno saturazione abbastanza alta ma sono percepiti come neutri.
NEUTRAL_NAMES: frozenset[str] = frozenset({"nero", "bianco", "grigio", "beige", "marrone"})
# Soglia sotto la quale consideriamo un colore "neutro" anche se non in whitelist.
NEUTRAL_SATURATION_THRESHOLD = 0.18
# Score per coppia di colori uguali / identica famiglia.
SAME_COLOR_SCORE = 0.85
# Pesi delle fasce di compatibilità.
ANALOGOUS_WINDOW_DEG = 35.0
ANALOGOUS_SCORE = 0.90
COMPLEMENTARY_WINDOW_DEG = 25.0
COMPLEMENTARY_SCORE = 0.85
SPLIT_COMPLEMENTARY_WINDOW_DEG = 25.0
SPLIT_COMPLEMENTARY_SCORE = 0.70
DEFAULT_SCORE = 0.45


def _rgb_to_hsl(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Converte RGB 0-255 in HSL con H in gradi 0-360, S e L in 0-1."""
    r, g, b = (c / 255.0 for c in rgb)
    hue, lightness, saturation = rgb_to_hls(r, g, b)
    return hue * 360.0, saturation, lightness


def _hue_distance(h1: float, h2: float) -> float:
    """Distanza circolare di hue in gradi (0-180)."""
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)


def is_neutral(name: str) -> bool:
    if name in NEUTRAL_NAMES:
        return True
    rgb = NAMED_COLORS.get(name)
    if rgb is None:
        return False
    _, s, _ = _rgb_to_hsl(rgb)
    return s <= NEUTRAL_SATURATION_THRESHOLD


def color_compat_score(name_a: str | None, name_b: str | None) -> float:
    """Score di compatibilità in [0, 1] fra due colori nominati.

    Se uno dei due è ignoto/None, ritorna 0.5 (neutro/incerto). Se sono uguali,
    ritorna `SAME_COLOR_SCORE`.
    """
    if not name_a or not name_b:
        return 0.5
    if name_a == name_b:
        return SAME_COLOR_SCORE
    if name_a not in NAMED_COLORS or name_b not in NAMED_COLORS:
        return 0.5

    if is_neutral(name_a) or is_neutral(name_b):
        return 0.92

    h_a, _, _ = _rgb_to_hsl(NAMED_COLORS[name_a])
    h_b, _, _ = _rgb_to_hsl(NAMED_COLORS[name_b])
    d = _hue_distance(h_a, h_b)

    if d <= ANALOGOUS_WINDOW_DEG:
        return ANALOGOUS_SCORE
    if abs(d - 180.0) <= COMPLEMENTARY_WINDOW_DEG:
        return COMPLEMENTARY_SCORE
    if abs(d - 150.0) <= SPLIT_COMPLEMENTARY_WINDOW_DEG / 2:
        return SPLIT_COMPLEMENTARY_SCORE
    return DEFAULT_SCORE


def palette_compat_score(colors: list[str | None]) -> float:
    """Score medio di compatibilità di una palette (lista colori)."""
    pairs: list[float] = []
    for i, a in enumerate(colors):
        for b in colors[i + 1 :]:
            pairs.append(color_compat_score(a, b))
    if not pairs:
        return 0.5
    return sum(pairs) / len(pairs)
