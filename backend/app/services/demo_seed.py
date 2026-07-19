"""Seed versionato del guardaroba dimostrativo.

Il database SQLite e ``data/items`` restano dati locali e non vanno committati.
Questo modulo ricostruisce invece lo stesso guardaroba a partire dal manifest
e dalle immagini in ``backend/demo_assets``. Il seed automatico è idempotente:
si attiva soltanto quando la tabella ``items`` è vuota.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import ITEMS_DIR
from app.db import SessionLocal
from app.models import Item, ItemAction, WearEvent
from app.services.circular import RETIRING_ACTIONS, estimate_co2_saved

log = logging.getLogger(__name__)

DEMO_ASSETS_DIR = Path(__file__).resolve().parents[2] / "demo_assets"
DEMO_MANIFEST = DEMO_ASSETS_DIR / "wardrobe.json"
DEMO_IMAGES_DIR = DEMO_ASSETS_DIR / "items"


def _load_manifest() -> dict[str, Any]:
    manifest = json.loads(DEMO_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("version") != 1:
        raise ValueError("Versione del manifest demo non supportata")
    if not isinstance(manifest.get("items"), list) or not manifest["items"]:
        raise ValueError("Il manifest demo non contiene capi")
    return manifest


def _source_image(filename: str) -> Path:
    root = DEMO_IMAGES_DIR.resolve()
    source = (DEMO_IMAGES_DIR / filename).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise FileNotFoundError(f"Asset demo non valido o mancante: {filename}")
    return source


def _destination_name(slug: str, source: Path) -> str:
    safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in {"-", "_"})
    if not safe_slug or safe_slug != slug:
        raise ValueError(f"Slug demo non valido: {slug!r}")
    return f"demo-{safe_slug}{source.suffix.lower()}"


def populate_demo_wardrobe(
    db: Session,
    *,
    items_dir: Path = ITEMS_DIR,
    skip_if_nonempty: bool = True,
) -> list[Item]:
    """Crea capi, utilizzi e azioni dal manifest e restituisce i capi creati."""
    existing = db.scalar(select(func.count(Item.id))) or 0
    if existing:
        if skip_if_nonempty:
            return []
        raise ValueError("Il guardaroba non è vuoto")

    manifest = _load_manifest()
    specs: list[dict[str, Any]] = manifest["items"]
    prepared: list[tuple[dict[str, Any], Path, str]] = []
    seen_slugs: set[str] = set()
    for spec in specs:
        slug = str(spec["slug"])
        if slug in seen_slugs:
            raise ValueError(f"Slug demo duplicato: {slug}")
        seen_slugs.add(slug)
        source = _source_image(str(spec["image"]))
        prepared.append((spec, source, _destination_name(slug, source)))

    items_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    created: list[Item] = []
    by_slug: dict[str, Item] = {}
    today = date.today()

    try:
        for spec_index, (spec, source, destination_name) in enumerate(prepared):
            destination = items_dir / destination_name
            shutil.copy2(source, destination)
            copied.append(destination)

            item = Item(
                name=str(spec["name"]),
                category=str(spec["category"]),
                color=str(spec["color"]),
                image_path=destination_name,
                price=float(spec["price"]),
                purchase_date=today - timedelta(days=int(spec["owned_days"])),
                description=str(spec.get("description") or "") or None,
                condition=str(spec["condition"]),
            )
            db.add(item)
            db.flush()
            created.append(item)
            by_slug[str(spec["slug"])] = item

            wear_count = int(spec.get("wear_count", 0))
            wear_window = max(1, int(spec.get("wear_window_days", 90)))
            for wear_index in range(wear_count):
                days_ago = 1 + ((wear_index * 7 + spec_index * 3) % wear_window)
                db.add(
                    WearEvent(
                        item_id=item.id,
                        worn_on=today - timedelta(days=days_ago),
                        occasion="demo",
                    )
                )

        for action_spec in manifest.get("actions", []):
            item = by_slug[str(action_spec["item_slug"])]
            action_type = str(action_spec["action_type"])
            db.add(
                ItemAction(
                    item_id=item.id,
                    action_type=action_type,
                    notes=str(action_spec.get("notes") or "") or None,
                    co2_saved_kg=estimate_co2_saved(item.category, action_type),
                )
            )
            if action_type in RETIRING_ACTIONS:
                item.retired_at = datetime.now(timezone.utc)

        db.commit()
    except Exception:
        db.rollback()
        for path in copied:
            path.unlink(missing_ok=True)
        raise

    return created


def seed_demo_if_empty() -> int:
    """Applica il seed sul DB configurato; gli errori non bloccano l'avvio."""
    with SessionLocal() as db:
        try:
            created = populate_demo_wardrobe(db)
        except Exception:
            log.exception("Impossibile inizializzare il guardaroba demo")
            return 0
    if created:
        log.info("Guardaroba demo inizializzato con %s capi", len(created))
    return len(created)


def clear_wardrobe(db: Session, *, items_dir: Path = ITEMS_DIR) -> int:
    """Elimina i capi e le relative immagini prima di un reset esplicito."""
    items = list(db.scalars(select(Item)))
    image_names = [item.image_path for item in items if item.image_path]
    for item in items:
        db.delete(item)
    db.commit()

    for image_name in image_names:
        if Path(image_name).name == image_name:
            (items_dir / image_name).unlink(missing_ok=True)
    return len(items)
