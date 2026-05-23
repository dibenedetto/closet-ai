"""Tutorial di riparazione per difetti comuni dei capi.

Strategia MVP: una **knowledge base hardcoded** con tutorial per i difetti
più ricorrenti. È un sostituto onesto e offline-friendly del piping "via
LLM" del PLAN: la generazione LLM è cara, lenta e richiede una API key che
non vogliamo come dipendenza obbligatoria.

L'interfaccia espone `get_tutorial(defect, category=None) -> RepairTutorial`.
Quando `CLOSETAI_ANTHROPIC_API_KEY` è settata, in futuro potremo arricchire
il tutorial con un LLM call (ADR aperto in `docs/architecture.md`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services import llm

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Difetti supportati. Servono al frontend per popolare la select.
DEFECTS: tuple[str, ...] = (
    "strappo",
    "macchia",
    "cucitura",
    "bottone",
    "elastico",
    "zip",
    "buco",
    "scolorimento",
)


@dataclass(frozen=True, slots=True)
class RepairTutorial:
    defect: str
    category: str | None
    title: str
    difficulty: str  # "facile" | "media" | "alta"
    time_minutes: int
    materials: list[str]
    steps: list[str]
    source: str  # "hardcoded" | "llm"


_TUTORIALS: dict[str, RepairTutorial] = {
    "strappo": RepairTutorial(
        defect="strappo",
        category=None,
        title="Riparare uno strappo con cucitura nascosta",
        difficulty="facile",
        time_minutes=20,
        materials=["ago", "filo dello stesso colore", "ditale", "forbici"],
        steps=[
            "Stira la zona dello strappo per appiattire le fibre.",
            "Allinea i bordi dello strappo dal rovescio del capo.",
            "Cuci a punto nascosto piccolo (punto smock o overcasting).",
            "Ogni 0,5 cm fai un nodo per fissare il filo.",
            "Termina con un nodo doppio e taglia il filo.",
        ],
        source="hardcoded",
    ),
    "macchia": RepairTutorial(
        defect="macchia",
        category=None,
        title="Rimuovere una macchia ostinata",
        difficulty="facile",
        time_minutes=15,
        materials=["sapone di Marsiglia", "bicarbonato", "acqua tiepida"],
        steps=[
            "Identifica la natura della macchia (organica / grassa / vino).",
            "Sciacqua con acqua fredda dal **rovescio** per non spingere la macchia in profondità.",
            "Strofina sapone di Marsiglia direttamente sulla macchia.",
            "Per macchie grasse: applica bicarbonato in pasta e lascia agire 30 min.",
            "Lava normalmente. Non asciugare prima di verificare: il calore fissa.",
        ],
        source="hardcoded",
    ),
    "cucitura": RepairTutorial(
        defect="cucitura",
        category=None,
        title="Ricucire una cucitura sciolta",
        difficulty="facile",
        time_minutes=15,
        materials=["ago", "filo", "spilli", "forbici"],
        steps=[
            "Rivolta il capo a rovescio.",
            "Fissa i due bordi con spilli, allineando i punti di partenza/arrivo della cucitura originale.",
            "Cuci a punto indietro per fissare l'inizio.",
            "Continua con punto unito (~3 mm), poi termina con altro punto indietro.",
            "Taglia il filo lasciando 1 cm.",
        ],
        source="hardcoded",
    ),
    "bottone": RepairTutorial(
        defect="bottone",
        category=None,
        title="Riattaccare un bottone caduto",
        difficulty="facile",
        time_minutes=10,
        materials=["ago", "filo doppio", "bottone (se sostituito)"],
        steps=[
            "Posiziona il bottone allineato all'asola del corrispondente.",
            "Inserisci l'ago dal rovescio e fai 5-6 passaggi nei fori del bottone.",
            "Prima di stringere, lascia un piccolo spazio (uno stuzzicadenti) per il \"gambo\".",
            "Avvolgi il filo intorno al gambo 4-5 volte per dargli spessore.",
            "Fissa con nodo doppio dal rovescio.",
        ],
        source="hardcoded",
    ),
    "elastico": RepairTutorial(
        defect="elastico",
        category=None,
        title="Sostituire un elastico interno",
        difficulty="media",
        time_minutes=30,
        materials=["elastico nuovo della larghezza giusta", "spilla da balia", "ago", "filo"],
        steps=[
            "Apri la cucitura del tunnel dell'elastico per circa 3 cm.",
            "Estrai l'elastico vecchio tirandolo da un'estremità.",
            "Aggancia il nuovo elastico a una spilla da balia e infila nel tunnel.",
            "Sovrapponi i due capi dell'elastico per 1-2 cm e fissali con cucitura a zigzag.",
            "Richiudi il tunnel con punto nascosto.",
        ],
        source="hardcoded",
    ),
    "zip": RepairTutorial(
        defect="zip",
        category=None,
        title="Sbloccare o sostituire una zip",
        difficulty="media",
        time_minutes=25,
        materials=["matita HB (grafite) o sapone", "pinze", "eventualmente zip di ricambio"],
        steps=[
            "Per zip bloccata: strofina grafite di matita o sapone secco sui denti.",
            "Apri e chiudi lentamente più volte, senza forzare.",
            "Se il cursore è deformato: stringi delicatamente con le pinze sui lati.",
            "Se la zip è rotta in più punti: rimuovi con uno scucitore e cuci una zip nuova della stessa lunghezza.",
        ],
        source="hardcoded",
    ),
    "buco": RepairTutorial(
        defect="buco",
        category=None,
        title="Rammendare un piccolo buco",
        difficulty="media",
        time_minutes=25,
        materials=["ago da rammendo", "filo o lana sottile", "telaietto da ricamo (opz.)"],
        steps=[
            "Posiziona il capo su un telaietto per tenere il tessuto teso.",
            "Crea dei \"fili di ordito\" sopra il buco: cuci avanti e indietro paralleli.",
            "Tesi i fili di ordito, inserisci la \"trama\" passando sopra-sotto-sopra alternato.",
            "Stringi delicatamente la maglia e fissa ai bordi del buco.",
            "Chiudi con nodo dal rovescio.",
        ],
        source="hardcoded",
    ),
    "scolorimento": RepairTutorial(
        defect="scolorimento",
        category=None,
        title="Ravvivare un capo scolorito",
        difficulty="facile",
        time_minutes=60,
        materials=["tintura tessile dello stesso colore", "sale grosso", "secchio"],
        steps=[
            "Verifica la composizione del tessuto sull'etichetta: i sintetici tingono peggio.",
            "Prepara la tintura nel secchio secondo le istruzioni; aggiungi sale per fissaggio.",
            "Immergi il capo bagnato muovendolo costantemente per 30-40 min.",
            "Risciacqua finché l'acqua non esce limpida.",
            "Stira a media temperatura per fissare il colore.",
        ],
        source="hardcoded",
    ),
}

_GENERIC_FALLBACK = RepairTutorial(
    defect="generico",
    category=None,
    title="Suggerimenti generici di riparazione",
    difficulty="facile",
    time_minutes=15,
    materials=["ago", "filo", "forbici", "spilli"],
    steps=[
        "Identifica con precisione il difetto (strappo, macchia, cucitura, ecc.).",
        "Cerca un tutorial specifico nella nostra base — i difetti comuni sono coperti.",
        "Se il danno è strutturale (es. tessuto disintegrato), considera il riciclo tessile.",
        "Per dubbi: porta il capo a una sarta di quartiere — molti pezzi sono salvabili con € 5-15.",
    ],
    source="hardcoded",
)


def get_tutorial(defect: str | None, *, category: str | None = None) -> RepairTutorial:
    """Restituisce un tutorial appropriato. Se `defect` è ignoto, fallback generico."""
    if not defect:
        return _GENERIC_FALLBACK
    tut = _TUTORIALS.get(defect.lower().strip())
    if tut is None:
        return _GENERIC_FALLBACK
    if category:
        # Personalizza il campo `category` per il frontend, ma non altera i passi.
        return RepairTutorial(
            defect=tut.defect,
            category=category,
            title=tut.title,
            difficulty=tut.difficulty,
            time_minutes=tut.time_minutes,
            materials=list(tut.materials),
            steps=list(tut.steps),
            source=tut.source,
        )
    return tut


def llm_enrichment_available() -> bool:
    """True se l'LLM configurato è raggiungibile (Anthropic, OpenAI, Ollama,…).

    Anche `CLOSETAI_ANTHROPIC_API_KEY` (legacy) attiva il flag per non rompere
    chi aveva già configurato il prototipo prima dell'integrazione litellm.
    """
    return llm.is_llm_configured() or bool(os.environ.get("CLOSETAI_ANTHROPIC_API_KEY"))


_LLM_SYSTEM_PROMPT = (
    "Sei un sarto esperto che parla italiano. Quando ti viene chiesto un "
    "tutorial di riparazione di un capo, rispondi con istruzioni pratiche, "
    "chiare e brevi. Usa materiali facili da trovare in casa o in merceria. "
    "Sii prudente: se il danno è grave consiglia un sarto professionale."
)

_LLM_SCHEMA = (
    '{"title": str, "difficulty": "facile|media|alta", '
    '"time_minutes": int, "materials": [str, ...], "steps": [str, ...]}'
)


def enrich_with_llm(
    defect: str,
    *,
    category: str | None = None,
    color: str | None = None,
    condition: str | None = None,
    db: "Session | None" = None,
) -> RepairTutorial | None:
    """Genera un tutorial personalizzato via LLM. Ritorna `None` se l'LLM non
    è raggiungibile (in tal caso il chiamante usa la KB hardcoded)."""
    if not llm_enrichment_available():
        return None

    details = []
    if category:
        details.append(f"categoria: {category}")
    if color:
        details.append(f"colore: {color}")
    if condition:
        details.append(f"condizione attuale: {condition}")
    detail_text = "; ".join(details) if details else "informazioni minime"

    user = (
        f"Difetto da riparare: **{defect}**. Caratteristiche del capo: {detail_text}.\n"
        "Genera un tutorial di riparazione personalizzato. Concentrati sul difetto "
        "specifico e suggerisci materiali ragionevoli per il colore e tipo di tessuto."
    )

    payload = llm.generate_json(
        user, schema_hint=_LLM_SCHEMA, system=_LLM_SYSTEM_PROMPT, db=db
    )
    if payload is None:
        return None

    try:
        return RepairTutorial(
            defect=defect,
            category=category,
            title=str(payload.get("title") or f"Riparazione: {defect}"),
            difficulty=str(payload.get("difficulty") or "media"),
            time_minutes=int(payload.get("time_minutes") or 20),
            materials=[str(m) for m in (payload.get("materials") or []) if m],
            steps=[str(s) for s in (payload.get("steps") or []) if s],
            source="llm",
        )
    except (TypeError, ValueError):
        return None
