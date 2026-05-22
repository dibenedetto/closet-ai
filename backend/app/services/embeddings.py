"""Wrapper ChromaDB per gli embedding 512d dei capi.

ChromaDB è usato in modalità *persistente* su filesystem (vedi `CHROMA_DIR`),
con una singola collection `items` indicizzata per `id` SQLite.

La verità per i metadata resta in SQLite (`Item`); ChromaDB è un indice
secondario usato per le query di similarità (Fase 4 — recommender). Le
operazioni mutanti su `Item` (`POST`, `DELETE`, `reclassify`) chiamano
esplicitamente questo wrapper per mantenere l'allineamento.

Vedi `docs/architecture.md` (ADR-004) per la motivazione.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from app.config import CHROMA_DIR

log = logging.getLogger(__name__)


class EmbeddingStore:
    """Operazioni essenziali sulla collection ChromaDB di ClosetAI."""

    COLLECTION_NAME = "items"

    def __init__(self, persist_dir: Path) -> None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        # Settings minime: disabilito telemetria anonima per non far partire
        # connessioni di rete (questo è un prototipo single-user locale).
        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(self.COLLECTION_NAME)

    def upsert(
        self,
        item_id: int,
        embedding: Sequence[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # ChromaDB rifiuta metadata None; lo normalizziamo a dict vuoto.
        meta = {k: v for k, v in (metadata or {}).items() if v is not None}
        self._collection.upsert(
            ids=[str(item_id)],
            embeddings=[list(embedding)],
            metadatas=[meta] if meta else None,
        )

    def delete(self, item_id: int) -> None:
        try:
            self._collection.delete(ids=[str(item_id)])
        except Exception:
            log.warning("Errore eliminazione embedding item=%s", item_id, exc_info=True)

    def query_similar(
        self, embedding: Sequence[float], k: int = 5
    ) -> list[tuple[int, float]]:
        """Ritorna lista di `(item_id, similarity)` ordinata per similarità desc."""
        res = self._collection.query(query_embeddings=[list(embedding)], n_results=k)
        ids = (res.get("ids") or [[]])[0]
        distances = (res.get("distances") or [[]])[0]
        # ChromaDB di default usa la distanza L2 quadratica; convertiamo in
        # similarità "1 / (1 + dist)" — basta per ordinare, non è una cosine.
        return [(int(i), 1.0 / (1.0 + float(d))) for i, d in zip(ids, distances)]

    def count(self) -> int:
        return int(self._collection.count())


@lru_cache(maxsize=1)
def get_embedding_store() -> EmbeddingStore:
    return EmbeddingStore(CHROMA_DIR)


def reset_embedding_store_cache() -> None:
    """Resetta il singleton — usato dai test per puntare a una persist_dir isolata."""
    get_embedding_store.cache_clear()
