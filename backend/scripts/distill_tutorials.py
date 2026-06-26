"""Distilla i tutorial del dataset VLM da un modello vision grande.

Invece dei tutorial *hardcoded* (KB di `repair_tutorials.py`), questo script
fa guardare ogni foto a un **VLM grande** (Claude, GPT-4o, o un VLM locale
via Ollama) e gli chiede di scrivere un tutorial **personalizzato** sul capo
specifico. Le risposte distillate diventano i nuovi target per il
fine-tuning LoRA (Approccio C) — molto più ricchi e vari della KB fissa.

È il pattern standard di *knowledge distillation*: un modello grande
"insegna" a uno piccolo (Qwen2-VL-2B in LoRA) producendo target di qualità.

──────────────────────────────────────────────────────────────────────────
REQUISITI
──────────────────────────────────────────────────────────────────────────
Un VLM raggiungibile, configurato via `CLOSETAI_LLM_MODEL`:
  - cloud:  `claude-...` (ANTHROPIC_API_KEY) o `openai/gpt-4o` (OPENAI_API_KEY)
  - locale: `ollama/llava` o `ollama/qwen2-vl` (Ollama in esecuzione)

──────────────────────────────────────────────────────────────────────────
USO
──────────────────────────────────────────────────────────────────────────
    # Distilla un piccolo campione (default 12 immagini) per provare:
    uv run python scripts/distill_tutorials.py --sample 12

    # Distilla l'intero dataset (occhio ai costi/tempi delle chiamate API):
    uv run python scripts/distill_tutorials.py --all

Output: ``ml/datasets/garment_condition/vlm_dataset_distilled.jsonl``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import llm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = ROOT / "ml" / "datasets" / "garment_condition"
MANIFEST = DATASET_DIR / "manifest.csv"
OUT_JSONL = DATASET_DIR / "vlm_dataset_distilled.jsonl"

_SYSTEM = (
    "Sei un esperto di sartoria e cura dei capi di abbigliamento. Osservi la "
    "foto di un capo e produci una valutazione del suo stato di conservazione "
    "con un eventuale tutorial di recupero **personalizzato** su ciò che vedi: "
    "tipo di capo, colore, posizione e gravità del difetto. Sii concreto e "
    "pratico. Rispondi SOLO in JSON valido."
)

_USER = (
    "Valuta questo capo. Restituisci un JSON con questa struttura esatta:\n"
    '{\n'
    '  "stato": "nuovo|buono|usurato|danneggiato",\n'
    '  "difetto": "<breve descrizione del difetto visibile, o null>",\n'
    '  "tutorial": "<tutorial personalizzato di 2-4 frasi per recuperare il '
    'capo, oppure null se non serve>"\n'
    '}\n'
    "Il tutorial deve riferirsi a CIO' CHE VEDI (colore del capo, dove si "
    "trova il danno, quanto è esteso), non essere generico."
)

_INSTRUCTION_FOR_DATASET = (
    "Osserva la foto del capo di abbigliamento. Valuta il suo stato di "
    "conservazione (nuovo, buono, usurato o danneggiato) e, se serve, "
    "suggerisci un breve tutorial per migliorarlo. Rispondi in JSON."
)


def _read_manifest() -> list[dict]:
    import csv

    if not MANIFEST.is_file():
        print(f"!! Manifest non trovato: {MANIFEST}")
        sys.exit(1)
    with MANIFEST.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _select(rows: list[dict], sample: int | None) -> list[dict]:
    if sample is None:
        return rows
    # campione bilanciato per stato
    from collections import defaultdict

    by_cond: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cond[r["condition"]].append(r)
    per = max(1, sample // len(by_cond))
    out: list[dict] = []
    for cond, items in by_cond.items():
        out.extend(items[:per])
    return out[:sample]


def _parse_json(raw: str) -> dict | None:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def distill(sample: int | None, model: str | None) -> None:
    if not llm.is_llm_configured(model):
        print("!! Nessun VLM configurato.")
        print("   Imposta CLOSETAI_LLM_MODEL + credenziali, p.es.:")
        print("     - Claude:  ANTHROPIC_API_KEY=...  CLOSETAI_LLM_MODEL=claude-haiku-4-5")
        print("     - locale:  CLOSETAI_LLM_MODEL=ollama/llava   (Ollama attivo)")
        sys.exit(1)

    rows = _select(_read_manifest(), sample)
    print(f"==> Distillo {len(rows)} immagini con {model or llm.LLM_MODEL}…")

    written = 0
    failed = 0
    with OUT_JSONL.open("w", encoding="utf-8") as out:
        for i, row in enumerate(rows, 1):
            img_path = DATASET_DIR / row["filename"]
            raw = llm.generate_vision(str(img_path), _USER, system=_SYSTEM, model=model)
            data = _parse_json(raw) if raw else None
            if data is None:
                failed += 1
                print(f"  [{i}/{len(rows)}] {row['filename']}: distillazione fallita")
                continue

            record = {
                "image": row["filename"],
                "messages": [
                    {"role": "user", "content": f"<image>\n{_INSTRUCTION_FOR_DATASET}"},
                    {"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                ],
                "distilled_from": model or llm.LLM_MODEL,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
            print(f"  [{i}/{len(rows)}] {row['condition']:12s} -> {data.get('stato')}")

    print(f"\n==> Distillati {written} esempi ({failed} falliti) in {OUT_JSONL.relative_to(ROOT)}")
    print("    Usa questo file come dataset per train_condition_vlm_lora.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sample", type=int, default=12, help="numero immagini (default 12)")
    group.add_argument("--all", action="store_true", help="distilla l'intero dataset")
    parser.add_argument("--model", default=None, help="override CLOSETAI_LLM_MODEL")
    args = parser.parse_args()

    distill(sample=None if args.all else args.sample, model=args.model)
