# Spike 1 Plan: Baseline Vector Retrieval

Date: 2026-03-19

## Goal

Validate vector-only retrieval quality over canonical English nodes.

## Recommended First Implementation

- Embedding provider: OpenAI API (`text-embedding-3-small`)
- Vector store: Chroma local persistent collection
- Query metric: cosine similarity / default nearest-neighbor

## Why this path

- Fastest setup from current repository state.
- Minimal infra burden.
- Produces reliable baseline for spike 2 comparisons.

## Setup Steps

1. Activate environment:

```powershell
conda activate py312
```

2. Install minimal extra dependencies:

```powershell
pip install chromadb numpy pandas python-dotenv
```

3. Ensure API credentials in environment:

```env
OPENAI_API_KEY=...
```

## Implementation Steps

1. Load canonical nodes from a local JSON fixture.
2. Create embeddings for node canonical text.
3. Upsert vectors into Chroma with metadata.
4. Execute benchmark query set and collect top-k results.
5. Save metrics artifact JSON in this folder.

## Deliverables

- `spike_01_baseline.py`
- `results_spike_01.json`
- short markdown summary with observations

## Pass Criteria

1. Precision@5 is stable across runs.
2. P95 query latency remains within agreed target.
3. No blocking schema or indexing errors.
