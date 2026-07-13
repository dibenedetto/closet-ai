"""Build the official-exam ML notebook set for ClosetAI.

The generated notebooks are intentionally split by learning task.  Each file
contains its own imports, data loading/generation, model, evaluation and an
explicit note about whether the model is used by the running product.

Run from ``backend/`` with::

    uv run python scripts/build_exam_notebooks.py
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "ml" / "notebooks" / "exam"


def md(text: str):
    return nbf.v4.new_markdown_cell(dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(dedent(text).strip())


def notebook(title: str, cells: list) -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook(cells=cells)
    nb["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3 (ClosetAI)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.14"},
        "closetai": {"exam_title": title, "status": "official-exam"},
    }
    return nb


ROOT_CELL = code(
    """
    # Trova la radice del repository anche se Jupyter parte da una sottocartella.
    from pathlib import Path

    def find_project_root(start: Path | None = None) -> Path:
        here = (start or Path.cwd()).resolve()
        for candidate in (here, *here.parents):
            if (candidate / "backend" / "pyproject.toml").is_file() and (candidate / "ml").is_dir():
                return candidate
        raise FileNotFoundError("Radice di ClosetAI non trovata")

    ROOT = find_project_root()
    SEED = 42
    print(f"Repository: {ROOT}")
    """
)


def build_condition_notebook():
    cells = [
        md(
            """
            # ClosetAI · Diagnosi dello stato del capo
            ## Testa MLP addestrata su embedding Fashion-CLIP congelati

            **Stato nel prodotto:** modello di produzione. Il backend carica il
            checkpoint `ml/weights/condition_head.pt`; se manca, usa un fallback
            euristico.

            **Domanda:** una foto mostra un capo `buono`, `usurato` o
            `danneggiato`?

            La rete Fashion-CLIP è **pre-addestrata da terzi e congelata**. Noi
            addestriamo soltanto una piccola testa neurale MLP:

            `foto → Fashion-CLIP (512 feature) → 256 → 128 → 3 classi`

            Il notebook non sovrascrive i pesi dell'app: riproduce il training e
            rende visibili dati, scelte, metriche e limiti per l'esame.
            """
        ),
        ROOT_CELL,
        code(
            """
            # Import riproducibili. Gli embedding CLIP sono già in cache: in questo
            # modo l'esame non dipende dalla rete o da un download di ~600 MB.
            import copy
            import random
            import time

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd
            import torch
            import torch.nn as nn
            from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix

            random.seed(SEED)
            np.random.seed(SEED)
            torch.manual_seed(SEED)
            torch.set_num_threads(1)

            DATA_DIR = ROOT / "ml" / "datasets" / "garment_condition"
            manifest = pd.read_csv(DATA_DIR / "manifest.csv")
            cached = np.load(DATA_DIR / "clip_embeddings.npz", allow_pickle=True)
            X = cached["X"].astype("float32")
            y = cached["y"].astype("int64")
            split = cached["split"].astype(str)
            LABELS = ["buono", "usurato", "danneggiato"]

            assert len(manifest) == len(X) == len(y) == len(split)
            assert X.shape[1] == 512
            print(f"Campioni: {len(X)} · embedding: {X.shape[1]}D")
            pd.crosstab(manifest["split"], manifest["condition"])
            """
        ),
        md(
            """
            ### Provenienza dei dati

            Il dataset è ibrido: immagini con difetti reali dal dataset COCO
            *Defect-Clothes* e degradazioni sintetiche controllate per simulare
            l'usura. Il vantaggio è poter costruire una pipeline completa; il
            limite è il possibile **domain gap** rispetto alle foto scattate da
            utenti reali. Inoltre il dataset locale è risuddiviso casualmente e
            non conserva gli split originali della sorgente: campioni correlati
            non sono esclusi con certezza fra train e test. Perciò l'accuracy qui
            sotto è un **holdout del prototipo**, non una validazione esterna né
            una certificazione industriale.
            """
        ),
        code(
            """
            # Separiamo usando lo split già scritto nel manifest. Il test resta
            # escluso da ogni decisione di training e early stopping.
            masks = {name: split == name for name in ("train", "val", "test")}
            tensors = {}
            for name, mask in masks.items():
                tensors[name] = (
                    torch.tensor(X[mask], dtype=torch.float32),
                    torch.tensor(y[mask], dtype=torch.long),
                )
                print(name, tensors[name][0].shape)

            def build_model():
                return nn.Sequential(
                    nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.30),
                    nn.Linear(256, 128), nn.ReLU(), nn.Dropout(0.30),
                    nn.Linear(128, 3),
                )

            model = build_model()
            trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
            print(f"Parametri addestrabili della nostra testa: {trainable:,}")
            model
            """
        ),
        code(
            """
            # Full-batch training: il dataset è piccolo. Adam + weight decay
            # riduce l'overfitting; early stopping usa soltanto la validation.
            optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
            criterion = nn.CrossEntropyLoss()
            history = {"train_loss": [], "val_accuracy": []}
            best_val, best_state, stale = -1.0, None, 0
            patience, max_epochs = 12, 120
            Xtr, ytr = tensors["train"]
            Xva, yva = tensors["val"]

            started = time.perf_counter()
            for epoch in range(1, max_epochs + 1):
                model.train()
                optimizer.zero_grad()
                loss = criterion(model(Xtr), ytr)
                loss.backward()
                optimizer.step()

                model.eval()
                with torch.no_grad():
                    val_accuracy = (model(Xva).argmax(1) == yva).float().mean().item()
                history["train_loss"].append(loss.item())
                history["val_accuracy"].append(val_accuracy)

                if val_accuracy > best_val:
                    best_val = val_accuracy
                    best_state = copy.deepcopy(model.state_dict())
                    stale = 0
                else:
                    stale += 1
                if stale >= patience:
                    break

            model.load_state_dict(best_state)
            print(f"Stop a epoca {epoch}; best validation accuracy={best_val:.3f}; tempo={time.perf_counter()-started:.1f}s")

            fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
            axes[0].plot(history["train_loss"], color="#176B4D")
            axes[0].set(title="Loss di training", xlabel="epoca", ylabel="cross-entropy")
            axes[1].plot(history["val_accuracy"], color="#E07A3F")
            axes[1].set(title="Accuracy di validation", xlabel="epoca", ylabel="accuracy", ylim=(0, 1.02))
            plt.tight_layout(); plt.show()
            """
        ),
        code(
            """
            # Il test viene aperto una sola volta, dopo aver fissato il modello.
            Xte, yte = tensors["test"]
            model.eval()
            with torch.no_grad():
                logits = model(Xte)
                predictions = logits.argmax(1).numpy()
                probabilities = logits.softmax(1).numpy()

            test_accuracy = float((predictions == yte.numpy()).mean())
            print(f"TEST accuracy: {test_accuracy:.3f}")
            print(classification_report(yte.numpy(), predictions, target_names=LABELS, digits=3, zero_division=0))

            cm = confusion_matrix(yte.numpy(), predictions)
            ConfusionMatrixDisplay(cm, display_labels=LABELS).plot(cmap="Greens", colorbar=False)
            plt.title("Stato del capo · matrice di confusione sul test")
            plt.tight_layout(); plt.show()
            """
        ),
        code(
            """
            # Esempio di inferenza completamente tracciabile su un campione test.
            idx = 0
            true_label = LABELS[int(yte[idx])]
            pred_label = LABELS[int(predictions[idx])]
            table = pd.Series(probabilities[idx], index=LABELS, name="probabilità").sort_values(ascending=False)
            print(f"Vero: {true_label} · Predetto: {pred_label}")
            table.to_frame()
            """
        ),
        md(
            """
            ### Cosa dire all'esame

            - Abbiamo congelato Fashion-CLIP e addestrato solo circa 164 mila
              parametri: è **transfer learning**, non training da zero.
            - Accuracy e confusion matrix misurano cose diverse: la seconda fa
              vedere *quali* stati vengono confusi.
            - L'early stopping usa validation; il test non guida il training.
            - Il limite principale non è l'architettura ma la rappresentatività
              delle foto. Prima di un rilascio servono dati reali, consenso,
              analisi dei bias e una valutazione per condizioni di luce/camera.
            """
        ),
    ]
    return notebook("Diagnosi stato del capo", cells)


def build_gap_notebook():
    cells = [
        md(
            """
            # ClosetAI · Gap analysis del guardaroba
            ## Rete neurale multi-label su dati aggregati

            **Stato nel prodotto:** modello di produzione. Il checkpoint
            `ml/weights/gap_model.pt` alimenta la sezione “Cosa manca davvero?”
            della dashboard; se non è disponibile, il backend torna a regole
            esperte trasparenti.

            **Domanda:** il guardaroba presenta uno o più vuoti funzionali?
            Ogni riga rappresenta un intero guardaroba, non una singola foto.
            """
        ),
        ROOT_CELL,
        code(
            """
            import copy
            import random
            import time

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd
            import torch
            import torch.nn as nn
            from sklearn.metrics import f1_score, hamming_loss

            random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
            torch.set_num_threads(1)

            FEATURES = [
                "n_top", "n_bottom", "n_outerwear", "n_shoes", "n_dress", "n_accessory",
                "n_total", "frac_tshirt", "frac_outerwear", "frac_winter", "frac_formal",
                "n_colors", "has_neutral", "ghost_ratio",
            ]
            LABELS = [
                "manca_capospalla", "manca_scarpe", "manca_formale",
                "manca_invernale", "troppe_tshirt", "poca_varieta_colori",
            ]

            path = ROOT / "ml" / "datasets" / "wardrobe" / "wardrobe_dataset.csv"
            df = pd.read_csv(path)
            X = df[FEATURES].to_numpy(dtype="float32")
            Y = df[LABELS].to_numpy(dtype="float32")
            print(f"Guardaroba simulati: {len(df):,} · feature: {X.shape[1]} · label: {Y.shape[1]}")
            (df[LABELS].mean().sort_values(ascending=False) * 100).round(1).rename("% positivi").to_frame()
            """
        ),
        md(
            """
            ### Perché “multi-label”

            Le sei uscite hanno una sigmoid indipendente: lo stesso guardaroba
            può contemporaneamente avere poche scarpe, poca varietà cromatica e
            troppi top. Una softmax sarebbe sbagliata perché imporrebbe una sola
            classe.

            Le label sono generate da regole esperte su profili sintetici. La
            rete dimostra la pipeline e può apprendere interazioni, ma **non prova
            che quei criteri siano universalmente corretti**. Con dati reali,
            servirebbero feedback degli utenti e una nuova validazione.
            """
        ),
        code(
            """
            # Split deterministico 70/15/15. Media e deviazione sono calcolate
            # SOLO sul train per evitare leakage statistico.
            rng = np.random.default_rng(SEED)
            order = rng.permutation(len(X))
            n_test = int(len(X) * 0.15)
            n_val = int(len(X) * 0.15)
            test_idx = order[:n_test]
            val_idx = order[n_test:n_test+n_val]
            train_idx = order[n_test+n_val:]

            mean = X[train_idx].mean(axis=0)
            std = X[train_idx].std(axis=0) + 1e-6

            def tx(indices):
                return (
                    torch.tensor((X[indices] - mean) / std, dtype=torch.float32),
                    torch.tensor(Y[indices], dtype=torch.float32),
                )

            Xtr, Ytr = tx(train_idx); Xva, Yva = tx(val_idx); Xte, Yte = tx(test_idx)
            print("train", len(train_idx), "validation", len(val_idx), "test", len(test_idx))

            def build_model():
                return nn.Sequential(
                    nn.Linear(14, 64), nn.ReLU(), nn.Dropout(0.20),
                    nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.20),
                    nn.Linear(32, 6),
                )

            model = build_model()
            print(f"Parametri addestrabili: {sum(p.numel() for p in model.parameters()):,}")
            model
            """
        ),
        code(
            """
            # BCEWithLogitsLoss combina sigmoid + binary cross entropy in modo
            # numericamente stabile. Early stopping monitora la validation loss.
            optimizer = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-4)
            criterion = nn.BCEWithLogitsLoss()
            best_loss, best_state, stale = float("inf"), None, 0
            patience, max_epochs = 25, 300
            history = {"train": [], "validation": []}

            started = time.perf_counter()
            for epoch in range(1, max_epochs + 1):
                model.train(); optimizer.zero_grad()
                train_loss = criterion(model(Xtr), Ytr)
                train_loss.backward(); optimizer.step()

                model.eval()
                with torch.no_grad():
                    val_loss = criterion(model(Xva), Yva).item()
                history["train"].append(train_loss.item())
                history["validation"].append(val_loss)
                if val_loss < best_loss:
                    best_loss = val_loss
                    best_state = copy.deepcopy(model.state_dict())
                    stale = 0
                else:
                    stale += 1
                if stale >= patience:
                    break

            model.load_state_dict(best_state)
            print(f"Stop a epoca {epoch}; best val loss={best_loss:.4f}; tempo={time.perf_counter()-started:.1f}s")
            plt.figure(figsize=(8, 3.4))
            plt.plot(history["train"], label="train", color="#176B4D")
            plt.plot(history["validation"], label="validation", color="#E07A3F")
            plt.xlabel("epoca"); plt.ylabel("BCE"); plt.title("Curva di apprendimento"); plt.legend()
            plt.tight_layout(); plt.show()
            """
        ),
        code(
            """
            # Soglia operativa fissata a 0.5, come nel backend.
            model.eval()
            with torch.no_grad():
                test_prob = torch.sigmoid(model(Xte)).numpy()
            test_pred = (test_prob >= 0.5).astype(int)
            y_true = Yte.numpy().astype(int)

            subset_accuracy = float((test_pred == y_true).all(axis=1).mean())
            micro_f1 = f1_score(y_true, test_pred, average="micro", zero_division=0)
            macro_f1 = f1_score(y_true, test_pred, average="macro", zero_division=0)
            hamming = hamming_loss(y_true, test_pred)
            print(f"Subset accuracy: {subset_accuracy:.3f}")
            print(f"Micro-F1: {micro_f1:.3f} · Macro-F1: {macro_f1:.3f} · Hamming loss: {hamming:.3f}")

            per_label = pd.DataFrame({
                "label": LABELS,
                "F1": f1_score(y_true, test_pred, average=None, zero_division=0),
                "prevalenza_test": y_true.mean(axis=0),
            }).sort_values("F1")
            per_label
            """
        ),
        code(
            """
            # Esempio leggibile: probabilità di tutti i gap per un guardaroba test.
            sample = 0
            result = pd.DataFrame({
                "gap": LABELS,
                "probabilità": test_prob[sample],
                "predetto": test_pred[sample].astype(bool),
                "vero": y_true[sample].astype(bool),
            }).sort_values("probabilità", ascending=False)
            result
            """
        ),
        md(
            """
            ### Cosa dire all'esame

            - “Multi-label” significa più risposte vere nello stesso esempio.
            - Micro-F1 pesa tutte le decisioni; macro-F1 dà pari dignità anche ai
              gap meno frequenti; subset accuracy è molto severa perché richiede
              che tutte e sei le risposte siano corrette insieme.
            - Il dato sintetico deriva da regole: oggi la rete è un dimostratore
              tecnico. Il valore scientifico futuro dipende da etichette reali e
              da una definizione partecipata di “guardaroba equilibrato”.
            - Il fallback a regole rende il prodotto utilizzabile e spiegabile
              anche senza checkpoint.
            """
        ),
    ]
    return notebook("Gap analysis multi-label", cells)


SYNTHETIC_WARDROBE_CELL = code(
    """
    # Dataset sintetico deterministico usato SOLO per l'esperimento didattico.
    # In produzione queste righe dovrebbero arrivare dal wear log consensuale.
    import numpy as np
    import pandas as pd

    CATEGORIES = ["t-shirt", "camicia", "felpa", "maglione", "giacca", "cappotto",
                  "jeans", "pantaloni", "shorts", "gonna", "vestito", "scarpe"]
    COLORS = ["nero", "bianco", "blu", "rosso", "verde", "beige", "grigio", "marrone"]
    WEAR_PRIOR = {"t-shirt": 38, "camicia": 20, "felpa": 24, "maglione": 18,
                  "giacca": 12, "cappotto": 8, "jeans": 34, "pantaloni": 24,
                  "shorts": 12, "gonna": 10, "vestito": 8, "scarpe": 30}
    PRICE_RANGE = {"t-shirt": (10, 40), "camicia": (25, 90), "felpa": (25, 80),
                   "maglione": (40, 130), "giacca": (60, 220), "cappotto": (120, 400),
                   "jeans": (40, 140), "pantaloni": (30, 120), "shorts": (15, 60),
                   "gonna": (25, 100), "vestito": (45, 180), "scarpe": (50, 180)}

    def generate_wardrobe(n=800, seed=SEED):
        rng = np.random.default_rng(seed)
        rows = []
        for _ in range(n):
            category = str(rng.choice(CATEGORIES))
            low, high = PRICE_RANGE[category]
            price = float(rng.uniform(low, high))
            days_owned = int(rng.integers(20, 1100))
            month = int(rng.integers(0, 12))
            years = days_owned / 365
            price_factor = 1 - 0.1 * (price - low) / max(high - low, 1)
            # Outcome didattico a 90 giorni. Questi coefficienti non sono
            # osservazioni reali: sono dichiarati per rendere l'esperimento
            # riproducibile senza creare un dataset degenere.
            occasion_risk = {"cappotto": 1.55, "vestito": 1.25, "giacca": .85,
                             "gonna": .65, "camicia": .45}.get(category, 0.0)
            off_season = (
                1.35 if category in {"cappotto", "maglione", "giacca"} and month in {4, 5, 6, 7, 8}
                else .9 if category in {"shorts", "t-shirt"} and month in {10, 11, 0, 1, 2}
                else 0.0
            )
            price_risk = .55 * ((price - low) / max(high - low, 1))
            logit = -2.25 + occasion_risk + off_season + price_risk + rng.normal(0, .20)
            ghost_probability = 1 / (1 + np.exp(-logit))
            ghost_outcome = int(rng.random() < ghost_probability)

            if ghost_outcome:
                wear = int(rng.integers(0, 2))
            else:
                wear = WEAR_PRIOR[category] * years * price_factor * rng.normal(1, 0.25)
            rows.append({
                "category": category, "color": str(rng.choice(COLORS)),
                "price_eur": round(price, 2), "days_owned": days_owned,
                "purchase_month": month, "wear_count": max(0, int(round(wear))),
                "is_ghost": ghost_outcome,
            })
        data = pd.DataFrame(rows)
        return data

    df = generate_wardrobe()
    print(df.shape, "ghost rate", f"{df['is_ghost'].mean():.1%}")
    df.head()
    """
)


def build_ghost_notebook():
    cells = [
        md(
            """
            # ClosetAI · Predire il rischio di “capo fantasma”
            ## Classificazione logistica interpretabile

            **Stato nel prodotto:** esperimento di ricerca, **non collegato alla
            UI**. L'app rileva oggi i capi fantasma con una regola auditabile:
            zero utilizzi e possesso da almeno una soglia di giorni.

            Questo notebook esplora una domanda futura: usando soltanto dati
            disponibili quando cataloghiamo un acquisto, possiamo stimare il
            rischio che resti inutilizzato nei 90 giorni successivi?
            """
        ),
        ROOT_CELL,
        SYNTHETIC_WARDROBE_CELL,
        code(
            """
            import matplotlib.pyplot as plt
            from sklearn.compose import ColumnTransformer
            from sklearn.impute import SimpleImputer
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import (
                ConfusionMatrixDisplay, RocCurveDisplay, average_precision_score,
                classification_report, f1_score, roc_auc_score,
            )
            from sklearn.model_selection import train_test_split
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import OneHotEncoder, StandardScaler

            categorical = ["category", "color"]
            # Feature engineering dichiarato: sono trasformazioni dei dati di
            # catalogazione, non informazioni osservate dopo i 90 giorni.
            winter = {"cappotto", "maglione", "giacca"}
            summer = {"shorts", "t-shirt"}
            df["is_off_season"] = [
                int((cat in winter and month in {4, 5, 6, 7, 8}) or
                    (cat in summer and month in {10, 11, 0, 1, 2}))
                for cat, month in zip(df["category"], df["purchase_month"])
            ]
            df["relative_price"] = [
                (price - PRICE_RANGE[cat][0]) / (PRICE_RANGE[cat][1] - PRICE_RANGE[cat][0])
                for cat, price in zip(df["category"], df["price_eur"])
            ]
            numeric = ["purchase_month", "is_off_season", "relative_price"]
            X = df[categorical + numeric]
            y = df["is_ghost"]

            # wear_count e days_owned NON sono feature: il primo rivelerebbe
            # l'outcome, il secondo non è noto al momento dell'acquisto.
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.25, random_state=SEED, stratify=y
            )
            model = Pipeline([
                ("prep", ColumnTransformer([
                    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
                    ("num", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), numeric),
                ])),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED)),
            ])
            model.fit(X_train, y_train)
            probability = model.predict_proba(X_test)[:, 1]
            prediction = model.predict(X_test)
            print(f"Baseline positiva (prevalenza): {y_test.mean():.3f}")
            print(f"ROC-AUC: {roc_auc_score(y_test, probability):.3f}")
            print(f"PR-AUC / average precision: {average_precision_score(y_test, probability):.3f}")
            print(f"F1 alla soglia 0.5: {f1_score(y_test, prediction):.3f}")
            print(classification_report(y_test, prediction, target_names=["non ghost", "ghost"], zero_division=0))

            fig, axes = plt.subplots(1, 2, figsize=(11, 4))
            ConfusionMatrixDisplay.from_predictions(y_test, prediction, display_labels=["non ghost", "ghost"], ax=axes[0], cmap="Greens", colorbar=False)
            RocCurveDisplay.from_predictions(y_test, probability, ax=axes[1], color="#176B4D")
            axes[0].set_title("Matrice di confusione"); axes[1].set_title("Curva ROC")
            plt.tight_layout(); plt.show()
            """
        ),
        code(
            """
            # I coefficienti permettono di spiegare il segno dell'effetto.
            cat_names = model.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(categorical)
            names = list(cat_names) + numeric
            coefficients = pd.Series(model.named_steps["model"].coef_[0], index=names).sort_values()
            pd.concat([coefficients.head(6), coefficients.tail(6)]).rename("coefficiente").to_frame()
            """
        ),
        md(
            """
            ### Cosa dire all'esame

            - È una baseline interpretabile, non una rete neurale.
            - ROC-AUC misura l'ordinamento del rischio, non la qualità di una
              singola soglia; precision e recall restano necessarie.
            - Le metriche su dati sintetici non dimostrano efficacia reale.
            - Prima di usare questa previsione per influenzare acquisti servono
              wear log longitudinali, consenso e controllo di bias/stagionalità.
            """
        ),
    ]
    return notebook("Rischio capo fantasma", cells)


def build_forecast_notebook():
    cells = [
        md(
            """
            # ClosetAI · Previsione degli utilizzi nei prossimi 90 giorni
            ## Random forest per una regressione non lineare

            **Stato nel prodotto:** esperimento di ricerca, non collegato alla
            UI. Il prodotto mostra conteggi e cost-per-wear osservati; non espone
            ancora una previsione futura.
            """
        ),
        ROOT_CELL,
        SYNTHETIC_WARDROBE_CELL,
        code(
            """
            import matplotlib.pyplot as plt
            from sklearn.compose import ColumnTransformer
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.metrics import mean_absolute_error, r2_score
            from sklearn.model_selection import train_test_split
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import OneHotEncoder

            rng = np.random.default_rng(SEED)
            season = np.sin((df["purchase_month"] / 12) * 2 * np.pi) * 0.3 + 1
            df["wear_next_90d"] = (
                (df["wear_count"] / np.maximum(df["days_owned"] / 365, 0.3)) / 4
                * season * rng.normal(1, 0.15, len(df))
            ).clip(0).round().astype(int)

            cat = ["category", "color"]
            num = ["price_eur", "days_owned", "purchase_month", "wear_count"]
            X_train, X_test, y_train, y_test = train_test_split(
                df[cat + num], df["wear_next_90d"], test_size=0.25, random_state=SEED
            )
            model = Pipeline([
                ("prep", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cat), ("num", "passthrough", num)])),
                ("model", RandomForestRegressor(n_estimators=200, max_depth=10, min_samples_leaf=2, random_state=SEED, n_jobs=-1)),
            ])
            model.fit(X_train, y_train)
            prediction = model.predict(X_test)
            mae = mean_absolute_error(y_test, prediction)
            r2 = r2_score(y_test, prediction)
            print(f"MAE: {mae:.2f} utilizzi · R²: {r2:.3f}")

            limit = max(float(y_test.max()), float(prediction.max())) + 1
            plt.figure(figsize=(6, 5))
            plt.scatter(y_test, prediction, alpha=.55, color="#176B4D")
            plt.plot([0, limit], [0, limit], "--", color="#E07A3F", label="predizione perfetta")
            plt.xlabel("utilizzi veri"); plt.ylabel("utilizzi previsti")
            plt.title("Previsione a 90 giorni"); plt.legend(); plt.tight_layout(); plt.show()
            """
        ),
        code(
            """
            # Importanza impurity-based: utile per orientarsi, non è causalità.
            cat_names = model.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(cat)
            feature_names = list(cat_names) + num
            importance = pd.Series(model.named_steps["model"].feature_importances_, index=feature_names).nlargest(12)
            importance.sort_values().plot.barh(figsize=(8, 4), color="#176B4D", title="Feature importance")
            plt.tight_layout(); plt.show()
            """
        ),
        md(
            """
            ### Cosa dire all'esame

            - MAE è espresso nell'unità comprensibile: numero di utilizzi.
            - R² confronta il modello con la media, ma può essere instabile su
              dataset piccoli o distribuzioni diverse.
            - Il wear storico è un segnale legittimo perché esiste prima della
              finestra futura; bisogna però costruire finestre temporali reali
              per evitare leakage.
            - L'importanza di una feature non implica una relazione causale.
            """
        ),
    ]
    return notebook("Previsione utilizzi", cells)


def build_clustering_notebook():
    cells = [
        md(
            """
            # ClosetAI · Cluster di stile nel guardaroba
            ## K-means non supervisionato + PCA per la visualizzazione

            **Stato nel prodotto:** esperimento di ricerca, non collegato alla
            UI. K-means non “scopre la verità”: crea gruppi secondo le feature e
            la distanza che scegliamo.
            """
        ),
        ROOT_CELL,
        SYNTHETIC_WARDROBE_CELL,
        code(
            """
            import matplotlib.pyplot as plt
            from sklearn.cluster import KMeans
            from sklearn.compose import ColumnTransformer
            from sklearn.decomposition import TruncatedSVD
            from sklearn.metrics import silhouette_score
            from sklearn.preprocessing import OneHotEncoder, StandardScaler

            cat = ["category", "color"]
            num = ["price_eur", "days_owned", "wear_count"]
            prep = ColumnTransformer([
                ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
                ("num", StandardScaler(), num),
            ])
            embedded = prep.fit_transform(df[cat + num])

            rows = []
            for k in range(2, 9):
                candidate = KMeans(n_clusters=k, random_state=SEED, n_init=20).fit(embedded)
                rows.append({"k": k, "inertia": candidate.inertia_, "silhouette": silhouette_score(embedded, candidate.labels_)})
            diagnostics = pd.DataFrame(rows)
            diagnostics
            """
        ),
        code(
            """
            # Scegliamo K=5 come compromesso didattico: non è una verità naturale.
            K = 5
            kmeans = KMeans(n_clusters=K, random_state=SEED, n_init=20).fit(embedded)
            df["cluster"] = kmeans.labels_

            # TruncatedSVD gestisce direttamente la matrice sparsa one-hot.
            projection = TruncatedSVD(n_components=2, random_state=SEED).fit_transform(embedded)
            plt.figure(figsize=(8, 5))
            for cluster in range(K):
                mask = df["cluster"] == cluster
                plt.scatter(projection[mask, 0], projection[mask, 1], s=24, alpha=.65, label=f"cluster {cluster}")
            plt.xlabel("componente 1"); plt.ylabel("componente 2")
            plt.title("Proiezione 2D dei cluster (solo per visualizzare)")
            plt.legend(ncol=2); plt.tight_layout(); plt.show()
            """
        ),
        code(
            """
            # Profilare i cluster è indispensabile: un numero da solo non ha senso.
            profile = df.groupby("cluster").agg(
                n=("category", "size"),
                categoria_top=("category", lambda s: s.mode().iloc[0]),
                colore_top=("color", lambda s: s.mode().iloc[0]),
                prezzo_medio=("price_eur", "mean"),
                utilizzi_medi=("wear_count", "mean"),
                giorni_medi=("days_owned", "mean"),
            ).round(1)
            profile
            """
        ),
        md(
            """
            ### Cosa dire all'esame

            - K-means minimizza la distanza interna ai cluster; non usa etichette.
            - Scaling e one-hot encoding definiscono implicitamente cosa conta
              come “vicino”. Cambiandoli, cambiano i cluster.
            - Silhouette aiuta a confrontare K, ma va letta insieme alla
              comprensibilità dei profili.
            - La proiezione 2D perde informazione ed è solo una visualizzazione.
            """
        ),
    ]
    return notebook("Clustering di stile", cells)


def build_readme() -> str:
    return dedent(
        """
        # Notebook ML per l'esame ufficiale

        Ogni notebook è autosufficiente e distingue chiaramente ciò che è
        caricato dal prodotto da ciò che è un esperimento didattico.

        | File | Modello | Stato nel prodotto |
        | --- | --- | --- |
        | `01_condition_state_mlp.ipynb` | MLP PyTorch su embedding Fashion-CLIP | **In uso** per lo stato del capo |
        | `02_wardrobe_gap_mlp.ipynb` | MLP PyTorch multi-label | **In uso** per i gap del guardaroba |
        | `03_ghost_risk_logistic_regression.ipynb` | Logistic regression | Esperimento, non collegato alla UI |
        | `04_wear_forecast_random_forest.ipynb` | Random forest regression | Esperimento, non collegato alla UI |
        | `05_style_clustering_kmeans.ipynb` | K-means | Esperimento, non collegato alla UI |

        Fashion-CLIP non compare come training “nostro”: il progetto lo usa
        pre-addestrato per inferenza e come estrattore di embedding congelato.
        Il recommender outfit, il cost-per-wear, i capi fantasma operativi e le
        stime CO₂ sono logiche/regole, non modelli addestrati.

        ## Esecuzione

        Da `backend/`:

        ```powershell
        uv run jupyter nbconvert --to notebook --execute --inplace ../ml/notebooks/exam/*.ipynb
        ```

        I notebook sono consegnati già eseguiti. Rieseguirli serve a dimostrare
        riproducibilità; non sovrascrivono i checkpoint usati dall'app.
        """
    ).strip() + "\n"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    notebooks = {
        "01_condition_state_mlp.ipynb": build_condition_notebook(),
        "02_wardrobe_gap_mlp.ipynb": build_gap_notebook(),
        "03_ghost_risk_logistic_regression.ipynb": build_ghost_notebook(),
        "04_wear_forecast_random_forest.ipynb": build_forecast_notebook(),
        "05_style_clustering_kmeans.ipynb": build_clustering_notebook(),
    }
    for filename, nb in notebooks.items():
        path = OUT_DIR / filename
        nbf.write(nb, path)
        print(f"Scritto {path.relative_to(ROOT)}")
    (OUT_DIR / "README.md").write_text(build_readme(), encoding="utf-8")
    print(f"Scritto {(OUT_DIR / 'README.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
