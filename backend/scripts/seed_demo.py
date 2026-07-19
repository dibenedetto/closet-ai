"""Inizializza il guardaroba dimostrativo versionato.

Uso dalla cartella ``backend``::

    uv run python scripts/seed_demo.py          # crea solo se il DB è vuoto
    uv run python scripts/seed_demo.py --reset  # sostituisce il guardaroba locale

Il backend non deve essere in esecuzione. Il database e ``data/items`` restano
locali; ciò che va su Git è contenuto in ``backend/demo_assets``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Item, WearEvent  # noqa: E402
from app.services.demo_seed import clear_wardrobe, populate_demo_wardrobe  # noqa: E402
from app.services.stats import compute_impact_stats, compute_wardrobe_stats  # noqa: E402


def main(*, reset: bool) -> None:
    init_db()
    with SessionLocal() as db:
        existing = db.scalar(select(func.count(Item.id))) or 0
        if existing and not reset:
            print(
                f"Guardaroba non modificato: contiene già {existing} capi. "
                "Usa --reset per sostituirlo con la demo."
            )
            return

        if reset:
            removed = clear_wardrobe(db)
            print(f"Rimossi {removed} capi dal guardaroba locale.")

        created = populate_demo_wardrobe(db, skip_if_nonempty=False)
        wardrobe = compute_wardrobe_stats(db)
        impact = compute_impact_stats(db)
        total_wears = db.scalar(select(func.count(WearEvent.id))) or 0

    print(f"Guardaroba demo creato: {len(created)} capi e {total_wears} utilizzi.")
    print(f"Capi attivi: {wardrobe['total_items']}")
    print(f"Capi fantasma: {wardrobe['ghost_count']}")
    # Solo ASCII: il comando deve funzionare anche nel cmd.exe con cp1252.
    print(f"CO2eq evitata: {impact['total_co2_saved_kg']} kg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Sostituisce il guardaroba locale esistente con quello dimostrativo",
    )
    args = parser.parse_args()
    main(reset=args.reset)
