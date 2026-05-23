"""Try-on virtuale tramite diffusion model.

Architettura **backend-pluggable**: la classe astratta `TryOnBackend`
dichiara l'interfaccia, e le implementazioni concrete possono usare modelli
locali (`DiffusersLocalBackend`, default), endpoint cloud (HF Inference API,
Replicate, ecc.), o tornare semplicemente un placeholder.

Scelta del backend tramite `CLOSETAI_TRYON_BACKEND`:

- `disabled` (default) — endpoint risponde 503: niente download di pesi
  senza richiesta esplicita.
- `diffusers` — carica `CLOSETAI_TRYON_MODEL` (default Stable Diffusion 2
  inpainting, ~5 GB) e fa l'inferenza in locale. Lento su CPU (minuti per
  immagine); accettabile come demo.

Approccio MVP (non IDM-VTON vero):

1. Carichiamo il ritratto dell'utente in alta risoluzione.
2. Costruiamo una maschera "torso" automatica (rettangolo centrale che
   copre approssimativamente la zona busto).
3. Lanciamo lo Stable Diffusion **inpainting** con un prompt che descrive
   il capo (categoria + colore + nome).

È un compromise consapevole: l'illusione del try-on funziona in demo, non
sostituisce un vero modello try-on garment-aware. Vedi ADR-007 in
`docs/architecture.md` per la roadmap.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from app.config import TRYON_BACKEND, TRYON_DIR, TRYON_MODEL

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TryOnResult:
    filename: str
    backend: str
    prompt: str
    elapsed_ms: int


class TryOnBackend(ABC):
    name: str = "abstract"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def generate(
        self,
        portrait: Image.Image,
        garment: Image.Image,
        *,
        prompt: str,
        negative_prompt: str | None = None,
    ) -> Image.Image:
        """Sintetizza un'immagine del soggetto che indossa il capo."""


# ---------------------------------------------------------------------------
# Disabled backend (default in test e quando il modello non è scaricato)
# ---------------------------------------------------------------------------


class DisabledBackend(TryOnBackend):
    name = "disabled"

    def is_available(self) -> bool:
        return False

    def generate(self, *_a, **_kw):  # pragma: no cover
        raise RuntimeError("try-on backend disabilitato")


# ---------------------------------------------------------------------------
# Diffusers locale
# ---------------------------------------------------------------------------


class DiffusersLocalBackend(TryOnBackend):
    """Wrapper attorno a `diffusers.StableDiffusionInpaintPipeline`.

    Modello caricato lazy al primo `generate()`. Su CPU una singola immagine
    impiega 30s-3min; su GPU CUDA pochi secondi.
    """

    name = "diffusers"

    def __init__(self, model_id: str = TRYON_MODEL) -> None:
        self.model_id = model_id
        self._pipe = None

    def is_available(self) -> bool:
        try:
            import diffusers  # noqa: F401
            import torch  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_loaded(self) -> None:
        if self._pipe is not None:
            return
        import torch
        from diffusers import StableDiffusionInpaintPipeline

        log.info("Carico pipeline try-on (%s) — primo run scarica i pesi", self.model_id)
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            safety_checker=None,  # demo: niente safety checker (lento + falsi positivi)
            requires_safety_checker=False,
        )
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        else:
            pipe = pipe.to("cpu")
            # Optimization specifica CPU: riduce uso RAM.
            try:
                pipe.enable_attention_slicing()
            except AttributeError:
                pass
        self._pipe = pipe

    def generate(
        self,
        portrait: Image.Image,
        garment: Image.Image,
        *,
        prompt: str,
        negative_prompt: str | None = None,
    ) -> Image.Image:
        self._ensure_loaded()
        assert self._pipe is not None

        # Resize a 512x512 mantenendo l'aspect: SD2 inpainting è tarato lì.
        target_size = 512
        rgb = portrait.convert("RGB")
        rgb.thumbnail((target_size, target_size), Image.LANCZOS)
        # Pad a 512x512 con sfondo nero per soddisfare il modello.
        canvas = Image.new("RGB", (target_size, target_size), (0, 0, 0))
        offset = (
            (target_size - rgb.width) // 2,
            (target_size - rgb.height) // 2,
        )
        canvas.paste(rgb, offset)

        # Maschera "torso": rettangolo centrale dal 30% al 75% dell'altezza,
        # dal 15% all'85% della larghezza. È un'euristica grezza ma sufficiente
        # come MVP. Per un try-on vero servirebbe una segmentazione del corpo.
        mask = Image.new("L", (target_size, target_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle(
            (
                int(target_size * 0.15),
                int(target_size * 0.30),
                int(target_size * 0.85),
                int(target_size * 0.75),
            ),
            fill=255,
        )

        _ = garment  # il garment vero non viene passato al modello inpaint; serve
        # solo a popolare il prompt testuale dal chiamante.

        result = self._pipe(
            prompt=prompt,
            negative_prompt=negative_prompt
            or "blurry, deformed, low quality, watermark, text, extra limbs",
            image=canvas,
            mask_image=mask,
            num_inference_steps=20,
            guidance_scale=7.5,
        )
        return result.images[0]


# ---------------------------------------------------------------------------
# Factory + entry point
# ---------------------------------------------------------------------------


_INSTANCE: TryOnBackend | None = None


def get_backend() -> TryOnBackend:
    global _INSTANCE
    if _INSTANCE is not None:
        return _INSTANCE
    selected = TRYON_BACKEND.lower().strip()
    if selected == "diffusers":
        backend: TryOnBackend = DiffusersLocalBackend()
        if not backend.is_available():
            log.warning("Backend diffusers non disponibile, fallback a disabled")
            backend = DisabledBackend()
    else:
        backend = DisabledBackend()
    _INSTANCE = backend
    return backend


def reset_backend_cache() -> None:
    """Esposta per i test."""
    global _INSTANCE
    _INSTANCE = None


def build_prompt(item_name: str, category: str | None, color: str | None) -> str:
    parts: list[str] = []
    if color:
        parts.append(color)
    if category:
        parts.append(category)
    if not parts:
        parts.append(item_name)
    descriptor = " ".join(parts)
    return (
        f"a photorealistic portrait of a person wearing a {descriptor}, "
        "studio lighting, soft shadows, high detail, sharp focus"
    )


def run_tryon(
    portrait_bytes: bytes,
    garment_path: Path,
    *,
    item_name: str,
    category: str | None,
    color: str | None,
) -> TryOnResult:
    """Pipeline completa: legge il ritratto, genera, salva su TRYON_DIR.

    Solleva `RuntimeError` se il backend non è attivo (lasciamo che il
    router lo traduca in HTTP 503).
    """
    import time

    backend = get_backend()
    if not backend.is_available():
        raise RuntimeError(
            f"Try-on backend '{TRYON_BACKEND}' non disponibile. Imposta "
            "CLOSETAI_TRYON_BACKEND=diffusers e installa i pesi del modello."
        )

    portrait = Image.open(BytesIO(portrait_bytes)).convert("RGB")
    garment = Image.open(garment_path).convert("RGB")
    prompt = build_prompt(item_name, category, color)

    TRYON_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    out_path = TRYON_DIR / filename

    started = time.time()
    out_image = backend.generate(portrait, garment, prompt=prompt)
    elapsed_ms = int((time.time() - started) * 1000)
    out_image.save(out_path, format="PNG")

    return TryOnResult(
        filename=filename, backend=backend.name, prompt=prompt, elapsed_ms=elapsed_ms
    )
