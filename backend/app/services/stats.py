"""Servizi per il calcolo delle statistiche di wear log."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Item, ItemAction, WearEvent
from app.services.circular import RETIRING_ACTIONS

DEFAULT_GHOST_AFTER_DAYS = 30


def _today() -> date:
    return date.today()


def compute_item_stats(
    db: Session, item: Item, *, ghost_after_days: int = DEFAULT_GHOST_AFTER_DAYS
) -> dict:
    """Calcola le statistiche di un singolo capo."""
    row = db.execute(
        select(
            func.count(WearEvent.id),
            func.max(WearEvent.worn_on),
        ).where(WearEvent.item_id == item.id)
    ).one()
    wear_count: int = row[0] or 0
    last_worn: date | None = row[1]

    today = _today()
    days_since_last_worn = (today - last_worn).days if last_worn is not None else None

    cost_per_wear: float | None = None
    if item.price is not None and wear_count > 0:
        cost_per_wear = round(item.price / wear_count, 2)

    is_ghost = wear_count == 0 and _ghost_eligible(item, today, ghost_after_days)

    return {
        "item_id": item.id,
        "wear_count": wear_count,
        "last_worn": last_worn,
        "days_since_last_worn": days_since_last_worn,
        "cost_per_wear": cost_per_wear,
        "is_ghost": is_ghost,
        "ghost_after_days": ghost_after_days,
    }


def _ghost_eligible(item: Item, today: date, ghost_after_days: int) -> bool:
    """Un capo è 'eligible' per lo stato fantasma se è stato posseduto da
    almeno `ghost_after_days`. Per la determinazione preferiamo
    `purchase_date`; fallback su `created_at` (data di registrazione)."""
    reference: date | None = item.purchase_date
    if reference is None:
        reference = item.created_at.date() if item.created_at else None
    if reference is None:
        return False
    return (today - reference).days >= ghost_after_days


def compute_wardrobe_stats(
    db: Session, *, ghost_after_days: int = DEFAULT_GHOST_AFTER_DAYS, top_n: int = 5
) -> dict:
    """Calcola le statistiche aggregate sul guardaroba (esclude capi ritirati)."""
    total_items: int = db.execute(
        select(func.count(Item.id)).where(Item.retired_at.is_(None))
    ).scalar_one() or 0
    total_wears: int = db.execute(
        select(func.count(WearEvent.id))
        .join(Item, Item.id == WearEvent.item_id)
        .where(Item.retired_at.is_(None))
    ).scalar_one() or 0
    avg_wears_per_item = (total_wears / total_items) if total_items > 0 else 0.0

    # Investimento totale (somma price escludendo None)
    total_investment: float | None = db.execute(
        select(func.coalesce(func.sum(Item.price), 0.0))
        .where(Item.retired_at.is_(None))
    ).scalar_one()
    if total_investment == 0.0:
        total_investment = None

    # Cost-per-wear medio: media dei rapporti price/wears per i capi con
    # price e almeno un wear.
    cpw_subq = (
        select(
            Item.id.label("item_id"),
            Item.price.label("price"),
            func.count(WearEvent.id).label("wears"),
        )
        .join(WearEvent, WearEvent.item_id == Item.id)
        .where(Item.price.is_not(None), Item.retired_at.is_(None))
        .group_by(Item.id, Item.price)
    ).subquery()
    cpw_rows = db.execute(select(cpw_subq.c.price, cpw_subq.c.wears)).all()
    cpw_values = [
        float(price) / int(wears) for price, wears in cpw_rows if wears and wears > 0
    ]
    avg_cost_per_wear = round(sum(cpw_values) / len(cpw_values), 2) if cpw_values else None

    # Top capi più indossati
    top_rows = db.execute(
        select(Item.id, Item.name, func.count(WearEvent.id).label("wears"))
        .join(WearEvent, WearEvent.item_id == Item.id)
        .where(Item.retired_at.is_(None))
        .group_by(Item.id, Item.name)
        .order_by(func.count(WearEvent.id).desc())
        .limit(top_n)
    ).all()
    top_worn = [
        {"item_id": r[0], "name": r[1], "wear_count": r[2]} for r in top_rows
    ]

    # Capi fantasma: wear_count = 0 e posseduti da almeno ghost_after_days.
    ghost_count = _count_ghosts(db, ghost_after_days)

    return {
        "total_items": total_items,
        "total_wears": total_wears,
        "avg_wears_per_item": round(avg_wears_per_item, 2),
        "ghost_count": ghost_count,
        "ghost_after_days": ghost_after_days,
        "total_investment": (
            round(float(total_investment), 2) if total_investment is not None else None
        ),
        "avg_cost_per_wear": avg_cost_per_wear,
        "top_worn": top_worn,
    }


def list_ghost_items(
    db: Session, *, ghost_after_days: int = DEFAULT_GHOST_AFTER_DAYS
) -> list[dict]:
    """Lista i capi mai indossati e posseduti da almeno X giorni."""
    today = _today()
    threshold = today - timedelta(days=ghost_after_days)

    # Capi senza wear events, non ritirati (LEFT OUTER JOIN + filter)
    rows = (
        db.execute(
            select(Item)
            .outerjoin(WearEvent, WearEvent.item_id == Item.id)
            .where(WearEvent.id.is_(None), Item.retired_at.is_(None))
            .order_by(Item.created_at.desc())
        )
        .scalars()
        .all()
    )

    out: list[dict] = []
    for item in rows:
        ref = item.purchase_date or (item.created_at.date() if item.created_at else None)
        if ref is None or ref > threshold:
            continue
        out.append(
            {
                "item_id": item.id,
                "name": item.name,
                "category": item.category,
                "purchase_date": item.purchase_date,
                "days_owned": (today - ref).days,
                "price": item.price,
            }
        )
    return out


def _count_ghosts(db: Session, ghost_after_days: int) -> int:
    today = _today()
    threshold = today - timedelta(days=ghost_after_days)
    rows = (
        db.execute(
            select(Item.purchase_date, Item.created_at)
            .outerjoin(WearEvent, WearEvent.item_id == Item.id)
            .where(WearEvent.id.is_(None), Item.retired_at.is_(None))
        )
        .all()
    )
    count = 0
    for purchase_date, created_at in rows:
        ref = purchase_date or (created_at.date() if created_at else None)
        if ref is not None and ref <= threshold:
            count += 1
    return count


def compute_impact_stats(db: Session) -> dict:
    """Statistiche aggregate del modulo circolare (Fase 5)."""
    actions = list(db.execute(select(ItemAction)).scalars())
    total_actions = len(actions)
    total_co2 = round(sum(a.co2_saved_kg for a in actions), 2)

    actions_by_type: dict[str, int] = {}
    co2_by_type: dict[str, float] = {}
    for a in actions:
        actions_by_type[a.action_type] = actions_by_type.get(a.action_type, 0) + 1
        co2_by_type[a.action_type] = round(
            co2_by_type.get(a.action_type, 0.0) + a.co2_saved_kg, 2
        )

    retired_count: int = db.execute(
        select(func.count(Item.id)).where(Item.retired_at.is_not(None))
    ).scalar_one() or 0

    # Capi che hanno almeno un'azione di tipo "riparazione".
    repaired_item_ids = {
        a.item_id for a in actions if a.action_type == "riparazione"
    }
    # `RETIRING_ACTIONS` non viene usato qui ma esportato per chiarezza in docs.
    _ = RETIRING_ACTIONS

    return {
        "total_actions": total_actions,
        "total_co2_saved_kg": total_co2,
        "actions_by_type": actions_by_type,
        "co2_by_type": co2_by_type,
        "retired_items_count": retired_count,
        "repaired_items_count": len(repaired_item_ids),
    }
