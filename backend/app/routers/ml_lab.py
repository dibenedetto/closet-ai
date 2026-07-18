"""Endpoint per la pagina tecnica ML Lab.

Espone lo stato di **training / test / eval** delle reti addestrate da noi
(rete stato del capo, rete gap analysis) e due endpoint di prova
interattiva usati dal frontend:

- ``POST /ml/condition/predict`` — foto → stato predetto (senza creare item)
- ``POST /ml/gap/predict``       — conteggi simulati → vuoti predetti
- ``GET /ml/notebooks/{key}``    — scarica uno dei due notebook runtime
- ``POST /ml/notebooks/{key}/open`` — apre localmente il notebook in VS Code

Tutto in sola lettura rispetto al DB: la pagina serve a *ispezionare e
provare* i modelli, non a modificare il guardaroba.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.config import ALLOWED_IMAGE_CONTENT_TYPES, MAX_UPLOAD_SIZE, PROJECT_ROOT
from app.schemas.ml_lab import (
    ConditionPredictOut,
    DatasetInfo,
    GapPredictIn,
    GapPredictOut,
    MlLabStatus,
    ModelInfo,
    NotebookOpenOut,
)

router = APIRouter(prefix="/ml", tags=["ml-lab"])
log = logging.getLogger(__name__)

CONFUSION_MATRIX_PNG = (
    PROJECT_ROOT / "ml" / "datasets" / "garment_condition" / "condition_confusion_matrix.png"
)
CONDITION_MANIFEST = PROJECT_ROOT / "ml" / "datasets" / "garment_condition" / "manifest.csv"
WARDROBE_CSV = PROJECT_ROOT / "ml" / "datasets" / "wardrobe" / "wardrobe_dataset.csv"
MODEL_NOTEBOOKS: dict[str, Path] = {
    "condition-mlp": PROJECT_ROOT / "ml" / "notebooks" / "exam" / "01_condition_state_mlp.ipynb",
    "gap-mlp": PROJECT_ROOT / "ml" / "notebooks" / "exam" / "02_wardrobe_gap_mlp.ipynb",
}


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


def _count_csv_rows(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)  # meno l'header
    except Exception:
        return None


def _notebook_for(model_key: str) -> Path:
    """Restituisce soltanto uno dei due notebook esplicitamente consentiti."""
    notebook = MODEL_NOTEBOOKS.get(model_key)
    if notebook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook non associato a questo modello.",
        )
    if not notebook.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notebook non trovato: {notebook.name}.",
        )
    return notebook


def _is_loopback_request(request: Request) -> bool:
    """L'apertura di applicazioni desktop è ammessa solo dal computer locale."""
    if request.client is None:
        return False
    host = request.client.host
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _find_vscode() -> Path | None:
    """Trova VS Code da variabili d'ambiente, PATH o installazioni comuni."""
    configured = os.environ.get("CLOSETAI_VSCODE_PATH")
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())

    for command in ("code", "code-insiders", "codium"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))

    if os.name == "nt":
        for base_var in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = os.environ.get(base_var)
            if base:
                candidates.extend([
                    Path(base) / "Programs" / "Microsoft VS Code" / "Code.exe",
                    Path(base) / "Microsoft VS Code" / "Code.exe",
                ])

    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _launch_notebook(notebook: Path) -> str:
    """Apre il notebook in VS Code oppure nell'app predefinita del sistema."""
    vscode = _find_vscode()
    if vscode is not None:
        command: list[str]
        if os.name == "nt" and vscode.suffix.lower() in {".cmd", ".bat"}:
            command = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d", "/c", str(vscode), "--reuse-window", str(notebook),
            ]
        else:
            command = [str(vscode), "--reuse-window", str(notebook)]
        subprocess.Popen(  # noqa: S603 - executable e file provengono da allowlist locale
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return "Visual Studio Code"

    if os.name == "nt":
        os.startfile(notebook)  # type: ignore[attr-defined]
        return "applicazione predefinita"

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    executable = shutil.which(opener)
    if executable is None:
        raise OSError("Nessun editor compatibile trovato")
    subprocess.Popen(  # noqa: S603 - opener di sistema e file in allowlist
        [executable, str(notebook)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return "applicazione predefinita"


@router.get("/models", response_model=MlLabStatus)
def get_models_status() -> MlLabStatus:
    """Stato + metriche delle reti addestrate da noi e dei loro dataset."""
    from app.ml.condition_model import WEIGHTS_PATH as COND_W
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
            name="Rete per lo stato del capo",
            nature="own",
            task="Dalla foto: buono / usurato / danneggiato",
            available=COND_W.is_file(),
            architecture="Fashion-CLIP pre-addestrato → rete neurale a 3 classi",
            metrics=cond_metrics,
            labels=list(cond_meta.get("labels", [])) or None,
            notebook_filename=MODEL_NOTEBOOKS["condition-mlp"].name,
            notebook_available=MODEL_NOTEBOOKS["condition-mlp"].is_file(),
        ),
        ModelInfo(
            key="gap-mlp",
            name="Rete gap analysis del guardaroba",
            nature="own",
            task="Dai dati aggregati: vuoti funzionali (multi-label)",
            available=GAP_W.is_file(),
            architecture="14 indicatori del guardaroba → rete neurale → 6 possibili gap",
            metrics=gap_meta.get("metrics"),
            labels=list(gap_meta.get("labels", [])) or None,
            notebook_filename=MODEL_NOTEBOOKS["gap-mlp"].name,
            notebook_available=MODEL_NOTEBOOKS["gap-mlp"].is_file(),
        ),
    ]

    datasets = [
        DatasetInfo(
            key="garment_condition",
            name="Dataset per lo stato dei capi",
            available=CONDITION_MANIFEST.is_file(),
            n_samples=_count_csv_rows(CONDITION_MANIFEST),
            detail="3 stati bilanciati · foto reali con difetti annotati (COCO) + degradazione sintetica",
        ),
        DatasetInfo(
            key="wardrobe",
            name="Dataset per i gap del guardaroba",
            available=WARDROBE_CSV.is_file(),
            n_samples=_count_csv_rows(WARDROBE_CSV),
            detail="guardaroba simulati · 14 feature · 6 label multi-hot",
        ),
    ]

    return MlLabStatus(models=models, datasets=datasets)


@router.get("/notebooks/{model_key}")
def get_training_notebook(model_key: str) -> FileResponse:
    """Scarica il notebook di training associato a uno dei modelli runtime."""
    notebook = _notebook_for(model_key)
    return FileResponse(
        notebook,
        media_type="application/x-ipynb+json",
        filename=notebook.name,
    )


@router.post("/notebooks/{model_key}/open", response_model=NotebookOpenOut)
def open_training_notebook(model_key: str, request: Request) -> NotebookOpenOut:
    """Apre localmente il notebook; non accetta richieste provenienti dalla LAN."""
    if not _is_loopback_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Per sicurezza il notebook può essere aperto soltanto da localhost.",
        )
    notebook = _notebook_for(model_key)
    try:
        application = _launch_notebook(notebook)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Editor non trovato. Usa il collegamento per scaricare il file .ipynb.",
        ) from exc
    return NotebookOpenOut(
        opened=True,
        application=application,
        filename=notebook.name,
        message=f"{notebook.name} aperto in {application}.",
    )


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
            detail="Il modello per lo stato del capo non è disponibile.",
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
