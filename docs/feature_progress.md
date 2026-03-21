Retrieval is now in its first production-safe slice.

- [docs/vector_indexing.md](vector_indexing.md) — retrieval feature specification
- [spike/vector_indexing/README.md](../spike/vector_indexing/README.md) — retrieval spike overview and research entry point
- [progress_report.md](../progress_report.md) for active feature development
- [software_engineering.md](software_engineering.md) for engineering principles and development cycle

Current status

The codebase now has a minimal retrieval boundary integrated upstream of the lesson pipeline with a safe fallback path.

Implemented in production code

1. Minimal retrieval data model
   Added:
   - canonical lesson node
   - language branch
   - retrieval candidate
   - retrieval result envelope
   - pipeline-friendly retrieved material payload

2. Retrieval module boundary
   Added a narrow API for:
   - ingest canonical node
   - attach branch
   - search with metadata filters
   - return lesson-material payload compatible with the current pipeline

3. Safe upstream pipeline integration
   Flow is now:
   - try retrieval first
   - estimate noun/verb coverage
   - use retrieved material when coverage is above threshold
   - otherwise fall back to the existing vocab + LLM generation path

4. Retrieval trace logging
   Current trace captures:
   - query
   - filters
   - requested language
   - top candidates
   - estimated coverage
   - fallback reason or retrieval-use outcome

5. Validation coverage
   Added tests for:
   - retrieval hit
   - retrieval miss with fallback to vocab flow
   - file-backed branch projection
   - branch attachment validation

What this implementation intentionally is

- a file-backed retrieval skeleton
- a stable production interface
- a low-dependency first slice
- a safe insertion point for later vector-backed implementations

What this implementation intentionally is not yet

- not Chroma-backed production retrieval
- not embedding-driven semantic search
- not spike benchmark parity
- not multilingual branch projection quality evaluation
- not source-vocab durability hardening

Why this was the correct first landing

- architecture.md already identified the correct insertion point: upstream of generation with fallback to the current flow
- retrieval can now be enabled or bypassed cleanly from the CLI
- downstream compilation, rendering, and persistence remain unchanged
- the codebase now has a concrete seam where spike learnings can be pulled into production incrementally

Important follow-up note

The retrieval spike documentation was used as design input for this slice, but the spike implementation details have not yet been fully ported into production code.

That means the current production retrieval layer reflects the intended shape of the spike, but not yet its vector-store, embedding, or benchmark machinery.

Recommended next implementation order

1. Review and align with the spike implementation in detail
   Pull across:
   - spike query model
   - metadata filter conventions
   - benchmark structure
   - store adapter shape where useful

2. Add ingest tooling for the production retrieval store
   Add commands or utilities to:
   - ingest canonical nodes
   - attach language branches
   - inspect stored retrieval material

3. Expand retrieval beyond vocab reuse
   Add support for:
   - sentence material
   - grammar-linked retrieval payloads
   - richer branch metadata

4. Evaluate whether to add a vector-backed implementation behind the same interface
   Candidates remain:
   - Chroma
   - Postgres + pgvector

5. Only after that, harden vocab durability
   Then address:
   - overwrite safety
   - difficulty metadata
   - cross-theme deduplication

   Reason:
   retrieval quality will still be bounded by source-data consistency, but the retrieval boundary now exists and can be exercised first.

What I would still not do next

- not checkpointing first
- not Anki export
- not broader architecture docs
- not a full vector platform buildout before aligning production code with spike findings

Concrete next deliverable

The best next commit after this slice would be:

- review the spike implementation files directly
- align the production retrieval request/filter model with the spike
- add production ingest tooling for the file-backed store
- add sentence and grammar retrieval coverage
- preserve the existing fallback guarantees and test coverage