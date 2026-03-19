# Vector Indexing Spikes (Spike 1 + Spike 2)

This folder starts implementation-research for the first two spikes from `docs/vector_indexing.md`.

## Scope

- Spike 1: Baseline vector retrieval over canonical English nodes.
- Spike 2: Vector retrieval with secondary metadata filtering.

## Execution Environment

Use the `py312` conda environment.

```powershell
conda activate py312
python --version
```

Current workspace package baseline:
- Installed: `openai`, `click`, `pydantic`
- Not yet installed: `chromadb`, `qdrant-client`, `faiss-cpu`, `sentence-transformers`

## Folder Layout

- `shared/`: Cross-spike research and benchmark setup.
- `spike_01_baseline_vector_retrieval/`: Baseline semantic retrieval plan and script skeleton.
- `spike_02_vector_metadata_filtering/`: Metadata filter plan and script skeleton.

## Recommended Starting Stack for Fastest Progress

For initial learning speed and low ops burden:
1. Embeddings API: OpenAI `text-embedding-3-small`
2. Vector store (local): Chroma
3. Metadata filtering: Chroma `where` filtering for spike 2

Alternative stack (more production-like relational path):
1. Embeddings API: OpenAI `text-embedding-3-small`
2. Vector store: Postgres + pgvector
3. Metadata filtering: SQL `WHERE` + vector similarity query

## Run Order

1. Read `shared/tooling_research.md`
2. Read `shared/benchmark_plan.md`
3. Run `spike_01_baseline_vector_retrieval/spike_01_baseline.py`
4. Run `spike_02_vector_metadata_filtering/spike_02_metadata.py`
5. Record outcomes in `docs/development_history.md`
