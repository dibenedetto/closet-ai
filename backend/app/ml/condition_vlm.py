"""Inferenza con il VLM fine-tunato in LoRA (Approccio C).

Carica il modello base + l'adapter LoRA addestrato da
``scripts/train_condition_vlm_lora.py`` e, da una foto di capo, produce un
output **strutturato**::

    {"stato": "...", "difetto": "...", "tutorial": "..."}

A differenza dell'Approccio A (`condition_model.py`, che predice solo lo
stato), qui un solo modello produce stato **e** tutorial — combinando il
ruolo vision e quello generativo.

Richiede GPU per essere usabile (il modello 2B su CPU impiega minuti per
generazione). `get_condition_vlm()` ritorna ``None`` se l'adapter non
esiste o le dipendenze mancano, così il backend ricade sugli altri metodi.

Questo modulo è uno **scheletro pronto all'uso**: diventa attivo non appena
l'adapter viene addestrato e i pesi compaiono in
``ml/weights/condition_vlm_lora/``.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import PROJECT_ROOT
from app.ml.condition_model import CONDITION_LABELS

log = logging.getLogger(__name__)

ADAPTER_DIR = Path(
    os.environ.get(
        "CLOSETAI_CONDITION_VLM_ADAPTER",
        str(PROJECT_ROOT / "ml" / "weights" / "condition_vlm_lora"),
    )
)
BASE_MODEL = os.environ.get("CLOSETAI_CONDITION_VLM_BASE", "Qwen/Qwen2-VL-2B-Instruct")

_INSTRUCTION = (
    "Osserva la foto del capo di abbigliamento. Valuta il suo stato di "
    "conservazione (nuovo, buono, usurato o danneggiato) e, se serve, "
    "suggerisci un breve tutorial per migliorarlo. Rispondi in JSON."
)


@dataclass(frozen=True, slots=True)
class VlmDiagnosis:
    condition: str | None
    defect: str | None
    tutorial: str | None
    raw: str


class ConditionVlm:
    """Wrapper attorno al VLM base + adapter LoRA."""

    def __init__(self, adapter_dir: Path = ADAPTER_DIR, base_model: str = BASE_MODEL) -> None:
        self.adapter_dir = adapter_dir
        self.base_model = base_model
        self._model = None
        self._processor = None

    def is_available(self) -> bool:
        if not (self.adapter_dir / "adapter_config.json").is_file():
            return False
        try:
            import peft  # noqa: F401
            import qwen_vl_utils  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from peft import PeftModel
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        log.info("Carico VLM base %s + adapter LoRA %s", self.base_model, self.adapter_dir)
        base = Qwen2VLForConditionalGeneration.from_pretrained(
            self.base_model,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        self._model = PeftModel.from_pretrained(base, str(self.adapter_dir))
        self._model.eval()
        self._processor = AutoProcessor.from_pretrained(str(self.adapter_dir))

    def diagnose(self, image_path: str | Path) -> VlmDiagnosis:
        import torch
        from qwen_vl_utils import process_vision_info

        self._ensure_loaded()
        assert self._model is not None
        assert self._processor is not None

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": _INSTRUCTION},
                ],
            }
        ]
        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, _ = process_vision_info(messages)
        inputs = self._processor(
            text=[text], images=image_inputs, return_tensors="pt", padding=True
        ).to(self._model.device)

        with torch.no_grad():
            generated = self._model.generate(**inputs, max_new_tokens=256, do_sample=False)
        trimmed = generated[:, inputs["input_ids"].shape[1]:]
        raw = self._processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        return _parse(raw)


def _normalize_condition(value: object) -> str | None:
    """Valida che lo stato sia una delle 4 etichette ammesse, altrimenti None.

    Il VLM può produrre varianti (maiuscole, sinonimi); normalizziamo. Se lo
    stato non è riconoscibile, ritorniamo None così il chiamante può fare
    fallback su un backend più affidabile."""
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    if v in CONDITION_LABELS:
        return v
    # sinonimi comuni che il VLM potrebbe restituire
    synonyms = {
        "ottimo": "nuovo",
        "come nuovo": "nuovo",
        "discreto": "buono",
        "consumato": "usurato",
        "rovinato": "danneggiato",
        "rotto": "danneggiato",
    }
    return synonyms.get(v)


def _parse(raw: str) -> VlmDiagnosis:
    """Estrae e valida il JSON dalla generazione, robusto a preamboli/code-fence."""
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            condition = _normalize_condition(data.get("stato"))
            defect = data.get("difetto")
            tutorial = data.get("tutorial")
            return VlmDiagnosis(
                condition=condition,
                defect=defect if isinstance(defect, str) and defect.strip() else None,
                tutorial=tutorial if isinstance(tutorial, str) and tutorial.strip() else None,
                raw=raw,
            )
    log.warning("Output VLM non parsabile come JSON valido: %r", raw[:200])
    return VlmDiagnosis(condition=None, defect=None, tutorial=None, raw=raw)


@lru_cache(maxsize=1)
def get_condition_vlm() -> ConditionVlm | None:
    """Singleton. ``None`` se l'adapter non è addestrato o le deps mancano."""
    vlm = ConditionVlm()
    if not vlm.is_available():
        return None
    return vlm


def reset_condition_vlm_cache() -> None:
    get_condition_vlm.cache_clear()
