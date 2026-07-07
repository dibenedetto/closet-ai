"""Addestra la rete neurale multi-label per la gap analysis del guardaroba.

Legge ``ml/datasets/wardrobe/wardrobe_dataset.csv``, addestra un MLP a
predire i vuoti funzionali (multi-label, sigmoid + BCE), valuta con metriche
adatte al multi-label, salva i pesi in ``ml/weights/gap_model.pt``.

Uso::

    uv run python scripts/build_wardrobe_dataset.py --rows 4000
    uv run python scripts/train_gap_model.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.gap_model import (  # noqa: E402
    DROPOUT, FEATURE_NAMES, GAP_LABELS, HIDDEN_DIMS, build_mlp,
)

ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = ROOT / "ml" / "datasets" / "wardrobe" / "wardrobe_dataset.csv"
WEIGHTS_PATH = ROOT / "ml" / "weights" / "gap_model.pt"


def _load() -> tuple[np.ndarray, np.ndarray]:
    if not CSV_PATH.is_file():
        print(f"!! Dataset non trovato: {CSV_PATH}")
        print("   Genera prima: uv run python scripts/build_wardrobe_dataset.py")
        sys.exit(1)
    X, Y = [], []
    with CSV_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            X.append([float(row[name]) for name in FEATURE_NAMES])
            Y.append([int(row[lab]) for lab in GAP_LABELS])
    return np.asarray(X, dtype=np.float32), np.asarray(Y, dtype=np.float32)


def _split(n: int, seed: int):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(n * 0.15)
    n_val = int(n * 0.15)
    return idx[n_test + n_val:], idx[:n_val], idx[n_val:n_val + n_test]  # train, val, test


def train(epochs: int, lr: float, seed: int) -> None:
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    X, Y = _load()
    tr, va, te = _split(len(X), seed)

    # Standardizzazione (salvata nel checkpoint per l'inferenza).
    mean = X[tr].mean(axis=0)
    std = X[tr].std(axis=0) + 1e-6

    def norm(a):
        return torch.tensor((a - mean) / std, dtype=torch.float32)

    Xtr, Ytr = norm(X[tr]), torch.tensor(Y[tr])
    Xva, Yva = norm(X[va]), torch.tensor(Y[va])
    Xte = norm(X[te])

    model = build_mlp()
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()

    best_val, best_state, bad = 1e9, None, 0
    for epoch in range(1, epochs + 1):
        model.train()
        opt.zero_grad()
        loss = loss_fn(model(Xtr), Ytr)
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            vloss = loss_fn(model(Xva), Yva).item()
        if vloss < best_val:
            best_val, best_state, bad = vloss, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
        if epoch % 20 == 0 or epoch == 1:
            print(f"    epoch {epoch:3d}  train_loss={loss.item():.3f}  val_loss={vloss:.3f}")
        if bad >= 25:
            print(f"    early stopping a epoch {epoch} (best val_loss={best_val:.3f})")
            break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(model(Xte)).numpy()
    preds = (probs >= 0.5).astype(int)
    y_true = Y[te].astype(int)

    metrics = _report(y_true, preds)

    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": model.state_dict(),
        "features": list(FEATURE_NAMES),
        "labels": list(GAP_LABELS),
        "hidden": list(HIDDEN_DIMS),
        "dropout": DROPOUT,
        "threshold": 0.5,
        "feature_mean": mean.tolist(),
        "feature_std": std.tolist(),
        "metrics": metrics,
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
    }, WEIGHTS_PATH)
    print(f"\n==> Pesi salvati: {WEIGHTS_PATH.relative_to(ROOT)}")
    print("    Il backend userà la rete per /stats/gap-analysis.")


def _report(y_true: np.ndarray, preds: np.ndarray) -> dict:
    from sklearn.metrics import f1_score, hamming_loss

    subset_acc = float((preds == y_true).all(axis=1).mean())
    micro_f1 = float(f1_score(y_true, preds, average="micro", zero_division=0))
    macro_f1 = float(f1_score(y_true, preds, average="macro", zero_division=0))
    hl = float(hamming_loss(y_true, preds))

    print("\n==> Valutazione (test multi-label):")
    print(f"    Subset accuracy (tutte le label esatte): {subset_acc:.3f}")
    print(f"    Micro-F1: {micro_f1:.3f}   Macro-F1: {macro_f1:.3f}   Hamming loss: {hl:.3f}\n")
    print("    F1 per vuoto:")
    per = f1_score(y_true, preds, average=None, zero_division=0)
    per_label: dict[str, float] = {}
    for lab, score in zip(GAP_LABELS, per):
        per_label[lab] = float(score)
        print(f"      {lab:22s} {score:.3f}")

    return {
        "subset_accuracy": round(subset_acc, 4),
        "micro_f1": round(micro_f1, 4),
        "macro_f1": round(macro_f1, 4),
        "hamming_loss": round(hl, 4),
        "f1_per_label": {k: round(v, 4) for k, v in per_label.items()},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train(epochs=args.epochs, lr=args.lr, seed=args.seed)
