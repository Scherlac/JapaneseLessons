from __future__ import annotations

import json
import os
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from .spike_data_model import CanonicalMetadata, CanonicalNodeRecord, RetrievalQuery, SearchHit


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def repo_root_from_script(script_path: Path) -> Path:
    # .../spike/vector_indexing/spike_XX_xxx/script.py -> repo root
    return script_path.resolve().parents[3]


def load_env_for_repo(repo_root: Path) -> None:
    load_dotenv(repo_root / ".env")


def build_nodes_from_vocab(repo_root: Path, target_size: int, seed: int = 42) -> list[CanonicalNodeRecord]:
    vocab_dir = repo_root / "vocab"
    files = sorted(vocab_dir.rglob("*.json"))
    nodes: list[CanonicalNodeRecord] = []

    for file_path in files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        theme = str(data.get("theme") or file_path.stem).strip().lower() or file_path.stem.lower()
        language_scope = "hun-eng" if "hungarian" in str(file_path).lower() else "eng-jap"

        for concept_type in ("nouns", "verbs", "adjectives", "others"):
            items = data.get(concept_type, [])
            if not isinstance(items, list):
                continue

            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                english = str(item.get("english", "")).strip().lower()
                if not english:
                    continue

                concept = concept_type[:-1] if concept_type.endswith("s") else concept_type
                node = CanonicalNodeRecord(
                    node_id=f"{theme}:{concept_type}:{idx}:{language_scope}",
                    canonical_text_en=f"Theme: {theme}. Type: {concept}. English: {english}.",
                    metadata=CanonicalMetadata(
                        theme=theme,
                        level="beginner",
                        concept_type=concept_type,
                        language_scope=language_scope,
                        grammar_progression_ja="",
                    ),
                )
                nodes.append(node)

    # Deduplicate by canonical text for cleaner benchmark corpora.
    dedup: dict[str, CanonicalNodeRecord] = {}
    for n in nodes:
        dedup.setdefault(n.canonical_text_en, n)

    values = list(dedup.values())
    random.Random(seed).shuffle(values)
    return values[:target_size]


def build_benchmark_queries(nodes: list[CanonicalNodeRecord], query_count: int, seed: int = 42) -> list[RetrievalQuery]:
    rng = random.Random(seed)
    by_theme: dict[str, list[CanonicalNodeRecord]] = {}
    for node in nodes:
        by_theme.setdefault(node.metadata.theme, []).append(node)

    lexical_queries: list[RetrievalQuery] = []
    theme_queries: list[RetrievalQuery] = []

    sample_nodes = nodes[: min(20, len(nodes))]
    for idx, node in enumerate(sample_nodes):
        term = node.canonical_text_en.split("English:", 1)[-1].strip(" .")
        lexical_queries.append(
            RetrievalQuery(
                query_id=f"q_direct_{idx}",
                query_text=f"Find concept for the English term {term}",
                query_type="direct_lexical",
                expected_ids=[node.node_id],
            )
        )
        lexical_queries.append(
            RetrievalQuery(
                query_id=f"q_para_{idx}",
                query_text=f"I need lesson material related to {term}",
                query_type="paraphrase_intent",
                expected_ids=[node.node_id],
            )
        )

    themes = list(by_theme.keys())
    rng.shuffle(themes)
    for idx, theme in enumerate(themes[:10]):
        expected = [n.node_id for n in by_theme[theme]]
        theme_queries.append(
            RetrievalQuery(
                query_id=f"q_theme_{idx}",
                query_text=f"Beginner lesson concepts in theme {theme}",
                query_type="theme_constraint",
                expected_ids=expected,
                metadata_filter={"theme": theme},
            )
        )

    # Keep a stable mix so spike 2 always has metadata-filter-capable queries.
    min_theme = min(len(theme_queries), max(1, query_count // 4))
    min_lexical = min(len(lexical_queries), query_count - min_theme)

    selected: list[RetrievalQuery] = []
    selected.extend(theme_queries[:min_theme])
    selected.extend(lexical_queries[:min_lexical])

    if len(selected) < query_count:
        remaining = [q for q in theme_queries[min_theme:] + lexical_queries[min_lexical:] if q.query_id not in {s.query_id for s in selected}]
        selected.extend(remaining[: query_count - len(selected)])

    rng.shuffle(selected)
    return selected[:query_count]


def precision_at_k(retrieved_ids: list[str], expected_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = retrieved_ids[:k]
    if not top:
        return 0.0
    hits = sum(1 for rid in top if rid in expected_ids)
    return hits / k


def percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) < 20:
        return max(values)
    return statistics.quantiles(values, n=20)[18]


class OpenAIEmbeddingProvider:
    """OpenAI-compatible embedding provider adapter."""

    def __init__(self, model_name: str, batch_size: int = 64) -> None:
        self.model_name = model_name
        self._batch_size = batch_size
        self._client = self._build_client()

    @staticmethod
    def _build_client() -> OpenAI:
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or os.getenv("LLM_BASE_URL", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("LLM_API_KEY", "").strip()

        if not api_key and base_url and "api.openai.com" not in base_url.lower():
            api_key = "lm-studio"

        if not api_key:
            raise RuntimeError("No API key found. Set OPENAI_API_KEY or LLM_API_KEY in environment/.env.")

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAI(**kwargs)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i:i + self._batch_size]
            resp = self._client.embeddings.create(model=self.model_name, input=batch)
            vectors.extend([item.embedding for item in resp.data])
        return vectors


class ChromaVectorStoreAdapter:
    """Chroma implementation of VectorStore interface."""

    backend_name = "chroma_local_persistent"

    def __init__(self, persist_path: Path, collection_name: str) -> None:
        self._client = chromadb.PersistentClient(path=str(persist_path))
        self._collection_name = collection_name
        self._collection = None

    def reset(self) -> None:
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
        self._collection = self._client.create_collection(name=self._collection_name)

    def upsert(self, records: list[CanonicalNodeRecord], embeddings: list[list[float]]) -> None:
        if self._collection is None:
            raise RuntimeError("Collection not initialized. Call reset() before upsert().")
        ids = [r.node_id for r in records]
        docs = [r.to_document() for r in records]
        metas = [r.metadata.to_storage_dict() for r in records]
        self._collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        if self._collection is None:
            raise RuntimeError("Collection not initialized. Call reset() before query().")

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if metadata_filter:
            kwargs["where"] = metadata_filter

        result = self._collection.query(**kwargs)
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0] if result.get("distances") else []
        metadatas = result.get("metadatas", [[]])[0] if result.get("metadatas") else []

        hits: list[SearchHit] = []
        for idx, node_id in enumerate(ids):
            score = float(distances[idx]) if idx < len(distances) else None
            metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
            hits.append(SearchHit(node_id=node_id, score=score, metadata=metadata))
        return hits
