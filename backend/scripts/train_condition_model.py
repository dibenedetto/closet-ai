"""Addestra la testa MLP per la diagnosi dello stato del capo (Approccio A).

Pipeline:

1. Legge il manifest del dataset (``ml/datasets/garment_condition/manifest.csv``).
2. Estrae l'embedding Fashion-CLIP di ogni immagine (con cache su disco:
   l'estrazione CLIP è lenta, la facciamo una volta sola).
3. Addestra un MLP PyTorch sul train split, con early stopping su val.
4. Valuta su test: accuracy, classification report, confusion matrix (PNG).
5. Salva i pesi in ``ml/weights/condition_head.pt``.

Uso::

    uv run python scripts/train_condition_model.py
    uv run python scripts/train_condition_model.py --epochs 80 --no-cache

I pesi salvati vengono caricati automaticamente dal backend
(``app/ml/condition_model.py``) per sostituire l'euristica.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.condition_model import (  # noqa: E402
    CONDITION_LABELS, DROPOUT, EMBED_DIM, HIDDEN_DIMS, build_mlp,
)

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = ROOT / "ml" / "datasets" / "garment_condition"
MANIFEST = DATASET_DIR / "manifest.csv"
CACHE_PATH = DATASET_DIR / "clip_embeddings.npz"
WEIGHTS_PATH = ROOT / "ml" / "weights" / "condition_head.pt"
REPORT_DIR = DATASET_DIR

LABEL_TO_IDX = {lab: i for i, lab in enumerate(CONDITION_LABELS)}


def _read_manifest() -> list[dict]:
    if not MANIFEST.is_file():
        print(f"!! Manifest non trovato: {MANIFEST}")
        print("   Genera prima il dataset: uv run python scripts/build_condition_dataset.py")
        sys.exit(1)
    with MANIFEST.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _extract_embeddings(rows: list[dict], use_cache: bool):
    """Estrae embedding CLIP per ogni immagine. Cache su .npz."""
    if use_cache and CACHE_PATH.is_file():
        data = np.load(CACHE_PATH, allow_pickle=True)
        if len(data["X"]) == len(rows):
            print(f"==> Embedding caricati da cache ({CACHE_PATH.name})")
            return data["X"], data["y"], data["split"]
        print("==> Cache disallineata col manifest, riestraggo.")

    from app.ml.classifier import FashionClipClassifier

    print(f"==> Estraggo embedding Fashion-CLIP di {len(rows)} immagini (lento la prima volta)…")
    clf = FashionClipClassifier()
    X = np.zeros((len(rows), EMBED_DIM), dtype=np.float32)
    y = np.zeros(len(rows), dtype=np.int64)
    split = np.empty(len(rows), dtype=object)
    for i, row in enumerate(rows):
        img_path = DATASET_DIR / row["filename"]
        X[i] = np.asarray(clf.embed_image(img_path), dtype=np.float32)
        y[i] = LABEL_TO_IDX[row["condition"]]
        split[i] = row["split"]
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(rows)}")

    np.savez_compressed(CACHE_PATH, X=X, y=y, split=split)
    print(f"==> Embedding salvati in cache: {CACHE_PATH.name}")
    return X, y, split


def _train(X, y, split, *, epochs: int, lr: float, seed: int):
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    np.random.seed(seed)

    tr = split == "train"
    va = split == "val"
    te = split == "test"

    Xtr = torch.tensor(X[tr])
    ytr = torch.tensor(y[tr])
    Xva = torch.tensor(X[va])
    yva = torch.tensor(y[va])
    Xte = torch.tensor(X[te])
    yte = torch.tensor(y[te])

    model = build_mlp()
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss()

    best_val = -1.0
    best_state = None
    patience, bad = 12, 0

    for epoch in range(1, epochs + 1):
        model.train()
        opt.zero_grad()
        out = model(Xtr)
        loss = loss_fn(out, ytr)
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            val_acc = (model(Xva).argmax(1) == yva).float().mean().item()
        if val_acc > best_val:
            best_val, best_state, bad = val_acc, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
        if epoch % 10 == 0 or epoch == 1:
            print(f"    epoch {epoch:3d}  loss={loss.item():.3f}  val_acc={val_acc:.3f}")
        if bad >= patience:
            print(f"    early stopping a epoch {epoch} (best val_acc={best_val:.3f})")
            break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        test_logits = model(Xte)
        test_pred = test_logits.argmax(1).numpy()
    return model, best_val, yte.numpy(), test_pred


def _report(y_true, y_pred):
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

    acc = accuracy_score(y_true, y_pred)
    print(f"\n==> Test accuracy: {acc:.3f}\n")
    print(classification_report(
        y_true, y_pred, target_names=CONDITION_LABELS, zero_division=0,
    ))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cm = confusion_matrix(y_true, y_pred)
        fig, ax = plt.subplots(figsize=(5.5, 5))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(CONDITION_LABELS)), CONDITION_LABELS, rotation=30, ha="right")
        ax.set_yticks(range(len(CONDITION_LABELS)), CONDITION_LABELS)
        ax.set_xlabel("Predetto")
        ax.set_ylabel("Vero")
        ax.set_title(f"Stato di conservazione — test acc {acc:.2f}")
        for (i, j), v in np.ndenumerate(cm):
            ax.text(j, i, str(v), ha="center", va="center",
                    color="white" if v > cm.max() / 2 else "black", fontweight="bold")
        fig.colorbar(im, fraction=0.046)
        fig.tight_layout()
        out = REPORT_DIR / "condition_confusion_matrix.png"
        fig.savefig(out, dpi=120)
        print(f"==> Confusion matrix salvata: {out.relative_to(ROOT)}")
    except Exception as e:  # pragma: no cover
        print(f"   (grafico saltato: {e})")
    return acc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-cache", action="store_true", help="riestrai gli embedding")
    args = parser.parse_args()

    rows = _read_manifest()
    X, y, split = _extract_embeddings(rows, use_cache=not args.no_cache)

    print(f"==> Train MLP {EMBED_DIM} -> {HIDDEN_DIMS} -> {len(CONDITION_LABELS)} (dropout {DROPOUT})")
    model, best_val, y_true, y_pred = _train(
        X, y, split, epochs=args.epochs, lr=args.lr, seed=args.seed
    )
    test_acc = _report(y_true, y_pred)

    import torch
    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": model.state_dict(),
        "labels": list(CONDITION_LABELS),
        "in_dim": EMBED_DIM,
        "hidden": list(HIDDEN_DIMS),
        "dropout": DROPOUT,
        "val_accuracy": best_val,
        "test_accuracy": test_acc,
    }, WEIGHTS_PATH)
    print(f"\n==> Pesi salvati: {WEIGHTS_PATH.relative_to(ROOT)}")
    print("    Il backend ora userà il modello vision al posto dell'euristica.")


if __name__ == "__main__":
    main()
