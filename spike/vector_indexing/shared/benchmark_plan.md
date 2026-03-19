# Shared Benchmark Plan (Spike 1 + Spike 2)

Date: 2026-03-19

## Objective

Provide a stable and comparable evaluation protocol across the first two spikes.

## Dataset

1. Canonical corpus size target: 200 to 500 nodes.
2. Source language: English canonical text.
3. Required metadata fields:
- `theme`
- `level`
- `concept_type`
- `grammar_progression.ja` (optional in spike 1, required in spike 2)

## Query Set

1. Build a fixed set of 30 to 50 semantic queries.
2. Include at least:
- direct lexical match queries
- paraphrased intent queries
- grammar-constrained queries
- theme-constrained queries

## Metrics

1. Relevance metrics:
- precision@k (k=3, 5, 10)
- recall@k (if labeled gold set available)

2. Latency metrics:
- p50, p95 query latency
- indexing throughput (documents/sec)

3. Filtering metrics (spike 2):
- filter pass-rate
- off-topic reduction rate
- relevance delta vs no-filter baseline

## Run Protocol

1. Use same corpus and query set for both spikes.
2. Freeze embedding model per benchmark run.
3. Run each query batch at least 3 times; report median metrics.
4. Persist outputs as JSON artifacts under each spike folder.

## Output Artifact Contract

Each run should emit:

```json
{
  "spike": "spike_01_or_spike_02",
  "embedding_model": "...",
  "vector_store": "...",
  "timestamp_utc": "...",
  "corpus_size": 0,
  "query_count": 0,
  "latency_ms": {"p50": 0, "p95": 0},
  "precision_at_k": {"p3": 0, "p5": 0, "p10": 0},
  "notes": "..."
}
```

## Decision Gates

1. Spike 1 passes if baseline semantic retrieval is stable and latency is acceptable.
2. Spike 2 passes if metadata filtering improves topical precision without major relevance collapse.
