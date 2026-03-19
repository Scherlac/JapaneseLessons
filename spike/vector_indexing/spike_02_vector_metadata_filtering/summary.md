# Spike 2 Summary: Vector + Metadata Filtering

Date: 2026-03-19

## Run Snapshot

- Spike: `spike_02_vector_metadata_filtering`
- Embedding model: `text-embedding-3-small`
- Vector store: `chroma_local_persistent`
- Corpus size: 300
- Query count: 40
- Repeats: 3

## Headline Metrics (Filtered Mode)

- Precision@3: 0.3833
- Precision@5: 0.26
- Precision@10: 0.1675
- Latency p50: 1.606 ms
- Latency p95: 2.351 ms

## Baseline vs Filtered

- Precision@5 delta (overall): 0.0
- Precision@5 delta (metadata-eligible subset): 0.0
- Off-topic reduction (overall): 0.0
- Off-topic reduction (metadata-eligible subset): 0.0
- Filter pass-rate on constrained queries (filtered mode): 1.0

## Interpretation

- Metadata filters are being applied correctly (`filter_pass_rate = 1.0`).
- In this run, constrained queries already retrieve in-theme results in baseline mode, so measured relevance deltas are neutral.
- This indicates the current query set/corpus pair is easy for semantic retrieval and does not yet stress metadata disambiguation.

## Recommended Next Iteration

1. Add harder ambiguous queries where semantics alone can cross themes.
2. Increase metadata-constrained query share beyond current distribution.
3. Add concept-type and grammar-progression filters to stress non-theme constraints.
