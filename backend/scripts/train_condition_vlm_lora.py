"""Fine-tuning LoRA di un Visual-LLM per la diagnosi stato + tutorial (Approccio C).

Addestra un VLM (default ``Qwen/Qwen2-VL-2B-Instruct``) con **LoRA** a
produrre, da una foto di capo, un JSON strutturato::

    {"stato": "...", "difetto": "...", "tutorial": "..."}

Usa il dataset ``ml/datasets/garment_condition/vlm_dataset.jsonl`` già
prodotto da ``build_condition_dataset.py``.

──────────────────────────────────────────────────────────────────────────
REQUISITI
──────────────────────────────────────────────────────────────────────────
- GPU NVIDIA con ~10-16 GB di VRAM (Qwen2-VL-2B in LoRA bf16).
  Con QLoRA 4-bit (``--load-4bit``, richiede ``bitsandbytes``) bastano ~6-8 GB.
- Pacchetti: ``peft``, ``qwen-vl-utils`` (già installati come dev-deps),
  ``transformers``, ``torch``, e — per 4-bit — ``bitsandbytes``.

──────────────────────────────────────────────────────────────────────────
USO
──────────────────────────────────────────────────────────────────────────
    # 1) Valida setup e dataset SENZA scaricare il modello (~istantaneo):
    uv run python scripts/train_condition_vlm_lora.py --dry-run

    # 2) Training vero (scarica ~4GB di pesi al primo run):
    uv run python scripts/train_condition_vlm_lora.py --epochs 3

    # 3) Con QLoRA 4-bit (meno VRAM):
    uv run python scripts/train_condition_vlm_lora.py --load-4bit

L'adapter LoRA viene salvato in ``ml/weights/condition_vlm_lora/``.
L'inferenza è in ``app/ml/condition_vlm.py``.

Vedi ADR-010 in ``docs/architecture.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = ROOT / "ml" / "datasets" / "garment_condition"
ADAPTER_OUT = ROOT / "ml" / "weights" / "condition_vlm_lora"

DEFAULT_MODEL = "Qwen/Qwen2-VL-2B-Instruct"

# Candidati in ordine di preferenza: il dataset distillato (tutorial ricchi)
# vince sul base (tutorial hardcoded) se presente.
_DATASET_CANDIDATES = (
    "vlm_dataset_distilled.jsonl",
    "vlm_dataset.jsonl",
)


def _resolve_dataset(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = DATASET_DIR / explicit
        if not p.is_file():
            print(f"!! Dataset indicato non trovato: {p}")
            sys.exit(1)
        return p
    for name in _DATASET_CANDIDATES:
        cand = DATASET_DIR / name
        if cand.is_file():
            return cand
    print("!! Nessun dataset VLM trovato. Genera prima:")
    print("     uv run python scripts/build_condition_dataset.py --per-class 150")
    print("   (e, opzionale, distilla i tutorial:)")
    print("     uv run python scripts/distill_tutorials.py --all")
    sys.exit(1)


def load_records(dataset_path: Path) -> list[dict]:
    with dataset_path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def to_qwen_messages(record: dict) -> list[dict]:
    """Converte un record del nostro jsonl nel formato chat di Qwen2-VL.

    Il nostro formato:
        {"image": "images/.../x.png",
         "messages": [{"role":"user","content":"<image>\\n<istruzione>"},
                      {"role":"assistant","content":"<json>"}]}

    Formato Qwen2-VL: content come lista di blocchi {type: image|text}.
    """
    image_path = DATASET_DIR / record["image"]
    user_text = record["messages"][0]["content"].replace("<image>", "").strip()
    assistant_text = record["messages"][1]["content"]
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": str(image_path)},
                {"type": "text", "text": user_text},
            ],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": assistant_text}],
        },
    ]


def split_records(records: list[dict], val_frac: float = 0.1, seed: int = 42):
    import random

    rng = random.Random(seed)
    shuffled = records[:]
    rng.shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * val_frac))
    return shuffled[n_val:], shuffled[:n_val]


# ============================================================================
# Dry-run: valida senza scaricare nulla
# ============================================================================


def dry_run(dataset_path: Path) -> None:
    print("=== DRY-RUN: validazione setup LoRA (nessun download) ===\n")
    print(f"  Dataset: {dataset_path.relative_to(ROOT)}")

    # 1. dipendenze
    missing = []
    for mod in ("torch", "transformers", "peft", "qwen_vl_utils"):
        try:
            __import__(mod)
            print(f"  [ok] {mod}")
        except ImportError:
            missing.append(mod)
            print(f"  [MANCANTE] {mod}")
    if missing:
        print(f"\n!! Installa: uv add --dev {' '.join(missing)}")
        sys.exit(1)

    # 2. GPU
    import torch
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"\n  [ok] GPU: {name} ({vram:.1f} GB VRAM)")
    else:
        print("\n  [warn] Nessuna GPU CUDA rilevata: il training sarà "
              "improponibilmente lento su CPU. Usa una macchina con GPU.")

    # 3. dataset
    records = load_records(dataset_path)
    train, val = split_records(records)
    print(f"\n  [ok] Dataset: {len(records)} esempi  (train {len(train)} / val {len(val)})")

    # 4. immagini esistono?
    missing_imgs = [r["image"] for r in records[:50] if not (DATASET_DIR / r["image"]).is_file()]
    if missing_imgs:
        print(f"  [MANCANTI] {len(missing_imgs)} immagini non trovate (es. {missing_imgs[0]})")
        sys.exit(1)
    print("  [ok] Immagini presenti (campione di 50 verificato)")

    # 5. esempio convertito
    example = to_qwen_messages(records[0])
    answer = records[0]["messages"][1]["content"]
    print("\n  Esempio convertito (formato Qwen2-VL):")
    print(f"    image:     {example[0]['content'][0]['image']}")
    print(f"    istruzione:{example[0]['content'][1]['text'][:70]}…")
    print(f"    target:    {answer[:90]}…")

    # 6. distribuzione classi
    from collections import Counter
    dist = Counter(json.loads(r["messages"][1]["content"]).get("stato") for r in records)
    print(f"\n  Distribuzione stati: {dict(dist)}")

    print("\n=== Setup valido. Per addestrare davvero: rimuovi --dry-run ===")


# ============================================================================
# Training
# ============================================================================


def build_collate_fn(processor):
    from qwen_vl_utils import process_vision_info

    def collate_fn(records: list[dict]):
        messages_batch = [to_qwen_messages(r) for r in records]
        texts = [
            processor.apply_chat_template(m, tokenize=False, add_generation_prompt=False)
            for m in messages_batch
        ]
        image_inputs = [process_vision_info(m)[0] for m in messages_batch]

        batch = processor(
            text=texts, images=image_inputs, return_tensors="pt", padding=True
        )

        # Loss solo sui token di risposta: maschera padding e token immagine.
        labels = batch["input_ids"].clone()
        labels[labels == processor.tokenizer.pad_token_id] = -100
        image_token_id = getattr(processor.tokenizer, "image_token_id", None)
        if image_token_id is None:
            # Qwen2-VL: recupera l'id del token immagine dal vocab
            image_token_id = processor.tokenizer.convert_tokens_to_ids("<|image_pad|>")
        labels[labels == image_token_id] = -100
        batch["labels"] = labels
        return batch

    return collate_fn


def train(args, dataset_path: Path) -> None:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoProcessor,
        Qwen2VLForConditionalGeneration,
        Trainer,
        TrainingArguments,
    )

    records = load_records(dataset_path)
    train_recs, val_recs = split_records(records, val_frac=0.1, seed=args.seed)
    print(f"==> Dataset: {dataset_path.name} — {len(train_recs)} train / {len(val_recs)} val")

    print(f"==> Carico {args.model} (primo run: download ~4GB)…")
    model_kwargs: dict = {"torch_dtype": torch.bfloat16}
    if args.load_4bit:
        from transformers import BitsAndBytesConfig

        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
        )
    else:
        model_kwargs["device_map"] = "auto"

    model = Qwen2VLForConditionalGeneration.from_pretrained(args.model, **model_kwargs)
    processor = AutoProcessor.from_pretrained(args.model, min_pixels=256 * 28 * 28,
                                              max_pixels=768 * 28 * 28)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=str(ADAPTER_OUT),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to=[],
        remove_unused_columns=False,
        gradient_checkpointing=True,
    )

    collate_fn = build_collate_fn(processor)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_recs,  # lista di dict; il collator fa il resto
        eval_dataset=val_recs,
        data_collator=collate_fn,
    )

    trainer.train()

    ADAPTER_OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ADAPTER_OUT))
    processor.save_pretrained(str(ADAPTER_OUT))
    print(f"\n==> Adapter LoRA salvato in {ADAPTER_OUT.relative_to(ROOT)}")
    print("    Inferenza: app/ml/condition_vlm.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--load-4bit", action="store_true",
                        help="QLoRA 4-bit (richiede bitsandbytes, meno VRAM)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dataset", default=None,
                        help="jsonl da usare (default: distilled se presente, "
                             "altrimenti base)")
    parser.add_argument("--dry-run", action="store_true",
                        help="valida setup e dataset senza scaricare il modello")
    args = parser.parse_args()

    dataset_path = _resolve_dataset(args.dataset)
    if args.dry_run:
        dry_run(dataset_path)
    else:
        train(args, dataset_path)


if __name__ == "__main__":
    main()
