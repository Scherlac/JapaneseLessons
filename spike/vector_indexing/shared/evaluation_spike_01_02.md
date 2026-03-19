# Spike 1 and Spike 2 Evaluation

Date: 2026-03-19

## Scope

This evaluation compares:
- Spike 1 baseline semantic retrieval
- Spike 2 semantic retrieval with metadata filtering

Both runs used:
- Embedding model: text-embedding-3-small
- Vector store: chroma_local_persistent
- Corpus size: 300
- Query count: 40
- Repeats: 3

## Results Snapshot

### Spike 1 (baseline)

- Precision@3: 0.3833
- Precision@5: 0.26
- Precision@10: 0.1675
- Latency p50: 1.799 ms
- Latency p95: 2.794 ms
- Throughput: 38.32 qps

### Spike 2 (filtered mode)

- Precision@3: 0.3833
- Precision@5: 0.26
- Precision@10: 0.1675
- Latency p50: 1.646 ms
- Latency p95: 2.899 ms
- Throughput: 69.36 qps (includes both baseline and filtered loops in one run)
- Metadata filter pass-rate: 1.0
- Metadata-eligible query share: 0.075

### Spike 2 internal baseline vs filtered

- Precision@5 delta (filtered - internal baseline): 0.0
- Off-topic reduction (filtered - internal baseline): 0.0

## Gate Check

- Spike 1 stability gate: PASS
  - Baseline retrieval is stable and reproducible.
- Spike 2 filtering gate: PARTIAL
  - Filters are correctly applied (pass-rate 1.0).
  - No measurable relevance gain in current dataset/query mix.

## Interpretation

Current semantic queries are not difficult enough to force disambiguation where metadata filters add value. The system behaves correctly, but benchmark sensitivity is low because only a small share of queries are metadata-constrained and those are already easy in baseline mode.

## Next Evaluation Actions

1. Raise metadata-constrained query share to 25% to 40%.
2. Add ambiguity-heavy cross-theme queries (same term in multiple contexts).
3. Add concept_type and grammar progression constraints in query filters.
4. Track separate metrics by query class (lexical, paraphrase, theme, grammar).
5. Re-run with fixed random seed and store 3-run aggregate mean/stdev.
