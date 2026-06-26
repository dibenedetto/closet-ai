"""Gateway unificato per i Large Language Model.

Usa **litellm** come livello d'astrazione: la stessa funzione `generate()`
parla con Claude API, OpenAI, Ollama locale (`ollama/llama3`), vLLM, ecc.
Il provider è scelto dalla forma del nome modello in `CLOSETAI_LLM_MODEL`:

| Modello configurato                  | Provider              | Credenziali necessarie         |
| ------------------------------------ | --------------------- | ------------------------------ |
| `claude-haiku-4-5` (default)         | Anthropic API         | `ANTHROPIC_API_KEY`            |
| `claude-sonnet-4-6`                  | Anthropic API         | `ANTHROPIC_API_KEY`            |
| `openai/gpt-4o-mini`                 | OpenAI API            | `OPENAI_API_KEY`               |
| `ollama/llama3.2`                    | Ollama locale         | `OLLAMA_API_BASE` (default :11434) |
| `huggingface/Qwen/Qwen2.5-7B-Instruct` | HF Inference        | `HUGGINGFACE_API_KEY`          |

Se la chiamata fallisce (no credenziali, network down, modello locale non
servito), `generate()` ritorna `None` e il chiamante deve avere un
fallback. Vedi ADR-008 in `docs/architecture.md`.

Caching: ogni risposta viene salvata in tabella `llm_cache` con TTL
configurabile (default 24h). Lo stesso prompt non viene rigenerato finché
non scade.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import LLM_CACHE_TTL_HOURS, LLM_MAX_TOKENS, LLM_MODEL, LLM_TIMEOUT
from app.models import LlmCache

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LlmResult:
    text: str
    model: str
    cached: bool
    latency_ms: int | None


def _cache_key(model: str, system: str | None, user: str) -> str:
    payload = json.dumps(
        {"model": model, "system": system or "", "user": user},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_lookup(db: Session, key: str) -> str | None:
    now = datetime.now(timezone.utc)
    row = db.execute(select(LlmCache).where(LlmCache.cache_key == key)).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at is not None:
        # SQLite restituisce datetime naive; normalizziamo a UTC-aware.
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            db.delete(row)
            db.commit()
            return None
    return row.response


def _cache_store(db: Session, key: str, model: str, response: str) -> None:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=LLM_CACHE_TTL_HOURS)
    # Idempotente: una riga per cache_key.
    db.execute(delete(LlmCache).where(LlmCache.cache_key == key))
    db.add(
        LlmCache(
            cache_key=key,
            model=model,
            response=response,
            created_at=now,
            expires_at=expires,
        )
    )
    db.commit()


def is_llm_configured(model: str | None = None) -> bool:
    """True se il modello configurato sembra invocabile. Heuristic:

    - Anthropic: serve `ANTHROPIC_API_KEY`.
    - OpenAI: serve `OPENAI_API_KEY`.
    - Ollama: non serve key (ma il daemon deve essere up).
    - Altri: assumiamo configurato se la model string non è vuota.
    """
    import os

    name = (model or LLM_MODEL).lower()
    if "claude" in name or name.startswith("anthropic/"):
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if name.startswith("openai/") or name.startswith("gpt-"):
        return bool(os.environ.get("OPENAI_API_KEY"))
    if name.startswith("ollama/"):
        return True  # Ollama non richiede API key; il chiamante gestisce il timeout
    if name.startswith("huggingface/"):
        return bool(os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN"))
    return bool(name)


def generate(
    user: str,
    *,
    system: str | None = None,
    db: Session | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    use_cache: bool = True,
    extra: dict[str, Any] | None = None,
) -> LlmResult | None:
    """Genera testo via il provider configurato. Ritorna `None` su errore."""
    model_name = model or LLM_MODEL
    if not is_llm_configured(model_name):
        log.info(
            "LLM non configurato (%s): nessuna credenziale rilevata", model_name
        )
        return None

    key = _cache_key(model_name, system, user)
    if use_cache and db is not None:
        cached = _cache_lookup(db, key)
        if cached is not None:
            return LlmResult(text=cached, model=model_name, cached=True, latency_ms=None)

    # Import differito: litellm è pesante e non vogliamo caricarlo se non serve.
    try:
        import litellm
    except ImportError:
        log.warning("litellm non disponibile")
        return None

    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    started = datetime.now(timezone.utc)
    try:
        response = litellm.completion(  # type: ignore[no-untyped-call]
            model=model_name,
            messages=messages,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
            timeout=LLM_TIMEOUT,
            **(extra or {}),
        )
    except Exception as e:
        log.warning("Errore LLM (%s): %s", model_name, e)
        return None

    latency_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    try:
        text = response.choices[0].message.content or ""
    except Exception:
        log.warning("Risposta LLM in formato inatteso: %r", response)
        return None
    text = text.strip()
    if not text:
        return None

    if use_cache and db is not None:
        _cache_store(db, key, model_name, text)

    return LlmResult(text=text, model=model_name, cached=False, latency_ms=latency_ms)


def generate_vision(
    image_path: str,
    user: str,
    *,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> str | None:
    """Genera testo a partire da **immagine + prompt** (modello multimodale).

    Usa il formato multimodale di litellm (compatibile OpenAI): l'immagine è
    inviata come data-URL base64. Funziona con i VLM cloud (Claude, GPT-4o) e
    locali (es. `ollama/llava`, `ollama/qwen2-vl`). Ritorna `None` su errore.

    Usato per la **distillazione** dei tutorial: un VLM grande guarda la foto
    e scrive un tutorial personalizzato (vedi `scripts/distill_tutorials.py`).
    """
    import base64
    import mimetypes
    from pathlib import Path as _Path

    model_name = model or LLM_MODEL
    if not is_llm_configured(model_name):
        log.info("VLM non configurato (%s)", model_name)
        return None

    p = _Path(image_path)
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    try:
        import litellm
    except ImportError:
        return None

    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    )

    try:
        response = litellm.completion(  # type: ignore[no-untyped-call]
            model=model_name,
            messages=messages,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
            timeout=LLM_TIMEOUT,
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception as e:
        log.warning("Errore VLM (%s): %s", model_name, e)
        return None


def generate_json(
    user: str,
    *,
    schema_hint: str,
    system: str | None = None,
    db: Session | None = None,
    model: str | None = None,
) -> dict | None:
    """Variante che chiede output JSON e lo parsa. Best-effort: se il modello
    rispnode con preambolo, estraiamo il blocco `{...}`."""
    full_system = (system or "") + (
        "\n\nRispondi *solo* con JSON valido, senza testo extra né code fence."
        f"\nSchema atteso:\n{schema_hint}"
    )
    result = generate(user, system=full_system, db=db, model=model)
    if result is None:
        return None
    text = result.text
    # Strip eventuali ``` code fences
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    # Trova il primo `{` e l'ultimo `}` (heuristic robusta)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        log.warning("Risposta non sembra JSON: %r", text[:200])
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        log.warning("JSON parse error: %s — payload: %r", e, text[:200])
        return None
