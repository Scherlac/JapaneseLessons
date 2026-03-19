from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CanonicalMetadata(BaseModel):
    """Storage-friendly metadata for canonical nodes.

    Uses flat scalar fields so records are compatible with vector stores and SQL.
    """

    theme: str
    level: str = "beginner"
    concept_type: str
    language_scope: str = "eng-jap"
    grammar_progression_ja: str = ""

    def to_storage_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "level": self.level,
            "concept_type": self.concept_type,
            "language_scope": self.language_scope,
            "grammar_progression.ja": self.grammar_progression_ja,
        }


class CanonicalNodeRecord(BaseModel):
    """Canonical English record for vector indexing."""

    node_id: str
    canonical_text_en: str
    metadata: CanonicalMetadata

    def to_document(self) -> str:
        return self.canonical_text_en


class RetrievalQuery(BaseModel):
    """Benchmark query with optional metadata filter for spike 2 reuse."""

    query_id: str
    query_text: str
    query_type: str
    expected_ids: list[str] = Field(default_factory=list)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)


class SearchHit(BaseModel):
    """Vector-search result for downstream metric computation."""

    node_id: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpikeResult(BaseModel):
    """Result payload contract for spike outputs."""

    spike: str
    embedding_model: str
    vector_store: str
    timestamp_utc: str
    corpus_size: int
    query_count: int
    latency_ms: dict[str, float]
    precision_at_k: dict[str, float]
    timing: dict[str, float] = Field(default_factory=dict)
    sample_results: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""
