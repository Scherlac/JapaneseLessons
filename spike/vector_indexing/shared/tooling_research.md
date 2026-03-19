# Tooling Research for Spike 1 and Spike 2

Date: 2026-03-19

## Research Goal

Identify practical tools, packages, APIs, and architecture options for:
- baseline semantic retrieval (spike 1)
- metadata-aware retrieval (spike 2)

## Embedding Model Options

### Hosted API options

1. OpenAI `text-embedding-3-small`
- Pros: strong quality/cost, straightforward API, dimension control support.
- Cons: external API dependency and network latency.
- Good fit: first spike baseline and fast iteration.

2. OpenAI `text-embedding-3-large`
- Pros: stronger retrieval quality potential than small model.
- Cons: higher cost and vector size.
- Good fit: later A/B quality comparison.

3. Other API vendors (Cohere, Voyage, etc.)
- Pros: additional quality/cost alternatives.
- Cons: integration overhead during initial spikes.
- Good fit: second-pass benchmark only.

### Self-hosted options

1. SentenceTransformers package
- Pros: local inference, broad model ecosystem.
- Cons: model ops and performance tuning burden.
- Good fit: optional follow-up once API baseline is stable.

2. BGE family (for example `bge-large-en-v1.5`, `bge-m3`)
- Pros: strong retrieval benchmarks, multilingual options.
- Cons: heavier runtime and model management.
- Good fit: advanced evaluation phase.

## Vector Store / Index Options

### Option A: Chroma

- Type: open-source vector data infrastructure with local and cloud modes.
- Metadata filtering: built-in metadata filtering in query path.
- Developer experience: very fast Python prototyping.
- Best for spikes: yes, minimal setup for quick evidence.

### Option B: Postgres + pgvector

- Type: relational DB extension for vector similarity.
- Index options: HNSW and IVFFlat.
- Metadata filtering: mature SQL filtering and joins.
- Best for spikes: yes, if production direction is PostgreSQL-centric.

### Option C: Qdrant

- Type: dedicated vector search engine (self-hosted/cloud).
- Strengths: vector-native features, multitenancy and distributed docs.
- Best for spikes: strong option if dedicated vector DB is target architecture.

### Option D: Weaviate

- Type: open-source vector database ecosystem.
- Strengths: semantic/hybrid search, cloud and local deployment options.
- Best for spikes: useful when agent-centric integrations are in scope.

### Option E: Milvus

- Type: high-scale vector database with managed path via Zilliz.
- Strengths: high-performance and large-scale capabilities.
- Best for spikes: useful for scale-focused exploration.

### Option F: FAISS

- Type: similarity search library, not a full database.
- Strengths: high-performance ANN and strong research lineage.
- Limitations: requires surrounding storage and CRUD management.
- Best for spikes: good for algorithm experimentation, less ideal for end-to-end app behavior.

## Metadata Filtering Approaches

1. Pre-filter then vector search
- Pros: reduced search space.
- Risk: recall loss if filters are too strict.

2. Vector search then post-filter
- Pros: better semantic recall.
- Risk: might return fewer valid results if filter is narrow.

3. Hybrid filter+rerank
- Approach: vector top-k, metadata constraints, then rerank.
- Best for spikes: recommended for evaluation in spike 2.

## Python Package Candidates

### Core

- `openai` (already installed): embeddings API access.
- `numpy` / `pandas`: vector and benchmark analysis.
- `python-dotenv`: API key and config management.

### Local vector DB candidates

- `chromadb`
- `qdrant-client`
- `psycopg` or `sqlalchemy` (+ pgvector extension in DB)

### Local embedding candidates

- `sentence-transformers`
- `transformers`
- `torch`

### Optional evaluation helpers

- `scikit-learn` (metrics and clustering utilities)
- `rich` (pretty benchmarking output)

## Recommended Decisions for First Pass

1. Keep embeddings API-based for initial speed.
2. Start with Chroma locally to reduce setup time.
3. Evaluate pgvector path as a second implementation branch if SQL filtering is strategic.
4. Keep model and index configuration explicit in result logs for reproducibility.

## Risks and Mitigations

1. Risk: vendor lock-in too early
- Mitigation: abstract embedding provider behind a small adapter.

2. Risk: metadata schema drift
- Mitigation: define and version metadata tag namespaces from spike 2.

3. Risk: unstable benchmark conclusions
- Mitigation: fixed benchmark query set and fixed candidate corpus size.

## Resources Used

- OpenAI embeddings guide and vector database cookbook links.
- pgvector documentation and indexing guidance.
- Chroma OSS docs and README usage examples.
- Qdrant, Weaviate, and Milvus documentation portals.
- FAISS wiki documentation.
- SBERT and BGE model documentation.
