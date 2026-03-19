"""Spike 2: vector retrieval with metadata filtering.

Usage:
    conda activate py312
    python spike/vector_indexing/spike_02_vector_metadata_filtering/spike_02_metadata.py

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
from typing import Any

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
from spike.vector_indexing.shared.spike_data_model import RetrievalQuery, SpikeResult


SPIKE_ID = "spike_02_vector_metadata_filtering"
EMBEDDING_MODEL = os.getenv("SPIKE_EMBEDDING_MODEL", "text-embedding-3-small")
CORPUS_SIZE = int(os.getenv("SPIKE_CORPUS_SIZE", "300"))
QUERY_COUNT = int(os.getenv("SPIKE_QUERY_COUNT", "40"))
TOP_K = 10
REPEATS = int(os.getenv("SPIKE_REPEATS", "3"))


def _evaluate_mode(
    vector_store: ChromaVectorStoreAdapter,
    queries: list[RetrievalQuery],
    query_embeddings: list[list[float]],
    apply_filters: bool,
) -> dict[str, Any]:
    latencies_ms: list[float] = []
    p3_scores: list[float] = []
    p5_scores: list[float] = []
    p10_scores: list[float] = []
    off_topic_rates: list[float] = []
    off_topic_rates_metadata_scope: list[float] = []
    filter_pass_rates: list[float] = []
    p5_scores_metadata_scope: list[float] = []

    total_queries = 0
    metadata_eligible_queries = 0
    filtered_queries_applied = 0

    for _ in range(REPEATS):
        for query, qv in zip(queries, query_embeddings):
            total_queries += 1

            metadata_eligible = bool(query.metadata_filter)
            if metadata_eligible:
                metadata_eligible_queries += 1

            metadata_filter = query.metadata_filter if apply_filters and metadata_eligible else None
            if metadata_filter:
                filtered_queries_applied += 1

            t0 = time.perf_counter()
            hits = vector_store.query(
                query_embedding=qv,
                top_k=TOP_K,
                metadata_filter=metadata_filter,
            )
            elapsed = (time.perf_counter() - t0) * 1000
            latencies_ms.append(elapsed)

            got_ids = [hit.node_id for hit in hits]
            expected = set(query.expected_ids)
            p3_scores.append(precision_at_k(got_ids, expected, 3))
            p5_scores.append(precision_at_k(got_ids, expected, 5))
            p10_scores.append(precision_at_k(got_ids, expected, 10))
            if metadata_eligible:
                p5_scores_metadata_scope.append(precision_at_k(got_ids, expected, 5))

            # Off-topic is measured as non-expected hits in top-k.
            if got_ids:
                off_topic_hits = sum(1 for rid in got_ids[:TOP_K] if rid not in expected)
                rate = off_topic_hits / min(TOP_K, len(got_ids))
                off_topic_rates.append(rate)
                if metadata_eligible:
                    off_topic_rates_metadata_scope.append(rate)
            else:
                off_topic_rates.append(1.0)
                if metadata_eligible:
                    off_topic_rates_metadata_scope.append(1.0)

            # Filter pass-rate quantifies how often returned hits satisfy active constraints.
            if metadata_filter:
                total_hits = max(1, len(hits))
                passed_hits = 0
                for hit in hits:
                    hit_meta = hit.metadata if isinstance(hit.metadata, dict) else {}
                    if all(hit_meta.get(k) == v for k, v in metadata_filter.items()):
                        passed_hits += 1
                filter_pass_rates.append(passed_hits / total_hits)

    return {
        "latency_ms": {
            "p50": round(statistics.median(latencies_ms) if latencies_ms else 0.0, 3),
            "p95": round(percentile_95(latencies_ms), 3),
        },
        "precision_at_k": {
            "p3": round(sum(p3_scores) / max(1, len(p3_scores)), 4),
            "p5": round(sum(p5_scores) / max(1, len(p5_scores)), 4),
            "p10": round(sum(p10_scores) / max(1, len(p10_scores)), 4),
        },
        "off_topic_rate": round(sum(off_topic_rates) / max(1, len(off_topic_rates)), 4),
        "off_topic_rate_metadata_scope": round(
            sum(off_topic_rates_metadata_scope) / max(1, len(off_topic_rates_metadata_scope)),
            4,
        ),
        "filter_pass_rate": round(sum(filter_pass_rates) / max(1, len(filter_pass_rates)), 4),
        "precision_at_5_metadata_scope": round(
            sum(p5_scores_metadata_scope) / max(1, len(p5_scores_metadata_scope)),
            4,
        ),
        "query_volume": {
            "total_queries": total_queries,
            "metadata_eligible_queries": metadata_eligible_queries,
            "filtered_queries_applied": filtered_queries_applied,
        },
    }


def run_spike() -> SpikeResult:
    start_ts = time.perf_counter()
    repo = repo_root_from_script(Path(__file__))
    load_env_for_repo(repo)

    output_dir = Path(__file__).resolve().parent
    provider = OpenAIEmbeddingProvider(model_name=EMBEDDING_MODEL)
    vector_store = ChromaVectorStoreAdapter(
        persist_path=output_dir / "chroma_db",
        collection_name="spike02_metadata_filtering",
    )

    nodes = build_nodes_from_vocab(repo_root=repo, target_size=CORPUS_SIZE)
    if len(nodes) < 20:
        raise RuntimeError(f"Corpus too small for benchmark: {len(nodes)}")

    corpus_embeddings = provider.embed_texts([n.to_document() for n in nodes])
    vector_store.reset()
    vector_store.upsert(nodes, corpus_embeddings)

    queries = build_benchmark_queries(nodes=nodes, query_count=QUERY_COUNT)
    query_embeddings = provider.embed_texts([q.query_text for q in queries])

    baseline = _evaluate_mode(
        vector_store=vector_store,
        queries=queries,
        query_embeddings=query_embeddings,
        apply_filters=False,
    )
    filtered = _evaluate_mode(
        vector_store=vector_store,
        queries=queries,
        query_embeddings=query_embeddings,
        apply_filters=True,
    )

    duration_s = time.perf_counter() - start_ts
    total_queries = len(queries) * REPEATS * 2  # baseline + filtered
    throughput_qps = round(total_queries / max(0.001, duration_s), 2)

    p5_delta = round(filtered["precision_at_k"]["p5"] - baseline["precision_at_k"]["p5"], 4)
    p5_delta_metadata_scope = round(
        filtered["precision_at_5_metadata_scope"] - baseline["precision_at_5_metadata_scope"],
        4,
    )
    off_topic_reduction = round(baseline["off_topic_rate"] - filtered["off_topic_rate"], 4)
    off_topic_reduction_metadata_scope = round(
        baseline["off_topic_rate_metadata_scope"] - filtered["off_topic_rate_metadata_scope"],
        4,
    )

    return SpikeResult(
        spike=SPIKE_ID,
        embedding_model=EMBEDDING_MODEL,
        vector_store=vector_store.backend_name,
        timestamp_utc=utc_now(),
        corpus_size=len(nodes),
        query_count=len(queries),
        latency_ms=filtered["latency_ms"],
        precision_at_k=filtered["precision_at_k"],
        timing={
            "total_duration_s": round(duration_s, 3),
            "throughput_qps": throughput_qps,
            "repeats": float(REPEATS),
            "filtered_query_share": round(
                filtered["query_volume"]["metadata_eligible_queries"]
                / max(1, filtered["query_volume"]["total_queries"]),
                4,
            ),
        },
        sample_results=[
            {
                "mode": "baseline_no_filter",
                "latency_ms": baseline["latency_ms"],
                "precision_at_k": baseline["precision_at_k"],
                "off_topic_rate": baseline["off_topic_rate"],
                "off_topic_rate_metadata_scope": baseline["off_topic_rate_metadata_scope"],
                "filter_pass_rate": baseline["filter_pass_rate"],
                "precision_at_5_metadata_scope": baseline["precision_at_5_metadata_scope"],
            },
            {
                "mode": "metadata_filtered",
                "latency_ms": filtered["latency_ms"],
                "precision_at_k": filtered["precision_at_k"],
                "off_topic_rate": filtered["off_topic_rate"],
                "off_topic_rate_metadata_scope": filtered["off_topic_rate_metadata_scope"],
                "filter_pass_rate": filtered["filter_pass_rate"],
                "precision_at_5_metadata_scope": filtered["precision_at_5_metadata_scope"],
            },
            {
                "mode": "delta_filtered_minus_baseline",
                "precision_p5_delta": p5_delta,
                "precision_p5_delta_metadata_scope": p5_delta_metadata_scope,
                "off_topic_reduction": off_topic_reduction,
                "off_topic_reduction_metadata_scope": off_topic_reduction_metadata_scope,
            },
        ],
        notes=(
            "Spike 2 compares no-filter and metadata-filtered retrieval on the same corpus/query set. "
            "Primary gates: off-topic reduction and stable precision@5."
        ),
    )


def main() -> int:
    output_file = Path(__file__).resolve().parent / "results_spike_02.json"

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
                "filtered_query_share": 0.0,
            },
            notes=f"Execution failed: {type(exc).__name__}: {exc}",
        )

    output_file.write_text(json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"Wrote benchmark artifact: {output_file}")
    print(f"Corpus: {result.corpus_size} | Queries: {result.query_count}")
    print(f"Precision@5: {result.precision_at_k.get('p5')} | P95 latency(ms): {result.latency_ms.get('p95')}")
    if result.corpus_size == 0:
        print("Spike failed. Check artifact notes for details.")
    else:
        baseline = next((x for x in result.sample_results if x.get("mode") == "baseline_no_filter"), {})
        filtered = next((x for x in result.sample_results if x.get("mode") == "metadata_filtered"), {})
        print(
            "Off-topic rate baseline->filtered: "
            f"{baseline.get('off_topic_rate', 0.0)} -> {filtered.get('off_topic_rate', 0.0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
