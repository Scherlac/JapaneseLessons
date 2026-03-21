from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CanonicalMetadata(BaseModel):
    """Flat scalar metadata aligned with the vector-indexing spike."""

    theme: str = ""
    level: str = "beginner"
    concept_type: str = ""
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

    @classmethod
    def from_storage_dict(cls, metadata: dict[str, Any]) -> "CanonicalMetadata":
        return cls(
            theme=str(metadata.get("theme", "")),
            level=str(metadata.get("level", "beginner")),
            concept_type=str(metadata.get("concept_type", "")),
            language_scope=str(metadata.get("language_scope", "eng-jap")),
            grammar_progression_ja=str(metadata.get("grammar_progression.ja", "")),
        )


class CanonicalLessonNode(BaseModel):
    """Canonical English lesson material node."""

    node_id: str
    canonical_text_en: str
    concept_type: str = ""
    metadata_tags: dict[str, str] = Field(default_factory=dict)
    metadata: CanonicalMetadata | None = None
    embedding_version: str = ""
    source_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _populate_metadata(self) -> "CanonicalLessonNode":
        if self.metadata is None:
            self.metadata = CanonicalMetadata(
                theme=self.metadata_tags.get("theme", ""),
                level=self.metadata_tags.get("level", "beginner"),
                concept_type=self.concept_type or self.metadata_tags.get("concept_type", ""),
                language_scope=self.metadata_tags.get("language_scope", "eng-jap"),
                grammar_progression_ja=self.metadata_tags.get("grammar_progression.ja", ""),
            )
        if not self.concept_type:
            self.concept_type = self.metadata.concept_type
        if not self.metadata_tags:
            self.metadata_tags = {
                key: str(value)
                for key, value in self.metadata.to_storage_dict().items()
                if value != ""
            }
        return self

    def to_document(self) -> str:
        return self.canonical_text_en

    def to_storage_metadata(self) -> dict[str, Any]:
        data = self.metadata.to_storage_dict() if self.metadata is not None else {}
        for key, value in self.metadata_tags.items():
            data.setdefault(key, value)
        return data


class LanguageBranch(BaseModel):
    """Localized branch payload attached to a canonical node."""

    node_id: str
    language_code: str
    payload: dict[str, Any] = Field(default_factory=dict)
    pronunciation: str = ""
    notes: str = ""
    branch_quality: str = ""
    examples: list[str] = Field(default_factory=list)


class RetrievalQuery(BaseModel):
    """Production query contract aligned with the spike query model."""

    query_id: str = ""
    query_text: str
    query_type: str = "lesson_lookup"
    expected_ids: list[str] = Field(default_factory=list)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)


class SearchHit(BaseModel):
    """Search result shape used internally by retrieval backends."""

    node_id: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalCandidate(BaseModel):
    """One ranked retrieval candidate projected into a branch payload."""

    node_id: str
    concept_type: str
    canonical_text_en: str
    language_code: str = ""
    score: float = 0.0
    metadata_tags: dict[str, Any] = Field(default_factory=dict)
    source_payload: dict[str, Any] = Field(default_factory=dict)
    branch_payload: dict[str, Any] = Field(default_factory=dict)


class RetrievedLessonMaterial(BaseModel):
    """Pipeline-friendly lesson material assembled from retrieval results."""

    nouns: list[dict[str, Any]] = Field(default_factory=list)
    verbs: list[dict[str, Any]] = Field(default_factory=list)
    sentences: list[dict[str, Any]] = Field(default_factory=list)
    grammar_ids: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """Envelope returned by the retrieval service."""

    query: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)
    requested_language: str = ""
    candidates: list[RetrievalCandidate] = Field(default_factory=list)
    material: RetrievedLessonMaterial = Field(default_factory=RetrievedLessonMaterial)
    coverage: float = 0.0
    fallback_reason: str = ""
    used_retrieval: bool = False


class RetrievalService(ABC):
    """Boundary for lesson material retrieval."""

    @abstractmethod
    def ingest_canonical_node(self, node: CanonicalLessonNode) -> None:
        """Insert or update a canonical node."""

    @abstractmethod
    def attach_branch(self, branch: LanguageBranch) -> None:
        """Insert or update a language branch linked to a canonical node."""

    @abstractmethod
    def search(
        self,
        query: str | RetrievalQuery,
        *,
        requested_language: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        """Search canonical nodes and project the requested branch payload."""


class NoOpRetrievalService(RetrievalService):
    """Safe fallback implementation that never returns retrieval material."""

    def __init__(self, reason: str = "retrieval disabled"):
        self.reason = reason

    def ingest_canonical_node(self, node: CanonicalLessonNode) -> None:
        return None

    def attach_branch(self, branch: LanguageBranch) -> None:
        return None

    def search(
        self,
        query: str | RetrievalQuery,
        *,
        requested_language: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        normalized_query = _normalize_query(query, filters)
        return RetrievalResult(
            query=normalized_query.query_text,
            filters=normalized_query.metadata_filter,
            requested_language=requested_language,
            fallback_reason=self.reason,
        )


class _RetrievalStore(BaseModel):
    nodes: list[CanonicalLessonNode] = Field(default_factory=list)
    branches: list[LanguageBranch] = Field(default_factory=list)


class _StoreBackedRetrievalService(RetrievalService):
    def __init__(self, store_path: Path | str):
        self.store_path = Path(store_path)

    def ingest_canonical_node(self, node: CanonicalLessonNode) -> None:
        store = self._load_store()
        store.nodes = [existing for existing in store.nodes if existing.node_id != node.node_id]
        store.nodes.append(node)
        self._save_store(store)

    def attach_branch(self, branch: LanguageBranch) -> None:
        store = self._load_store()
        if not any(node.node_id == branch.node_id for node in store.nodes):
            raise ValueError(
                f"Cannot attach branch to unknown canonical node {branch.node_id!r}"
            )
        store.branches = [
            existing
            for existing in store.branches
            if not (
                existing.node_id == branch.node_id
                and existing.language_code == branch.language_code
            )
        ]
        store.branches.append(branch)
        self._save_store(store)

    def _load_store(self) -> _RetrievalStore:
        if not self.store_path.exists():
            return _RetrievalStore()
        return _RetrievalStore.model_validate_json(
            self.store_path.read_text(encoding="utf-8")
        )

    def _save_store(self, store: _RetrievalStore) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            store.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

    def _branches_by_key(self, store: _RetrievalStore) -> dict[tuple[str, str], LanguageBranch]:
        return {(branch.node_id, branch.language_code): branch for branch in store.branches}

    def _build_result(
        self,
        query: RetrievalQuery,
        requested_language: str,
        candidates: list[RetrievalCandidate],
    ) -> RetrievalResult:
        material = RetrievedLessonMaterial()
        grammar_ids: list[str] = []
        for candidate in candidates:
            raw_item = self._merge_payload(candidate)
            concept_type = _normalize_concept_type(candidate.concept_type)
            if concept_type == "noun":
                material.nouns.append(raw_item)
            elif concept_type == "verb":
                material.verbs.append(raw_item)
            elif concept_type == "sentence":
                material.sentences.append(raw_item)
                grammar_id = str(
                    raw_item.get("grammar_id")
                    or candidate.metadata_tags.get("grammar_id", "")
                )
                if grammar_id and grammar_id not in grammar_ids:
                    grammar_ids.append(grammar_id)

        material.grammar_ids = grammar_ids
        fallback_reason = ""
        if not candidates:
            fallback_reason = "no retrieval candidates matched query and filters"

        return RetrievalResult(
            query=query.query_text,
            filters=query.metadata_filter,
            requested_language=requested_language,
            candidates=candidates,
            material=material,
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _merge_payload(candidate: RetrievalCandidate) -> dict[str, Any]:
        raw_item = dict(candidate.source_payload)
        raw_item.update(candidate.branch_payload)
        raw_item.setdefault("english", candidate.canonical_text_en)
        return raw_item


class FileBackedRetrievalService(_StoreBackedRetrievalService):
    """JSON-backed retrieval store for the first production-safe slice."""

    def search(
        self,
        query: str | RetrievalQuery,
        *,
        requested_language: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        normalized_query = _normalize_query(query, filters)
        store = self._load_store()
        branches = self._branches_by_key(store)
        candidates: list[RetrievalCandidate] = []

        for node in store.nodes:
            storage_metadata = node.to_storage_metadata()
            if not _matches_metadata(storage_metadata, normalized_query.metadata_filter):
                continue

            branch = branches.get((node.node_id, requested_language))
            if branch is None:
                continue

            score = _lexical_score_candidate(node, normalized_query)
            if score <= 0:
                continue

            candidates.append(
                RetrievalCandidate(
                    node_id=node.node_id,
                    concept_type=node.concept_type,
                    canonical_text_en=node.canonical_text_en,
                    language_code=requested_language,
                    score=score,
                    metadata_tags=storage_metadata,
                    source_payload=node.source_payload,
                    branch_payload=branch.payload,
                )
            )

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return self._build_result(normalized_query, requested_language, candidates[:limit])


class ChromaVectorRetrievalService(_StoreBackedRetrievalService):
    """Optional Chroma-backed vector retrieval aligned with the spike adapter shape."""

    backend_name = "chroma_local_persistent"

    def __init__(
        self,
        store_path: Path | str,
        *,
        persist_path: Path | str | None = None,
        collection_name: str = "jlesson_retrieval",
        embedding_model: str = "text-embedding-3-small",
    ):
        super().__init__(store_path)
        self.persist_path = Path(persist_path) if persist_path is not None else self.store_path.with_suffix("") / "chroma_db"
        self.collection_name = collection_name
        self.embedding_model = embedding_model

    def search(
        self,
        query: str | RetrievalQuery,
        *,
        requested_language: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        normalized_query = _normalize_query(query, filters)
        store = self._load_store()
        if not store.nodes:
            return self._build_result(normalized_query, requested_language, [])

        try:
            collection = self._build_collection(store.nodes)
            query_embedding = self._embed_texts([normalized_query.query_text])[0]
            kwargs: dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": limit,
            }
            if normalized_query.metadata_filter:
                kwargs["where"] = normalized_query.metadata_filter
            result = collection.query(**kwargs)
        except Exception as exc:
            return RetrievalResult(
                query=normalized_query.query_text,
                filters=normalized_query.metadata_filter,
                requested_language=requested_language,
                fallback_reason=f"vector backend unavailable: {type(exc).__name__}: {exc}",
            )

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0] if result.get("distances") else []
        metadatas = result.get("metadatas", [[]])[0] if result.get("metadatas") else []
        nodes_by_id = {node.node_id: node for node in store.nodes}
        branches = self._branches_by_key(store)
        candidates: list[RetrievalCandidate] = []

        for index, node_id in enumerate(ids):
            node = nodes_by_id.get(node_id)
            branch = branches.get((node_id, requested_language))
            if node is None or branch is None:
                continue
            distance = float(distances[index]) if index < len(distances) else 0.0
            metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else node.to_storage_metadata()
            candidates.append(
                RetrievalCandidate(
                    node_id=node.node_id,
                    concept_type=node.concept_type,
                    canonical_text_en=node.canonical_text_en,
                    language_code=requested_language,
                    score=1.0 / (1.0 + max(distance, 0.0)),
                    metadata_tags=metadata,
                    source_payload=node.source_payload,
                    branch_payload=branch.payload,
                )
            )

        return self._build_result(normalized_query, requested_language, candidates)

    def _build_collection(self, nodes: list[CanonicalLessonNode]) -> Any:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb is not installed") from exc

        self.persist_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.persist_path))
        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass
        collection = client.create_collection(name=self.collection_name)
        embeddings = self._embed_texts([node.to_document() for node in nodes])
        collection.add(
            ids=[node.node_id for node in nodes],
            documents=[node.to_document() for node in nodes],
            metadatas=[node.to_storage_metadata() for node in nodes],
            embeddings=embeddings,
        )
        return collection

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed") from exc

        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or os.getenv("LLM_BASE_URL", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("LLM_API_KEY", "").strip()
        if not api_key and base_url and "api.openai.com" not in base_url.lower():
            api_key = "lm-studio"
        if not api_key:
            raise RuntimeError("No API key found. Set OPENAI_API_KEY or LLM_API_KEY.")

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)
        response = client.embeddings.create(model=self.embedding_model, input=texts)
        return [list(item.embedding) for item in response.data]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _normalize_query(
    query: str | RetrievalQuery,
    filters: dict[str, Any] | None = None,
) -> RetrievalQuery:
    if isinstance(query, RetrievalQuery):
        merged_filter = dict(query.metadata_filter)
        if filters:
            merged_filter.update({key: value for key, value in filters.items() if value not in (None, "")})
        return RetrievalQuery(
            query_id=query.query_id,
            query_text=query.query_text,
            query_type=query.query_type,
            expected_ids=list(query.expected_ids),
            metadata_filter=merged_filter,
        )

    active_filters = {
        key: value
        for key, value in (filters or {}).items()
        if value not in (None, "")
    }
    return RetrievalQuery(query_text=query, metadata_filter=active_filters)


def _normalize_concept_type(concept_type: str) -> str:
    value = concept_type.strip().lower()
    if value.endswith("s"):
        value = value[:-1]
    return value


def _matches_metadata(
    metadata_tags: dict[str, Any],
    filters: dict[str, Any],
) -> bool:
    for key, value in filters.items():
        if metadata_tags.get(key) != value:
            return False
    return True


def _lexical_score_candidate(
    node: CanonicalLessonNode,
    query: RetrievalQuery,
) -> float:
    score = 0.0
    query_tokens = set(_tokenize(query.query_text))
    node_tokens = set(_tokenize(node.canonical_text_en))
    score += 3.0 * len(query_tokens & node_tokens)

    concept_type = _normalize_concept_type(node.concept_type)
    filter_concept = str(query.metadata_filter.get("concept_type", "")).strip().lower()
    if filter_concept and filter_concept == concept_type:
        score += 2.0

    storage_metadata = node.to_storage_metadata()
    score += 1.0 * sum(
        1 for key, value in query.metadata_filter.items() if storage_metadata.get(key) == value
    )

    if not query_tokens and query.metadata_filter:
        score += 1.0
    return score


def get_retrieval_service(
    enabled: bool,
    store_path: Path | None,
    *,
    backend: str = "file",
    embedding_model: str = "text-embedding-3-small",
) -> RetrievalService:
    if not enabled:
        return NoOpRetrievalService()
    if store_path is None:
        return NoOpRetrievalService(reason="retrieval store is not configured")

    if backend == "file":
        return FileBackedRetrievalService(store_path)
    if backend == "chroma":
        return ChromaVectorRetrievalService(
            store_path,
            collection_name="jlesson_retrieval",
            embedding_model=embedding_model,
        )
    return NoOpRetrievalService(reason=f"unknown retrieval backend: {backend}")