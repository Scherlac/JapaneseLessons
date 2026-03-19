"""Spike 1: baseline vector retrieval over canonical English nodes.

Usage:
    conda activate py312
    python spike/vector_indexing/spike_01_baseline_vector_retrieval/spike_01_baseline.py

Environment (optional):
    OPENAI_API_KEY=<key>
    OPENAI_BASE_URL=<url>              # optional, defaults to OpenAI hosted API
    SPIKE_EMBEDDING_MODEL=text-embedding-3-small
    SPIKE_CORPUS_SIZE=300              # target range: 200-500
    SPIKE_QUERY_COUNT=40               # target range: 30-50
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spike.vector_indexing.shared.spike_components import (
    ChromaVectorStoreAdapter,
    OpenAIEmbeddingProvider,
    build_benchmark_queries,
    build_nodes_from_vocab,
    load_env_for_repo,
    percentile_95,
    precision_at_k,
    repo_root_from_script,
    utc_now,
)
from spike.vector_indexing.shared.spike_data_model import SpikeResult


SPIKE_ID = "spike_01_baseline_vector_retrieval"
EMBEDDING_MODEL = os.getenv("SPIKE_EMBEDDING_MODEL", "text-embedding-3-small")
CORPUS_SIZE = int(os.getenv("SPIKE_CORPUS_SIZE", "300"))
QUERY_COUNT = int(os.getenv("SPIKE_QUERY_COUNT", "40"))
TOP_K = 10
REPEATS = int(os.getenv("SPIKE_REPEATS", "3"))


def run_spike() -> SpikeResult:
    start_ts = time.perf_counter()
    repo = repo_root_from_script(Path(__file__))
    load_env_for_repo(repo)

    output_dir = Path(__file__).resolve().parent
    provider = OpenAIEmbeddingProvider(model_name=EMBEDDING_MODEL)
    vector_store = ChromaVectorStoreAdapter(
        persist_path=output_dir / "chroma_db",
        collection_name="spike01_baseline",
    )

    nodes = build_nodes_from_vocab(repo_root=repo, target_size=CORPUS_SIZE)
    if len(nodes) < 20:
        raise RuntimeError(f"Corpus too small for benchmark: {len(nodes)}")

    corpus_embeddings = provider.embed_texts([n.to_document() for n in nodes])
    vector_store.reset()
    vector_store.upsert(nodes, corpus_embeddings)

    queries = build_benchmark_queries(nodes=nodes, query_count=QUERY_COUNT)
    query_embeddings = provider.embed_texts([q.query_text for q in queries])

    latencies_ms: list[float] = []
    p3_scores: list[float] = []
    p5_scores: list[float] = []
    p10_scores: list[float] = []

    for _ in range(REPEATS):
        for query, qv in zip(queries, query_embeddings):
            t0 = time.perf_counter()
            hits = vector_store.query(query_embedding=qv, top_k=TOP_K)
            elapsed = (time.perf_counter() - t0) * 1000
            latencies_ms.append(elapsed)

            got_ids = [hit.node_id for hit in hits]
            expected = set(query.expected_ids)
            p3_scores.append(precision_at_k(got_ids, expected, 3))
            p5_scores.append(precision_at_k(got_ids, expected, 5))
            p10_scores.append(precision_at_k(got_ids, expected, 10))

    duration_s = time.perf_counter() - start_ts
    throughput_qps = round((len(queries) * REPEATS) / max(0.001, duration_s), 2)

    return SpikeResult(
        spike=SPIKE_ID,
        embedding_model=EMBEDDING_MODEL,
        vector_store=vector_store.backend_name,
        timestamp_utc=utc_now(),
        corpus_size=len(nodes),
        query_count=len(queries),
        latency_ms={
            "p50": round(statistics.median(latencies_ms) if latencies_ms else 0.0, 3),
            "p95": round(percentile_95(latencies_ms), 3),
        },
        precision_at_k={
            "p3": round(sum(p3_scores) / max(1, len(p3_scores)), 4),
            "p5": round(sum(p5_scores) / max(1, len(p5_scores)), 4),
            "p10": round(sum(p10_scores) / max(1, len(p10_scores)), 4),
        },
        timing={
            "total_duration_s": round(duration_s, 3),
            "throughput_qps": throughput_qps,
            "repeats": float(REPEATS),
        },
        notes=(
            "Baseline uses canonical English node text with theme/type metadata persisted. "
            "No metadata filtering applied in this spike; focus is pure vector relevance baseline."
        ),
    )


def main() -> int:
    output_file = Path(__file__).resolve().parent / "results_spike_01.json"

    try:
        result = run_spike()
    except Exception as exc:
        result = SpikeResult(
            spike=SPIKE_ID,
            embedding_model=EMBEDDING_MODEL,
            vector_store="chroma_local_persistent",
            timestamp_utc=utc_now(),
            corpus_size=0,
            query_count=0,
            latency_ms={
                "p50": 0.0,
                "p95": 0.0,
            },
            precision_at_k={
                "p3": 0.0,
                "p5": 0.0,
                "p10": 0.0,
            },
            timing={
                "total_duration_s": 0.0,
                "throughput_qps": 0.0,
                "repeats": float(REPEATS),
            },
            notes=f"Execution failed: {type(exc).__name__}: {exc}",
        )

    output_file.write_text(json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"Wrote benchmark artifact: {output_file}")
    print(f"Corpus: {result.corpus_size} | Queries: {result.query_count}")
    print(f"Precision@5: {result.precision_at_k.get('p5')} | P95 latency(ms): {result.latency_ms.get('p95')}")
    if result.corpus_size == 0:
        print("Spike failed. Check artifact notes for details.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
