"""Endpoint per la pagina tecnica ML Lab.

Espone lo stato di **training / test / eval** delle reti addestrate da noi
(rete stato del capo, rete gap analysis, adapter VLM) e due endpoint di
prova interattiva usati dal frontend:

- ``POST /ml/condition/predict`` — foto → stato predetto (senza creare item)
- ``POST /ml/gap/predict``       — conteggi simulati → vuoti predetti

Tutto in sola lettura rispetto al DB: la pagina serve a *ispezionare e
provare* i modelli, non a modificare il guardaroba.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import ALLOWED_IMAGE_CONTENT_TYPES, MAX_UPLOAD_SIZE, PROJECT_ROOT
from app.schemas.ml_lab import (
    ConditionPredictOut,
    DatasetInfo,
    GapPredictIn,
    GapPredictOut,
    MlLabStatus,
    ModelInfo,
)

router = APIRouter(prefix="/ml", tags=["ml-lab"])
log = logging.getLogger(__name__)

CONFUSION_MATRIX_PNG = (
    PROJECT_ROOT / "ml" / "datasets" / "garment_condition" / "condition_confusion_matrix.png"
)
CONDITION_MANIFEST = PROJECT_ROOT / "ml" / "datasets" / "garment_condition" / "manifest.csv"
WARDROBE_CSV = PROJECT_ROOT / "ml" / "datasets" / "wardrobe" / "wardrobe_dataset.csv"


def _load_ckpt_meta(path: Path) -> dict | None:
    """Legge i metadati di un checkpoint torch senza istanziare il modello."""
    if not path.is_file():
        return None
    try:
        import torch

        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        return {k: v for k, v in ckpt.items() if k != "state_dict"}
    except Exception:
        log.warning("Checkpoint illeggibile: %s", path, exc_info=True)
        return None


def _rel(path: Path) -> str:
    """Path relativo al repo se possibile, altrimenti assoluto (es. nei test)."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _count_csv_rows(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)  # meno l'header
    except Exception:
        return None


@router.get("/models", response_model=MlLabStatus)
def get_models_status() -> MlLabStatus:
    """Stato + metriche delle reti addestrate da noi e dei loro dataset."""
    from app.ml.condition_model import WEIGHTS_PATH as COND_W
    from app.ml.condition_vlm import ADAPTER_DIR
    from app.ml.gap_model import WEIGHTS_PATH as GAP_W

    cond_meta = _load_ckpt_meta(COND_W) or {}
    gap_meta = _load_ckpt_meta(GAP_W) or {}

    cond_metrics = None
    if cond_meta:
        cond_metrics = {
            "val_accuracy": cond_meta.get("val_accuracy"),
            "test_accuracy": cond_meta.get("test_accuracy"),
        }

    models = [
        ModelInfo(
            key="condition-mlp",
            name="Rete stato del capo (Approccio A)",
            nature="own",
            task="Dalla foto: nuovo / buono / usurato / danneggiato",
            available=COND_W.is_file(),
            weights_path=_rel(COND_W),
            architecture="Fashion-CLIP (frozen) → MLP 512→256→128→4",
            metrics=cond_metrics,
            labels=list(cond_meta.get("labels", [])) or None,
            train_command="uv run python scripts/train_condition_model.py",
        ),
        ModelInfo(
            key="gap-mlp",
            name="Rete gap analysis del guardaroba",
            nature="own",
            task="Dai dati aggregati: vuoti funzionali (multi-label)",
            available=GAP_W.is_file(),
            weights_path=_rel(GAP_W),
            architecture="MLP 14→64→32→6 (sigmoid multi-label)",
            metrics=gap_meta.get("metrics"),
            labels=list(gap_meta.get("labels", [])) or None,
            train_command="uv run python scripts/train_gap_model.py",
        ),
        ModelInfo(
            key="condition-vlm-lora",
            name="VLM + LoRA stato+tutorial (Approccio C)",
            nature="gen",
            task="Dalla foto: stato + tutorial di recupero in JSON",
            available=(ADAPTER_DIR / "adapter_config.json").is_file(),
            weights_path=_rel(ADAPTER_DIR),
            architecture="Qwen2-VL-2B + LoRA r16 (q/k/v/o_proj)",
            metrics=None,
            labels=None,
            train_command="uv run python scripts/train_condition_vlm_pipeline.py",
        ),
    ]

    datasets = [
        DatasetInfo(
            key="garment_condition",
            name="Garment Condition (immagini degradate)",
            available=CONDITION_MANIFEST.is_file(),
            n_samples=_count_csv_rows(CONDITION_MANIFEST),
            detail="4 stati bilanciati · degradazione sintetica su forme reali (FashionMNIST)",
            build_command="uv run python scripts/build_condition_dataset.py --per-class 150",
        ),
        DatasetInfo(
            key="wardrobe",
            name="Wardrobe Gap (tabellare)",
            available=WARDROBE_CSV.is_file(),
            n_samples=_count_csv_rows(WARDROBE_CSV),
            detail="guardaroba simulati · 14 feature · 6 label multi-hot",
            build_command="uv run python scripts/build_wardrobe_dataset.py --rows 5000",
        ),
    ]

    return MlLabStatus(models=models, datasets=datasets)


@router.get("/condition/confusion-matrix")
def get_confusion_matrix() -> FileResponse:
    """Serve la confusion matrix salvata dall'ultimo training della rete stato."""
    if not CONFUSION_MATRIX_PNG.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Confusion matrix non trovata: esegui il training prima.",
        )
    return FileResponse(CONFUSION_MATRIX_PNG, media_type="image/png")


@router.post("/condition/predict", response_model=ConditionPredictOut)
def predict_condition(image: UploadFile = File(...)) -> ConditionPredictOut:
    """Prova interattiva della rete stato: foto → predizione, senza creare item."""
    from app.ml.condition_model import get_condition_classifier

    clf = get_condition_classifier()
    if clf is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Rete stato non addestrata. Esegui: "
                "uv run python scripts/train_condition_model.py"
            ),
        )

    if image.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato non supportato: {image.content_type!r}.",
        )
    payload = image.file.read(MAX_UPLOAD_SIZE + 1)
    if len(payload) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File troppo grande: limite {MAX_UPLOAD_SIZE} byte.",
        )

    # La pipeline di embedding lavora su path: scriviamo un file temporaneo.
    suffix = Path(image.filename or "img.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        pred = clf.predict_from_image(tmp_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Predizione fallita: {e}",
        ) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    return ConditionPredictOut(
        condition=pred.condition,
        confidence=pred.confidence,
        probabilities=pred.probabilities,
    )


@router.post("/gap/predict", response_model=GapPredictOut)
def predict_gap(payload: GapPredictIn) -> GapPredictOut:
    """Simulatore what-if della gap analysis: conteggi → vuoti predetti.

    Usa la rete se addestrata, altrimenti le regole (source lo indica)."""
    from app.ml.gap_model import (
        GAP_HUMAN,
        features_from_counts,
        get_gap_classifier,
        rule_based_gaps,
    )

    feats = features_from_counts(
        payload.counts,
        n_colors=payload.n_colors,
        has_neutral=payload.has_neutral,
        ghost_ratio=payload.ghost_ratio,
    )

    clf = get_gap_classifier()
    if clf is not None:
        try:
            pred = clf.predict(feats)
            return GapPredictOut(
                gaps=pred.gaps,
                labels={c: GAP_HUMAN.get(c, c) for c in pred.gaps},
                probabilities=pred.probabilities,
                balanced=pred.balanced,
                source="neural-net",
            )
        except Exception:
            log.warning("Predizione gap fallita, fallback a regole", exc_info=True)

    gaps = sorted(rule_based_gaps(
        payload.counts,
        n_colors=payload.n_colors,
        has_neutral=payload.has_neutral,
        ghost_ratio=payload.ghost_ratio,
    ))
    return GapPredictOut(
        gaps=gaps,
        labels={c: GAP_HUMAN.get(c, c) for c in gaps},
        probabilities={},
        balanced=len(gaps) == 0,
        source="rules",
    )
