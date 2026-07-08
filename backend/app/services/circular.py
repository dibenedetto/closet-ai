"""Servizi per il modulo circolare: suggerimenti azioni + stima CO₂.

I valori di CO₂ per produzione sono **medie indicative** derivate da letteratura
Ellen MacArthur Foundation / Quantis 2018. Da rivedere in Fase 6 con LCA per
materiale (cotone, poliestere, lana, ecc.) — attualmente è basato solo sulla
categoria.

Le percentuali di "evitamento" sono basate sull'assunto:

- **riparazione**: prolungare la vita del capo di ~70% evita produzione equivalente
- **swap / vendita / donazione**: 100% (qualcun altro non comprerà un nuovo capo)
- **riciclo**: 30% (recupero parziale del materiale, non sostituzione completa)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import ACTION_TYPES

# kg CO₂eq per produzione (medie indicative)
CO2_PROD_KG: dict[str, float] = {
    "t-shirt": 7.0,
    "camicia": 10.0,
    "felpa": 12.0,
    "maglione": 14.0,
    "giacca": 25.0,
    "cappotto": 40.0,
    "jeans": 32.0,
    "pantaloni": 20.0,
    "shorts": 15.0,
    "gonna": 15.0,
    "vestito": 25.0,
    "scarpe": 14.0,
    "cappello": 5.0,
    "sciarpa": 5.0,
}
CO2_DEFAULT_KG: float = 15.0

# % di CO₂ "evitata" per azione vs produzione nuovo equivalente.
ACTION_SAVINGS_PCT: dict[str, float] = {
    "riparazione": 0.70,
    "swap": 1.00,
    "vendita": 1.00,
    "donazione": 1.00,
    "riciclo": 0.30,
}

# Azioni che "ritirano" il capo dal guardaroba (non più disponibile per outfit/wear).
RETIRING_ACTIONS: frozenset[str] = frozenset({"swap", "vendita", "donazione", "riciclo"})


@dataclass(frozen=True, slots=True)
class ActionSuggestion:
    action_type: str
    co2_saved_kg: float
    rationale: str
    priority: int  # 1 = primaria, 2 = secondaria, 3 = ultima risorsa


def base_co2_for_category(category: str | None) -> float:
    if not category:
        return CO2_DEFAULT_KG
    return CO2_PROD_KG.get(category.lower(), CO2_DEFAULT_KG)


def estimate_co2_saved(category: str | None, action_type: str) -> float:
    """Stima dei kg CO₂eq evitati eseguendo `action_type` sul capo."""
    base = base_co2_for_category(category)
    pct = ACTION_SAVINGS_PCT.get(action_type, 0.5)
    return round(base * pct, 2)


def suggest_actions(
    category: str | None, condition: str | None
) -> list[ActionSuggestion]:
    """Restituisce la lista di azioni ordinate per priorità decrescente.

    La priorità riflette la gerarchia circolare (riparazione > riuso >
    riciclo). Lo stato del capo modula quali azioni sono *ragionevoli*:
    un capo danneggiato non si vende, ma si ripara o ricicla.
    """
    cond = (condition or "").lower()
    out: list[ActionSuggestion] = []

    def add(action: str, rationale: str, priority: int) -> None:
        out.append(
            ActionSuggestion(
                action_type=action,
                co2_saved_kg=estimate_co2_saved(category, action),
                rationale=rationale,
                priority=priority,
            )
        )

    if cond == "buono":
        # (include gli ex "nuovo": la classe è stata fusa)
        add("vendita", "in buono stato: ottimo valore di rivendita", 1)
        add("swap", "scambialo con un capo di tuo gradimento", 1)
        add("donazione", "donalo se non lo indossi", 2)
    elif cond == "usurato":
        add("riparazione", "alcune riparazioni mirate possono prolungarne la vita", 1)
        add("donazione", "può essere ancora utile a qualcun altro", 2)
        add("riciclo", "se non riparabile, conferiscilo a un centro tessile", 3)
    elif cond == "danneggiato":
        add("riparazione", "rammendo / patching può salvare il capo", 1)
        add("riciclo", "se irreparabile, vai al riciclo tessile (no rifiuti misti)", 2)
    else:
        # Diagnosi mancante: proponiamo le opzioni più comuni in ordine circolare.
        add("riparazione", "valuta una piccola riparazione preventiva", 2)
        add("swap", "scambia con un capo che indosseresti di più", 1)
        add("donazione", "donalo se non lo indossi", 2)
        add("vendita", "vendi second-hand", 2)
        add("riciclo", "ultimo step quando le altre opzioni non sono possibili", 3)

    out.sort(key=lambda a: a.priority)
    return out


def is_retiring(action_type: str) -> bool:
    return action_type in RETIRING_ACTIONS


def validate_action_type(action_type: str) -> None:
    if action_type not in ACTION_TYPES:
        raise ValueError(
            f"action_type non valido: {action_type!r}. Ammessi: {ACTION_TYPES}"
        )
