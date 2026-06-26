"""Pipeline automatica end-to-end per il VLM di diagnosi stato (Approccio C).

Esegue in sequenza, con un solo comando, tutti gli step necessari ad
addestrare l'adapter LoRA e renderlo attivo nel backend:

    1. fetch    — scarica immagini di capi reali (FashionMNIST) → source/
    2. build    — genera il dataset etichettato (degradazione sintetica)
    3. distill  — (opzionale) tutorial personalizzati da un VLM grande
    4. train    — fine-tuning LoRA del VLM su quel dataset
    5. verify   — controlla che l'adapter sia stato salvato e spiega come attivarlo

Ogni step viene **saltato se il suo output esiste già** (idempotente); usa
``--force`` per rifare tutto da zero.

──────────────────────────────────────────────────────────────────────────
USO
──────────────────────────────────────────────────────────────────────────
    # Validazione completa SENZA addestrare (veloce, nessun download pesante):
    uv run python scripts/train_condition_vlm_pipeline.py --dry-run

    # Pipeline completa (richiede GPU; ~4GB di download al primo run):
    uv run python scripts/train_condition_vlm_pipeline.py

    # Con tutorial distillati (richiede un VLM configurato) + QLoRA 4-bit:
    uv run python scripts/train_condition_vlm_pipeline.py --distill --load-4bit

    # Riprendere saltando step già fatti:
    uv run python scripts/train_condition_vlm_pipeline.py --skip-fetch --skip-build

Vedi ADR-010 in docs/architecture.md.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCRIPTS = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS.parent
ROOT = BACKEND_DIR.parent
DATASET_DIR = ROOT / "ml" / "datasets" / "garment_condition"
SOURCE_DIR = ROOT / "ml" / "datasets" / "source"
MANIFEST = DATASET_DIR / "manifest.csv"
DISTILLED = DATASET_DIR / "vlm_dataset_distilled.jsonl"
ADAPTER_DIR = ROOT / "ml" / "weights" / "condition_vlm_lora"


# ============================================================================
# Helpers
# ============================================================================


def _run(step: str, cmd: list[str]) -> None:
    """Esegue uno step come subprocess, fermandosi su errore."""
    print(f"\n{'=' * 70}\n>>> STEP: {step}\n{'=' * 70}")
    print("    " + " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"  # evita crash cp1252 su Windows
    result = subprocess.run(cmd, cwd=str(BACKEND_DIR), env=env)
    if result.returncode != 0:
        print(f"\n!! Step '{step}' fallito (exit {result.returncode}). Pipeline interrotta.")
        sys.exit(result.returncode)


def _py(script: str, *args: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / script), *args]


def _has_source_images() -> bool:
    if not SOURCE_DIR.is_dir():
        return False
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    return any(p.suffix.lower() in exts for p in SOURCE_DIR.iterdir())


def _llm_configured() -> bool:
    try:
        from app.services import llm

        return llm.is_llm_configured()
    except Exception:
        return False


def _gpu_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


# ============================================================================
# Pipeline
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fetch-count", type=int, default=240,
                        help="immagini reali da scaricare (0 = salta fetch)")
    parser.add_argument("--per-class", type=int, default=150,
                        help="immagini per stato nel dataset")
    parser.add_argument("--distill", action="store_true",
                        help="distilla i tutorial da un VLM (richiede LLM configurato)")
    parser.add_argument("--distill-all", action="store_true",
                        help="distilla l'INTERO dataset (default: campione)")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--load-4bit", action="store_true",
                        help="QLoRA 4-bit (meno VRAM, richiede bitsandbytes)")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="rifà gli step anche se l'output esiste già")
    parser.add_argument("--dry-run", action="store_true",
                        help="esegue fetch/build se servono, poi valida il training "
                             "senza scaricare il modello né addestrare")
    args = parser.parse_args()

    print("=== Pipeline VLM diagnosi stato (Approccio C) ===")
    print(f"    GPU CUDA: {'sì' if _gpu_available() else 'NO'}")
    print(f"    LLM per distillazione: {'configurato' if _llm_configured() else 'non configurato'}")
    if not args.dry_run and not _gpu_available():
        print("\n  ⚠️  Nessuna GPU rilevata: il training sarà improponibilmente lento.")
        print("     Usa --dry-run per validare, oppure esegui su una macchina con GPU.")

    # ---- STEP 1: fetch ----
    if args.skip_fetch or args.fetch_count == 0:
        print("\n[1/5] fetch: saltato")
    elif _has_source_images() and not args.force:
        print("\n[1/5] fetch: immagini sorgente già presenti (usa --force per riscaricare)")
    else:
        _run("1/5 · fetch capi reali (FashionMNIST)",
             _py("fetch_real_garments.py", "--count", str(args.fetch_count)))

    # ---- STEP 2: build ----
    if args.skip_build:
        print("\n[2/5] build: saltato")
    elif MANIFEST.is_file() and not args.force:
        print("\n[2/5] build: dataset già presente (usa --force per rigenerare)")
    else:
        _run("2/5 · build dataset etichettato",
             _py("build_condition_dataset.py", "--per-class", str(args.per_class)))

    # ---- STEP 3: distill (opzionale) ----
    want_distill = args.distill or args.distill_all
    if not want_distill:
        print("\n[3/5] distill: saltato (usa --distill per tutorial personalizzati)")
    elif not _llm_configured():
        print("\n[3/5] distill: SALTATO — nessun VLM configurato.")
        print("        Imposta CLOSETAI_LLM_MODEL + credenziali per abilitarlo.")
        print("        Il training userà i tutorial hardcoded del dataset base.")
    elif DISTILLED.is_file() and not args.force:
        print("\n[3/5] distill: dataset distillato già presente (usa --force per rifare)")
    else:
        distill_args = ["--all"] if args.distill_all else ["--sample", "60"]
        _run("3/5 · distillazione tutorial da VLM", _py("distill_tutorials.py", *distill_args))

    # ---- STEP 4: train ----
    train_args = ["--epochs", str(args.epochs)]
    if args.load_4bit:
        train_args.append("--load-4bit")
    if args.dry_run:
        train_args.append("--dry-run")
    _run("4/5 · training LoRA" + (" (DRY-RUN)" if args.dry_run else ""),
         _py("train_condition_vlm_lora.py", *train_args))

    # ---- STEP 5: verify ----
    print(f"\n{'=' * 70}\n>>> STEP: 5/5 · verifica\n{'=' * 70}")
    if args.dry_run:
        print("  Dry-run completato: setup valido. Rilancia senza --dry-run per addestrare.")
        return

    if (ADAPTER_DIR / "adapter_config.json").is_file():
        print(f"  [ok] Adapter LoRA salvato in {ADAPTER_DIR.relative_to(ROOT)}")
        print("\n  Il backend lo userà automaticamente (routing 'auto').")
        print("  Per forzarlo esplicitamente:")
        print("      CLOSETAI_CONDITION_BACKEND=vlm-lora  (poi avvia il backend)")
        print("\n  Verifica veloce dell'inferenza:")
        print("      uv run python -c \"from app.ml.condition_vlm import get_condition_vlm;"
              " print(get_condition_vlm())\"")
    else:
        print("  ⚠️  Adapter non trovato: controlla l'output dello step di training.")
        sys.exit(1)


if __name__ == "__main__":
    main()
