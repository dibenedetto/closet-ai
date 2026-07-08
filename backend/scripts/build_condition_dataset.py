"""Costruttore del dataset per la diagnosi dello *stato di conservazione*.

Problema: non esiste un dataset pubblico che etichetti i capi per stato
d'usura (buono / usurato / danneggiato). Lo costruiamo con
**degradazione sintetica controllata**: partiamo da immagini di capi in
buono stato e applichiamo trasformazioni che simulano l'usura, ottenendo
coppie (immagine, stato) etichettate in automatico.

Sorgenti delle immagini, in ordine di preferenza:

1. ``ml/datasets/Defect-Clothes.v3i.coco/`` — dataset COCO (Roboflow,
   CC BY 4.0) con **difetti reali annotati**: cut→strappo, hole→buco,
   stain→macchia. Modalità **ibrida**: i `danneggiato` sono foto reali di
   danni veri; buono/usurato derivano dalle foto pulite dello stesso
   dataset (usurato con degradazione sintetica, il COCO non ha la classe
   "consumato"). Disattivabile con ``--no-coco``.
2. ``ml/datasets/source/`` — se contiene immagini (jpg/png/webp), le usa
   come capi "puliti" da degradare (es. output di `fetch_real_garments.py`).
3. Bootstrap sintetico — sagome stilizzate PIL. Solo per validare la
   pipeline, non per il training finale.

Output in ``ml/datasets/garment_condition/``:

- ``images/{buono,usurato,danneggiato}/*.png`` — immagini etichettate
- ``manifest.csv`` — una riga per immagine (path, categoria, colore,
  stato, difetto, severità, split train/val/test)
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

from app.ml.color import NAMED_COLORS, dominant_color_name  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_DIR = ROOT / "ml" / "datasets" / "source"
OUT_DIR = ROOT / "ml" / "datasets" / "garment_condition"
COCO_DIR_DEFAULT = ROOT / "ml" / "datasets" / "Defect-Clothes.v3i.coco"

# Categorie COCO (Roboflow Defect-Clothes) → nostri difetti; priorità di
# assegnazione quando un'immagine ha più difetti.
COCO_DEFECT_MAP = {"cut": "strappo", "hole": "buco", "stain": "macchia"}
COCO_DEFECT_PRIORITY = ("cut", "hole", "stain")

IMG_SIZE = 256
BG_COLOR = (244, 244, 246)

# "nuovo" fuso in "buono": su foto reali il confine era artificiale (solo
# pieghe sintetiche leggere) e produceva confusione — vedi datasheet.
CONDITIONS = ("buono", "usurato", "danneggiato")

# Capi disegnabili come sagome nel bootstrap sintetico.
SHAPE_CATEGORIES = (
    "t-shirt", "maglione", "pantaloni", "jeans", "gonna", "vestito",
)


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


def _load_coco_index(coco_dir: Path) -> dict | None:
    """Indicizza il dataset COCO: foto pulite vs foto con difetto reale.

    Ritorna ``{"clean": [Path], "defect": [(Path, difetto)]}`` oppure None
    se la cartella non esiste o non contiene annotazioni valide."""
    if not coco_dir.is_dir():
        return None
    clean: list[Path] = []
    defect: list[tuple[Path, str]] = []
    for split in ("train", "valid", "test"):
        ann_path = coco_dir / split / "_annotations.coco.json"
        if not ann_path.is_file():
            continue
        try:
            data = json.loads(ann_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cats = {c["id"]: c["name"] for c in data.get("categories", [])}
        names_by_img: dict[int, set[str]] = {}
        for a in data.get("annotations", []):
            names_by_img.setdefault(a["image_id"], set()).add(cats.get(a["category_id"], ""))
        for img in data.get("images", []):
            path = coco_dir / split / img["file_name"]
            if not path.is_file():
                continue
            names = names_by_img.get(img["id"], set())
            found = None
            for coco_name in COCO_DEFECT_PRIORITY:
                if coco_name in names:
                    found = COCO_DEFECT_MAP[coco_name]
                    break
            if found:
                defect.append((path, found))
            else:
                clean.append(path)
    if not clean and not defect:
        return None
    return {"clean": clean, "defect": defect}


def _load_real_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)


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
    if condition == "buono":
        # Classe fusa (ex nuovo+buono): metà delle immagini restano quasi
        # intatte, metà ricevono lievi pieghe — copre l'intero spettro
        # "in buono stato" senza inventare un confine artificiale.
        if rng.random() < 0.5:
            img = apply_wrinkles(base, 0.1, rng)
            return img, None, 0.0
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
# 4 · Build
# ============================================================================


def _assign_split(rng: random.Random) -> str:
    r = rng.random()
    if r < 0.7:
        return "train"
    if r < 0.85:
        return "val"
    return "test"


def build(per_class: int, seed: int, *, use_coco: bool = True,
          coco_dir: Path | None = None) -> None:
    rng = random.Random(seed)

    coco = _load_coco_index(coco_dir or COCO_DIR_DEFAULT) if use_coco else None
    source_images = [] if coco else _load_source_images()
    use_source = len(source_images) > 0

    if coco:
        rng.shuffle(coco["clean"])
        rng.shuffle(coco["defect"])
        print(f"==> Sorgente: dataset COCO reale "
              f"({len(coco['clean'])} pulite, {len(coco['defect'])} con difetto vero)")
        if per_class > len(coco["defect"]):
            print(f"    ⚠️ per-class {per_class} > {len(coco['defect'])} difetti reali: "
                  "alcune immagini danneggiate saranno riusate")
    else:
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
    clean_i = 0
    defect_i = 0
    for cond in CONDITIONS:
        for _ in range(per_class):
            # 1+2. immagine base + degradazione (dipende dalla sorgente)
            category = "sconosciuto"
            color: str | None = None  # None → calcolato dopo il salvataggio
            if coco:
                if cond == "danneggiato":
                    # Difetto REALE: nessuna sintesi, etichetta dal COCO.
                    path, defect_label = coco["defect"][defect_i % len(coco["defect"])]
                    defect_i += 1
                    img = _load_real_image(path)
                    defect, severity = defect_label, 1.0
                else:
                    # Foto pulita reale; usurato ottenuto con degradazione sintetica.
                    path = coco["clean"][clean_i % len(coco["clean"])]
                    clean_i += 1
                    img, defect, severity = make_condition(_load_real_image(path), cond, rng)
            elif use_source:
                base = source_images[rng.randrange(len(source_images))].copy()
                img, defect, severity = make_condition(base, cond, rng)
            else:
                category = rng.choice(SHAPE_CATEGORIES)
                color = rng.choice(list(NAMED_COLORS.keys()))
                base = _draw_garment(category, NAMED_COLORS[color])
                img, defect, severity = make_condition(base, cond, rng)

            # 3. salva (+ colore dominante per le foto reali)
            filename = f"{cond}_{idx:04d}.png"
            out_path = images_root / cond / filename
            img.save(out_path)
            if color is None:
                try:
                    color = dominant_color_name(out_path)
                except Exception:
                    color = "sconosciuto"
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
    if coco:
        n_real = sum(1 for s in samples if s.condition == "danneggiato")
        print(f"    NB: i {n_real} 'danneggiato' sono foto con DIFETTI REALI (COCO);")
        print("        buono da foto reali pulite; usurato = pulite + sintesi.")
    elif not use_source:
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
    parser.add_argument("--coco-dir", type=str, default=None,
                        help=f"cartella dataset COCO difetti (default: {COCO_DIR_DEFAULT.name})")
    parser.add_argument("--no-coco", action="store_true",
                        help="ignora il dataset COCO anche se presente")
    args = parser.parse_args()

    if args.source_dir:
        SOURCE_DIR = Path(args.source_dir).resolve()  # noqa: F811

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build(
        per_class=args.per_class,
        seed=args.seed,
        use_coco=not args.no_coco,
        coco_dir=Path(args.coco_dir).resolve() if args.coco_dir else None,
    )
