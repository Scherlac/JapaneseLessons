from __future__ import annotations

from typing import Any, Protocol

from .spike_data_model import CanonicalNodeRecord, SearchHit


class EmbeddingProvider(Protocol):
    """Embedding provider contract for spike comparability."""

    model_name: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class VectorStore(Protocol):
    """Vector store contract for backend-neutral spike implementations."""

    backend_name: str

    def reset(self) -> None:
        """Clear existing collection/index state for deterministic runs."""
        ...

    def upsert(
        self,
        records: list[CanonicalNodeRecord],
        embeddings: list[list[float]],
    ) -> None:
        """Upsert records + embeddings into the vector store."""
        ...

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Query nearest neighbors with optional metadata filter."""
        ...
