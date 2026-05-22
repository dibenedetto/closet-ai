"""Unit test del classificatore mock e dell'estrazione colore."""

from __future__ import annotations

import random
from pathlib import Path

import pytest
from PIL import Image

from app.ml.classifier import CATEGORIES, ClassificationResult, MockClassifier, classify
from app.ml.color import NAMED_COLORS, dominant_color_name


def _save(tmp_path: Path, rgb: tuple[int, int, int], name: str = "img.png") -> Path:
    path = tmp_path / name
    Image.new("RGB", (32, 32), rgb).save(path)
    return path


# ----- classifier --------------------------------------------------------


def test_classify_returns_classification_result(tmp_path: Path) -> None:
    out = classify(_save(tmp_path, (0, 0, 0)))
    assert isinstance(out, ClassificationResult)
    assert out.category is not None
    assert out.color is not None


def test_mock_category_is_from_fixed_list(tmp_path: Path) -> None:
    out = MockClassifier().classify(_save(tmp_path, (128, 128, 128)))
    assert out.category in CATEGORIES
    # Il mock non produce embedding né confidence
    assert out.embedding is None
    assert out.confidence is None


def test_mock_category_is_deterministic_with_seeded_rng(tmp_path: Path) -> None:
    img = _save(tmp_path, (128, 128, 128))
    a = MockClassifier(rng=random.Random(42)).classify(img)
    b = MockClassifier(rng=random.Random(42)).classify(img)
    assert a.category == b.category


def test_classify_legacy_rng_argument(tmp_path: Path) -> None:
    """`classify(path, rng=...)` deve restare deterministico anche dopo il refactor."""
    img = _save(tmp_path, (128, 128, 128))
    a = classify(img, rng=random.Random(7))
    b = classify(img, rng=random.Random(7))
    assert a.category == b.category


def test_classify_accepts_str_path(tmp_path: Path) -> None:
    p = _save(tmp_path, (0, 0, 0))
    assert classify(str(p)).color == "nero"


# ----- dominant color ----------------------------------------------------


@pytest.mark.parametrize(
    "rgb,expected",
    [
        ((0, 0, 0), "nero"),
        ((40, 80, 200), "blu"),
        ((200, 30, 30), "rosso"),
        ((60, 160, 60), "verde"),
        ((240, 220, 30), "giallo"),
    ],
)
def test_dominant_color_on_solid_image(
    tmp_path: Path, rgb: tuple[int, int, int], expected: str
) -> None:
    assert dominant_color_name(_save(tmp_path, rgb)) == expected


def test_color_is_one_of_named_colors(tmp_path: Path) -> None:
    """Per qualunque colore solido, il risultato è uno dei nomi noti."""
    assert dominant_color_name(_save(tmp_path, (123, 45, 67))) in NAMED_COLORS


def test_background_filter_picks_garment_not_background(tmp_path: Path) -> None:
    """Capo blu su sfondo bianco prevalente -> deve restituire 'blu', non 'bianco'."""
    img_path = tmp_path / "garment_on_white.png"
    canvas = Image.new("RGB", (200, 200), (250, 250, 250))  # ~70% sfondo
    # Riquadro centrale blu (~24% di area, sotto la soglia di "dominanza" bg)
    blue = Image.new("RGB", (100, 100), (40, 80, 200))
    canvas.paste(blue, (50, 50))
    canvas.save(img_path)

    assert dominant_color_name(img_path) == "blu"
