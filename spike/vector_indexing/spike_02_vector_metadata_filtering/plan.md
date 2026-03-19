# Spike 2 Plan: Vector + Metadata Filtering

Date: 2026-03-19

## Goal

Validate that metadata filtering improves topical precision while preserving semantic relevance.

## Recommended First Implementation

- Reuse spike 1 embedding/index pipeline.
- Add metadata-aware query constraints in Chroma.
- Compare no-filter vs filtered retrieval outcomes.

## Metadata Fields in Scope

- `theme`
- `level`
- `concept_type`
- `grammar_progression.ja`

## Setup Steps

1. Activate environment:

```powershell
conda activate py312
```

2. Reuse dependencies from spike 1.

## Implementation Steps

1. Reuse canonical corpus and embeddings from spike 1.
2. Add metadata-enriched records to vector store.
3. Execute two query modes:
- baseline semantic search (no metadata filter)
- semantic search with metadata filters
4. Compare precision@k and off-topic hit rate.
5. Save metrics artifact JSON in this folder.

## Deliverables

- `spike_02_metadata.py`
- `results_spike_02.json`
- short markdown summary with before/after metrics

## Pass Criteria

1. Metadata filters reduce off-topic candidates.
2. Precision@5 does not materially regress.
3. Language/grammar key filtering behaves as expected.
