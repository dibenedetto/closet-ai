"""Benchmark dei classificatori (Mock vs Fashion-CLIP).

Esegui con:
    uv run python scripts/benchmark_classifier.py

Output: tempo medio per inferenza su un'immagine 512x512 generata. Per il
modello reale il primo run scarica ~600MB di pesi e impiega più tempo (warmup);
i tempi riportati sono dopo warmup.
"""

from __future__ import annotations

import io
import statistics
import sys
import tempfile
import time
from pathlib import Path

# Bootstrap: lo script vive in backend/scripts/, ma importa da backend/app/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from app.ml.classifier import FashionClipClassifier, MockClassifier  # noqa: E402


def make_test_image(path: Path, rgb: tuple[int, int, int] = (40, 80, 200)) -> None:
    """Genera un'immagine 512x512 con un capo "vagamente plausibile"."""
    img = Image.new("RGB", (512, 512), (245, 245, 245))
    # rettangolo centrale come "capo"
    canvas = io.BytesIO()
    garment = Image.new("RGB", (300, 400), rgb)
    img.paste(garment, (106, 56))
    img.save(path, format="PNG")
    del canvas


def benchmark(name: str, classifier, image_path: Path, runs: int = 5) -> None:
    print(f"\n=== {name} ===")
    # warmup
    t0 = time.perf_counter()
    classifier.classify(image_path)
    warmup = time.perf_counter() - t0
    print(f"  warmup:      {warmup * 1000:8.2f} ms")

    times: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        result = classifier.classify(image_path)
        times.append(time.perf_counter() - t0)
    print(f"  runs:        {runs}")
    print(f"  mean:        {statistics.mean(times) * 1000:8.2f} ms")
    print(f"  median:      {statistics.median(times) * 1000:8.2f} ms")
    print(f"  stdev:       {statistics.stdev(times) * 1000 if len(times) > 1 else 0:8.2f} ms")
    print(f"  category:    {result.category}")
    print(f"  color:       {result.color}")
    print(f"  confidence:  {result.confidence}")
    print(f"  has embed.:  {result.embedding is not None} (dim={len(result.embedding or [])})")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        img_path = tmp_dir / "garment.png"
        make_test_image(img_path)

        benchmark("Mock", MockClassifier(), img_path, runs=20)
        benchmark("Fashion-CLIP (CPU)", FashionClipClassifier(), img_path, runs=5)


if __name__ == "__main__":
    main()
