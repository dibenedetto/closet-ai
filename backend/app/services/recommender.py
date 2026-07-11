"""Outfit recommender — Fase 4.

Strategia MVP (regole + score):

1. **Ruoli per categoria**: ogni capo del guardaroba ha un "ruolo" derivato
   dalla `category` (top/bottom/dress/shoes/outerwear/accessory).
2. **Filtro meteo**: alcune categorie sono escluse dal pool in base a
   temperatura e pioggia (es. shorts se freddo, cappotto se caldo).
3. **Generazione candidati**: enumeriamo combinazioni
   {top, bottom, [outerwear], [shoes]} o {dress, [outerwear], [shoes]}.
   Capi senza wear events recenti hanno priorità leggera (anti-fantasma).
4. **Score**: media pesata di
   - compatibilità cromatica (`palette_compat_score`)
   - adeguatezza meteo
   - bonus se include capi "fantasma" (per riequilibrare il guardaroba)
5. **Diversità**: ritorniamo i top-N evitando duplicati di item.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from datetime import date as date_type, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Item, OutfitFeedback, WearEvent
from app.services.color_compat import palette_compat_score
from app.services.weather import WeatherInfo

ROLES_BY_CATEGORY: dict[str, str] = {
    "t-shirt": "top",
    "camicia": "top",
    "felpa": "top",
    "maglione": "top",
    "vestito": "dress",
    "giacca": "outerwear",
    "cappotto": "outerwear",
    "jeans": "bottom",
    "pantaloni": "bottom",
    "shorts": "bottom",
    "gonna": "bottom",
    "scarpe": "shoes",
    "cappello": "accessory",
    "sciarpa": "accessory",
}

# Vincoli meteo: categorie ammesse / vietate per fascia di temperatura.
_COLD_FORBIDDEN = {"shorts", "t-shirt"}
_WARM_FORBIDDEN = {"cappotto", "maglione", "sciarpa"}


@dataclass(frozen=True, slots=True)
class OutfitCandidate:
    item_ids: tuple[int, ...]
    score: float
    rationale: str
    color_score: float
    weather_score: float
    ghost_bonus: float


def _role_of(item: Item) -> str | None:
    return ROLES_BY_CATEGORY.get((item.category or "").lower())


def _filter_by_weather(items: list[Item], weather: WeatherInfo) -> list[Item]:
    out: list[Item] = []
    for it in items:
        cat = (it.category or "").lower()
        if weather.is_cold() and cat in _COLD_FORBIDDEN:
            continue
        if weather.is_warm() and cat in _WARM_FORBIDDEN:
            continue
        out.append(it)
    return out


def _weather_adequacy(items: list[Item], weather: WeatherInfo) -> tuple[float, list[str]]:
    """Punteggio in [0,1] su quanto l'outfit è adatto al meteo, + reasons."""
    categories = {(it.category or "").lower() for it in items}
    score = 0.7
    reasons: list[str] = []

    if weather.is_cold():
        if categories & {"cappotto", "maglione", "giacca"}:
            score += 0.2
            reasons.append("strato pesante per il freddo")
        else:
            score -= 0.2
            reasons.append("manca uno strato pesante")
    if weather.is_warm():
        if categories & {"t-shirt", "shorts", "vestito"}:
            score += 0.15
            reasons.append("leggero per il caldo")
    if weather.is_rainy():
        if categories & {"giacca", "cappotto"}:
            score += 0.1
            reasons.append("copertura per la pioggia")
        else:
            score -= 0.15
            reasons.append("manca copertura per la pioggia")

    return max(0.0, min(1.0, score)), reasons


def _recently_worn_ids(db: Session, *, days: int = 7) -> set[int]:
    threshold = date_type.today() - timedelta(days=days)
    rows = db.execute(
        select(WearEvent.item_id)
        .where(WearEvent.worn_on >= threshold)
        .distinct()
    ).scalars().all()
    return set(rows)


def _wear_count_map(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(WearEvent.item_id, func.count(WearEvent.id))
        .group_by(WearEvent.item_id)
    ).all()
    return {int(r[0]): int(r[1]) for r in rows}


def _feedback_affinity_map(db: Session) -> dict[int, float]:
    """Media dei feedback outfit per capo, in [-1, 1].

    È un segnale leggero: personalizza l'ordinamento senza sovrastare meteo e
    compatibilità cromatica. I feedback restano validi anche se un capo viene
    eliminato, quindi ignoriamo semplicemente gli id non presenti nel pool.
    """
    totals: dict[int, tuple[int, int]] = {}
    for feedback in db.execute(select(OutfitFeedback)).scalars():
        for item_id in feedback.item_ids:
            total, count = totals.get(item_id, (0, 0))
            totals[item_id] = (total + feedback.rating, count + 1)
    return {item_id: total / count for item_id, (total, count) in totals.items() if count}


def _ghost_bonus(items: list[Item], wear_counts: dict[int, int]) -> float:
    """Bonus se include capi mai/poco indossati (riequilibrio guardaroba)."""
    unused = [it for it in items if wear_counts.get(it.id, 0) == 0]
    if not unused:
        return 0.0
    # Fino a +0.15 se l'outfit include 2+ capi fantasma
    return min(0.15, 0.08 * len(unused))


def _build_candidates(
    pool: list[Item], wear_counts: dict[int, int], weather: WeatherInfo,
    *, max_candidates: int = 60, rng: random.Random | None = None,
) -> list[list[Item]]:
    """Genera combinazioni concrete a partire dai capi disponibili.

    Per non esplodere combinatoriamente, prendiamo al massimo 4 capi per ruolo
    (privilegiando i meno usati = candidati per ridurre i 'fantasma').
    """
    rng = rng or random.Random()
    by_role: dict[str, list[Item]] = {}
    for it in pool:
        r = _role_of(it)
        if r is None:
            continue
        by_role.setdefault(r, []).append(it)

    def trim(lst: list[Item]) -> list[Item]:
        sorted_ = sorted(lst, key=lambda x: wear_counts.get(x.id, 0))
        return sorted_[:4]

    tops = trim(by_role.get("top", []))
    bottoms = trim(by_role.get("bottom", []))
    dresses = trim(by_role.get("dress", []))
    outerwears = trim(by_role.get("outerwear", []))
    shoes = trim(by_role.get("shoes", []))

    candidates: list[list[Item]] = []

    # Outfit top + bottom + (outerwear)? + (shoes)?
    for top, bottom in itertools.product(tops, bottoms):
        for outer in [None, *outerwears]:
            for sh in [None, *shoes]:
                combo = [x for x in (top, bottom, outer, sh) if x is not None]
                if len(combo) >= 2:
                    candidates.append(combo)

    # Outfit vestito + (outerwear)? + (shoes)?
    for d in dresses:
        for outer in [None, *outerwears]:
            for sh in [None, *shoes]:
                combo = [x for x in (d, outer, sh) if x is not None]
                if combo:
                    candidates.append(combo)

    rng.shuffle(candidates)
    return candidates[:max_candidates]


def _score(
    items: list[Item], weather: WeatherInfo, wear_counts: dict[int, int],
    feedback_affinity: dict[int, float] | None = None,
) -> tuple[float, str, dict[str, float]]:
    colors = [it.color for it in items]
    color_score = palette_compat_score(colors)
    weather_score, weather_reasons = _weather_adequacy(items, weather)
    ghost_bonus = _ghost_bonus(items, wear_counts)

    affinity_values = [
        feedback_affinity[it.id]
        for it in items
        if feedback_affinity and it.id in feedback_affinity
    ]
    preference_bonus = (
        0.04 * (sum(affinity_values) / len(affinity_values))
        if affinity_values
        else 0.0
    )
    score = 0.55 * color_score + 0.35 * weather_score + ghost_bonus + preference_bonus
    score = max(0.0, min(1.0, score))

    palette_str = ", ".join(c for c in colors if c) or "—"
    rationale_parts = [f"colori: {palette_str}"]
    rationale_parts.extend(weather_reasons)
    if ghost_bonus > 0:
        rationale_parts.append("contiene capi mai indossati")
    if preference_bonus > 0.005:
        rationale_parts.append("in linea con le tue preferenze")
    rationale = "; ".join(rationale_parts)

    return score, rationale, {
        "color": color_score,
        "weather": weather_score,
        "ghost": ghost_bonus,
        "preference": preference_bonus,
    }


def suggest_outfits(
    db: Session,
    weather: WeatherInfo,
    *,
    count: int = 3,
    rng: random.Random | None = None,
) -> list[OutfitCandidate]:
    """Genera fino a `count` proposte di outfit dal guardaroba, ordinate per score."""
    pool = list(db.execute(select(Item).where(Item.retired_at.is_(None))).scalars())
    if not pool:
        return []

    eligible = _filter_by_weather(pool, weather)
    if not eligible:
        return []

    wear_counts = _wear_count_map(db)
    feedback_affinity = _feedback_affinity_map(db)
    candidates = _build_candidates(eligible, wear_counts, weather, rng=rng)

    scored: list[OutfitCandidate] = []
    seen_keys: set[tuple[int, ...]] = set()
    for combo in candidates:
        key = tuple(sorted(it.id for it in combo))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        score, rationale, parts = _score(combo, weather, wear_counts, feedback_affinity)
        scored.append(
            OutfitCandidate(
                item_ids=key,
                score=round(score, 3),
                rationale=rationale,
                color_score=round(parts["color"], 3),
                weather_score=round(parts["weather"], 3),
                ghost_bonus=round(parts["ghost"], 3),
            )
        )

    scored.sort(key=lambda o: o.score, reverse=True)

    # Diversità: penalizza outfit che condividono troppi capi con quelli già scelti.
    picked: list[OutfitCandidate] = []
    used_items: set[int] = set()
    for cand in scored:
        overlap = len(set(cand.item_ids) & used_items)
        if picked and overlap >= max(1, len(cand.item_ids) - 1):
            continue
        picked.append(cand)
        used_items.update(cand.item_ids)
        if len(picked) >= count:
            break

    return picked
