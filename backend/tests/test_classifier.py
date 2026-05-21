"""Unit test per il classificatore mock di Fase 1."""

from __future__ import annotations

import random
from pathlib import Path

import pytest
from PIL import Image

from app.ml.classifier import CATEGORIES, NAMED_COLORS, classify


def _save(tmp_path: Path, rgb: tuple[int, int, int], name: str = "img.png") -> Path:
    path = tmp_path / name
    Image.new("RGB", (32, 32), rgb).save(path)
    return path


def test_classify_returns_expected_keys(tmp_path: Path) -> None:
    out = classify(_save(tmp_path, (0, 0, 0)))
    assert set(out.keys()) == {"category", "color"}


def test_category_is_from_fixed_list(tmp_path: Path) -> None:
    out = classify(_save(tmp_path, (128, 128, 128)))
    assert out["category"] in CATEGORIES


def test_category_is_deterministic_with_seeded_rng(tmp_path: Path) -> None:
    img = _save(tmp_path, (128, 128, 128))
    a = classify(img, rng=random.Random(42))
    b = classify(img, rng=random.Random(42))
    assert a["category"] == b["category"]


def test_color_is_one_of_named_colors(tmp_path: Path) -> None:
    out = classify(_save(tmp_path, (250, 30, 30)))
    assert out["color"] in NAMED_COLORS


@pytest.mark.parametrize(
    "rgb,expected",
    [
        ((0, 0, 0), "nero"),
        ((250, 250, 250), "bianco"),
        ((40, 80, 200), "blu"),
        ((200, 30, 30), "rosso"),
        ((60, 160, 60), "verde"),
        ((240, 220, 30), "giallo"),
    ],
)
def test_dominant_color_on_solid_image(
    tmp_path: Path, rgb: tuple[int, int, int], expected: str
) -> None:
    out = classify(_save(tmp_path, rgb))
    assert out["color"] == expected, (
        f"RGB {rgb} → atteso {expected!r}, ottenuto {out['color']!r}"
    )


def test_classify_accepts_str_path(tmp_path: Path) -> None:
    """Sia `str` che `Path` devono essere accettati come argomento."""
    p = _save(tmp_path, (0, 0, 0))
    assert classify(str(p))["color"] == "nero"
