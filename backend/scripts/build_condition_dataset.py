"""Costruttore del dataset per la diagnosi dello *stato di conservazione*.

Problema: non esiste un dataset pubblico che etichetti i capi per stato
d'usura (nuovo / buono / usurato / danneggiato). Lo costruiamo con
**degradazione sintetica controllata**: partiamo da immagini di capi in
buono stato e applichiamo trasformazioni che simulano l'usura, ottenendo
coppie (immagine, stato) etichettate in automatico.

Sorgenti delle immagini base, in ordine di preferenza:

1. ``ml/datasets/source/`` — se contiene immagini (jpg/png/webp), le usa
   come capi "puliti" da degradare. **Metti qui le tue foto reali** o un
   dataset scaricato (es. Fashion Product Images da Kaggle).
2. Bootstrap sintetico — se la cartella è vuota, genera sagome stilizzate
   di capi (t-shirt, pantaloni, vestito, …) con PIL. Utile per far girare
   la pipeline end-to-end senza scaricare nulla, ma le immagini sono
   "icone", non foto: vanno bene per validare il codice, non per il
   training finale.

Output in ``ml/datasets/garment_condition/``:

- ``images/{nuovo,buono,usurato,danneggiato}/*.png`` — immagini etichettate
- ``manifest.csv`` — una riga per immagine (path, categoria, colore,
  stato, difetto, severità, split train/val/test)
- ``vlm_dataset.jsonl`` — formato instruction-tuning per fine-tuning di un
  Visual-LLM (LoRA): ogni riga è una conversazione image→{stato, tutorial}
- ``preview.png`` — griglia di anteprima (un esempio per stato)

Uso::

    uv run python scripts/build_condition_dataset.py --per-class 60
    uv run python scripts/build_condition_dataset.py --source-dir ml/datasets/source

Vedi ``docs/dataset-datasheet.md`` per la scheda completa del dataset.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.color import NAMED_COLORS  # noqa: E402
from app.services import repair_tutorials  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_DIR = ROOT / "ml" / "datasets" / "source"
OUT_DIR = ROOT / "ml" / "datasets" / "garment_condition"

IMG_SIZE = 256
BG_COLOR = (244, 244, 246)

CONDITIONS = ("nuovo", "buono", "usurato", "danneggiato")

# Capi disegnabili come sagome nel bootstrap sintetico.
SHAPE_CATEGORIES = (
    "t-shirt", "maglione", "pantaloni", "jeans", "gonna", "vestito",
)

# Mappa difetto -> defect della knowledge base tutorial (per il dataset VLM).
DEFECT_TO_KB = {
    "scolorimento": "scolorimento",
    "macchia": "macchia",
    "strappo": "strappo",
    "buco": "buco",
    "pilling": "scolorimento",  # il pilling lo trattiamo come cura del tessuto
}


@dataclass
class Sample:
    filename: str
    category: str
    color: str
    condition: str
    defect: str | None
    severity: float
    split: str = "train"
    extra: dict = field(default_factory=dict)


# ============================================================================
# 1 · Immagini base
# ============================================================================


def _draw_garment(category: str, rgb: tuple[int, int, int]) -> Image.Image:
    """Disegna una sagoma stilizzata di capo su sfondo neutro."""
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), BG_COLOR)
    d = ImageDraw.Draw(img)
    cx = IMG_SIZE // 2
    fill = rgb
    outline = tuple(max(0, c - 40) for c in rgb)

    if category in ("t-shirt", "maglione"):
        # corpo
        body = [(cx - 55, 80), (cx + 55, 80), (cx + 50, 210), (cx - 50, 210)]
        d.polygon(body, fill=fill, outline=outline)
        # maniche
        sleeve_len = 70 if category == "maglione" else 40
        d.polygon([(cx - 55, 80), (cx - 95, 90 + sleeve_len), (cx - 75, 100 + sleeve_len),
                   (cx - 50, 110)], fill=fill, outline=outline)
        d.polygon([(cx + 55, 80), (cx + 95, 90 + sleeve_len), (cx + 75, 100 + sleeve_len),
                   (cx + 50, 110)], fill=fill, outline=outline)
        # colletto
        d.ellipse([(cx - 22, 70), (cx + 22, 95)], fill=BG_COLOR, outline=outline)
    elif category in ("pantaloni", "jeans"):
        d.polygon([(cx - 45, 60), (cx + 45, 60), (cx + 42, 95), (cx - 42, 95)],
                  fill=fill, outline=outline)
        # gamba sinistra
        d.polygon([(cx - 42, 95), (cx - 4, 95), (cx - 8, 215), (cx - 40, 215)],
                  fill=fill, outline=outline)
        # gamba destra
        d.polygon([(cx + 4, 95), (cx + 42, 95), (cx + 40, 215), (cx + 8, 215)],
                  fill=fill, outline=outline)
    elif category == "gonna":
        d.polygon([(cx - 40, 90), (cx + 40, 90), (cx + 70, 200), (cx - 70, 200)],
                  fill=fill, outline=outline)
    elif category == "vestito":
        d.polygon([(cx - 35, 70), (cx + 35, 70), (cx + 25, 110), (cx + 65, 210),
                   (cx - 65, 210), (cx - 25, 110)], fill=fill, outline=outline)
        d.ellipse([(cx - 18, 62), (cx + 18, 84)], fill=BG_COLOR, outline=outline)
    else:
        d.rounded_rectangle([(cx - 55, 75), (cx + 55, 205)], radius=14,
                            fill=fill, outline=outline)

    return img.filter(ImageFilter.SMOOTH)


def _load_source_images() -> list[Image.Image]:
    if not SOURCE_DIR.is_dir():
        return []
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    paths = [p for p in SOURCE_DIR.iterdir() if p.suffix.lower() in exts]
    images = []
    for p in sorted(paths):
        try:
            im = Image.open(p).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            images.append(im)
        except Exception:
            continue
    return images


# ============================================================================
# 2 · Degradazioni sintetiche
# ============================================================================


def _to_arr(img: Image.Image) -> np.ndarray:
    return np.asarray(img, dtype=np.float32)


def _to_img(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _garment_mask(img: Image.Image) -> np.ndarray:
    """Maschera booleana: True dove c'è il capo (pixel diversi dallo sfondo)."""
    arr = _to_arr(img)
    bg = np.array(BG_COLOR, dtype=np.float32)
    dist = np.linalg.norm(arr - bg, axis=2)
    return dist > 25


def apply_fading(img: Image.Image, severity: float, rng: random.Random) -> Image.Image:
    """Sbiadimento: riduce la saturazione e schiarisce (capo lavato troppe volte)."""
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32)
    hsv[..., 1] *= (1.0 - 0.6 * severity)  # meno saturazione
    hsv[..., 2] = np.clip(hsv[..., 2] * (1.0 + 0.15 * severity) + 20 * severity, 0, 255)
    out = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")
    return out


def apply_pilling(img: Image.Image, severity: float, rng: random.Random) -> Image.Image:
    """Pilling / micro-pallini: rumore granulare chiaro a chiazze sul tessuto."""
    arr = _to_arr(img)
    mask = _garment_mask(img)
    noise = rng_normal(rng, arr.shape[:2], 0, 30 * severity)
    # chiazze: moltiplica per un campo a bassa frequenza
    blob = _low_freq_field(arr.shape[:2], rng)
    noise = noise * blob
    for c in range(3):
        arr[..., c][mask] += noise[mask]
    return _to_img(arr)


def apply_wrinkles(img: Image.Image, severity: float, rng: random.Random) -> Image.Image:
    """Pieghe: bande d'ombra morbide diagonali."""
    arr = _to_arr(img)
    mask = _garment_mask(img)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    n_wrinkles = 2 + int(4 * severity)
    shadow = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_wrinkles):
        angle = rng.uniform(0, math.pi)
        freq = rng.uniform(0.04, 0.09)
        phase = rng.uniform(0, 2 * math.pi)
        wave = np.sin((xx * math.cos(angle) + yy * math.sin(angle)) * freq + phase)
        shadow += wave
    shadow = (shadow / n_wrinkles) * 35 * severity
    for c in range(3):
        arr[..., c][mask] += shadow[mask]
    return _to_img(arr)


def apply_stain(img: Image.Image, severity: float, rng: random.Random) -> Image.Image:
    """Macchia: blob ellittico scuro/marrone semitrasparente."""
    img = img.copy()
    d = ImageDraw.Draw(img, "RGBA")
    mask_idx = np.argwhere(_garment_mask(img))
    if len(mask_idx) == 0:
        return img
    n_stains = 1 + int(2 * severity)
    for _ in range(n_stains):
        cy, cx = mask_idx[rng.randrange(len(mask_idx))]
        r = int(rng.uniform(12, 30) * (0.6 + severity))
        stain_col = rng.choice([(60, 40, 20), (40, 30, 20), (30, 30, 35)])
        alpha = int(120 + 100 * severity)
        d.ellipse([(cx - r, cy - r), (cx + r, cy + int(r * 1.3))],
                  fill=(*stain_col, alpha))
    return img.convert("RGB")


def apply_tear(img: Image.Image, severity: float, rng: random.Random) -> Image.Image:
    """Strappo: linea frastagliata che mostra lo 'sfondo' attraverso il capo."""
    img = img.copy()
    d = ImageDraw.Draw(img)
    mask_idx = np.argwhere(_garment_mask(img))
    if len(mask_idx) == 0:
        return img
    cy, cx = mask_idx[rng.randrange(len(mask_idx))]
    length = int(rng.uniform(30, 70) * (0.6 + severity))
    angle = rng.uniform(0, 2 * math.pi)
    points = [(cx, cy)]
    x, y = float(cx), float(cy)
    steps = max(4, length // 6)
    for _ in range(steps):
        x += math.cos(angle) * 6 + rng.uniform(-4, 4)
        y += math.sin(angle) * 6 + rng.uniform(-4, 4)
        points.append((x, y))
    # bordo scuro + interno colore sfondo (buco aperto)
    d.line(points, fill=(20, 20, 25), width=4)
    d.line(points, fill=BG_COLOR, width=2)
    return img


def apply_hole(img: Image.Image, severity: float, rng: random.Random) -> Image.Image:
    """Buco: ellisse del colore di sfondo con alone scuro."""
    img = img.copy()
    d = ImageDraw.Draw(img)
    mask_idx = np.argwhere(_garment_mask(img))
    if len(mask_idx) == 0:
        return img
    cy, cx = mask_idx[rng.randrange(len(mask_idx))]
    r = int(rng.uniform(8, 20) * (0.6 + severity))
    d.ellipse([(cx - r - 2, cy - r - 2), (cx + r + 2, cy + r + 2)], fill=(30, 30, 35))
    d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=BG_COLOR)
    return img


# --- helper rumore ---------------------------------------------------------


def rng_normal(rng: random.Random, shape, mean: float, std: float) -> np.ndarray:
    np_rng = np.random.default_rng(rng.randrange(2**32))
    return np_rng.normal(mean, std, shape).astype(np.float32)


def _low_freq_field(shape, rng: random.Random) -> np.ndarray:
    """Campo a bassa frequenza in [0,1] per modulare le chiazze."""
    h, w = shape
    small = np.random.default_rng(rng.randrange(2**32)).random((8, 8)).astype(np.float32)
    field = np.asarray(
        Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
        dtype=np.float32,
    ) / 255.0
    return field


# ============================================================================
# 3 · Assemblaggio condizioni
# ============================================================================


def make_condition(base: Image.Image, condition: str, rng: random.Random
                   ) -> tuple[Image.Image, str | None, float]:
    """Applica le degradazioni corrispondenti allo stato. Ritorna
    (immagine, difetto_principale, severità)."""
    if condition == "nuovo":
        # capo come nuovo: nessuna degradazione, eventuale micro-luce
        img = apply_wrinkles(base, 0.1, rng)
        return img, None, 0.0

    if condition == "buono":
        sev = rng.uniform(0.15, 0.35)
        img = apply_wrinkles(base, sev, rng)
        img = apply_fading(img, sev * 0.4, rng)
        return img, None, sev

    if condition == "usurato":
        sev = rng.uniform(0.45, 0.7)
        img = apply_fading(base, sev, rng)
        img = apply_pilling(img, sev, rng)
        img = apply_wrinkles(img, sev * 0.8, rng)
        defect = rng.choice(["scolorimento", "pilling"])
        return img, defect, sev

    # danneggiato
    sev = rng.uniform(0.7, 1.0)
    img = apply_fading(base, sev * 0.6, rng)
    img = apply_wrinkles(img, sev * 0.6, rng)
    defect = rng.choice(["macchia", "strappo", "buco"])
    if defect == "macchia":
        img = apply_stain(img, sev, rng)
    elif defect == "strappo":
        img = apply_tear(img, sev, rng)
    else:
        img = apply_hole(img, sev, rng)
    return img, defect, sev


# ============================================================================
# 4 · Dataset VLM (instruction tuning)
# ============================================================================

_VLM_INSTRUCTION = (
    "Osserva la foto del capo di abbigliamento. Valuta il suo stato di "
    "conservazione (nuovo, buono, usurato o danneggiato) e, se serve, "
    "suggerisci un breve tutorial per migliorarlo. Rispondi in JSON."
)


def _vlm_record(sample: Sample, rel_image_path: str) -> dict:
    """Costruisce un record instruction-tuning con risposta strutturata.

    Il tutorial proviene dalla knowledge base hardcoded (`repair_tutorials`),
    così le risposte sono coerenti e verificabili, non inventate."""
    tutorial_text = None
    if sample.defect:
        kb_defect = DEFECT_TO_KB.get(sample.defect)
        tut = repair_tutorials.get_tutorial(kb_defect, category=sample.category)
        steps = " ".join(f"{i+1}) {s}" for i, s in enumerate(tut.steps))
        tutorial_text = f"{tut.title}. {steps}"

    answer = {
        "stato": sample.condition,
        "difetto": sample.defect,
        "tutorial": tutorial_text,
    }
    return {
        "image": rel_image_path,
        "messages": [
            {"role": "user", "content": f"<image>\n{_VLM_INSTRUCTION}"},
            {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
        ],
    }


# ============================================================================
# 5 · Build
# ============================================================================


def _assign_split(rng: random.Random) -> str:
    r = rng.random()
    if r < 0.7:
        return "train"
    if r < 0.85:
        return "val"
    return "test"


def build(per_class: int, seed: int) -> None:
    rng = random.Random(seed)

    source_images = _load_source_images()
    use_source = len(source_images) > 0
    print(f"==> Sorgente immagini base: "
          f"{'cartella source/ (' + str(len(source_images)) + ' immagini reali)' if use_source else 'bootstrap sintetico'}")

    # Reset cartelle output
    images_root = OUT_DIR / "images"
    for cond in CONDITIONS:
        (images_root / cond).mkdir(parents=True, exist_ok=True)
        for old in (images_root / cond).glob("*.png"):
            old.unlink()

    samples: list[Sample] = []
    idx = 0
    for cond in CONDITIONS:
        for _ in range(per_class):
            # 1. immagine base
            if use_source:
                base = source_images[rng.randrange(len(source_images))].copy()
                category = "sconosciuto"
                color = "sconosciuto"
            else:
                category = rng.choice(SHAPE_CATEGORIES)
                color = rng.choice(list(NAMED_COLORS.keys()))
                base = _draw_garment(category, NAMED_COLORS[color])

            # 2. degradazione
            img, defect, severity = make_condition(base, cond, rng)

            # 3. salva
            filename = f"{cond}_{idx:04d}.png"
            img.save(images_root / cond / filename)
            samples.append(Sample(
                filename=f"images/{cond}/{filename}",
                category=category,
                color=color,
                condition=cond,
                defect=defect,
                severity=round(severity, 3),
                split=_assign_split(rng),
            ))
            idx += 1

    # manifest.csv
    manifest_path = OUT_DIR / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "category", "color", "condition", "defect", "severity", "split"])
        for s in samples:
            w.writerow([s.filename, s.category, s.color, s.condition,
                        s.defect or "", s.severity, s.split])

    # vlm_dataset.jsonl
    vlm_path = OUT_DIR / "vlm_dataset.jsonl"
    with vlm_path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(_vlm_record(s, s.filename), ensure_ascii=False) + "\n")

    # preview.png (un esempio per stato)
    _write_preview(samples)

    # stats
    from collections import Counter
    by_cond = Counter(s.condition for s in samples)
    by_split = Counter(s.split for s in samples)
    print(f"==> Dataset generato in {OUT_DIR}")
    print(f"    Totale immagini: {len(samples)}")
    print(f"    Per stato:  {dict(by_cond)}")
    print(f"    Per split:  {dict(by_split)}")
    print(f"    manifest:   {manifest_path.relative_to(ROOT)}")
    print(f"    VLM jsonl:  {vlm_path.relative_to(ROOT)}")
    if not use_source:
        print("    NB: immagini sintetiche (bootstrap). Per il training reale,")
        print(f"        metti foto vere in {SOURCE_DIR.relative_to(ROOT)} e rilancia.")


def _write_preview(samples: list[Sample]) -> None:
    cell = IMG_SIZE
    grid = Image.new("RGB", (cell * len(CONDITIONS), cell + 30), (255, 255, 255))
    d = ImageDraw.Draw(grid)
    for i, cond in enumerate(CONDITIONS):
        example = next((s for s in samples if s.condition == cond), None)
        if example is None:
            continue
        im = Image.open(OUT_DIR / example.filename)
        grid.paste(im, (i * cell, 30))
        d.text((i * cell + 8, 8), cond.upper(), fill=(20, 20, 30))
    grid.save(OUT_DIR / "preview.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-class", type=int, default=60,
                        help="immagini per stato (default 60 → 240 totali)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--source-dir", type=str, default=None,
                        help="cartella con immagini base reali (override)")
    args = parser.parse_args()

    if args.source_dir:
        SOURCE_DIR = Path(args.source_dir).resolve()  # noqa: F811

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build(per_class=args.per_class, seed=args.seed)
