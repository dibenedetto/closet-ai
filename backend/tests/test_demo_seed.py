from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Item, ItemAction, WearEvent
from app.services.demo_seed import populate_demo_wardrobe
from app.services.stats import compute_impact_stats, compute_wardrobe_stats


def test_demo_seed_populates_a_complete_idempotent_wardrobe(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'demo.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    items_dir = tmp_path / "items"

    with session_factory() as db:
        created = populate_demo_wardrobe(db, items_dir=items_dir)

        assert len(created) == 12
        assert db.scalar(select(func.count(Item.id))) == 12
        assert db.scalar(select(func.count(WearEvent.id))) == 147
        assert db.scalar(select(func.count(ItemAction.id))) == 2
        assert db.scalar(
            select(func.count(Item.id)).where(Item.retired_at.is_not(None))
        ) == 1
        assert db.scalar(
            select(func.count(Item.id)).where(Item.condition == "danneggiato")
        ) == 1
        assert len(list(items_dir.iterdir())) == 12

        wardrobe = compute_wardrobe_stats(db)
        impact = compute_impact_stats(db)
        assert wardrobe["total_items"] == 11
        assert wardrobe["ghost_count"] == 2
        assert impact["repaired_items_count"] == 1
        assert impact["retired_items_count"] == 1
        assert impact["total_co2_saved_kg"] == 34.8

        # Una seconda inizializzazione non duplica il guardaroba.
        assert populate_demo_wardrobe(db, items_dir=items_dir) == []
        assert db.scalar(select(func.count(Item.id))) == 12

    engine.dispose()
