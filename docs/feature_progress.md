
Next should be the first production-safe retrieval slice.

- [docs/vector_indexing.md](vector_indexing.md) — retrieval feature specification
- [spike/vector_indexing/README.md](../spike/vector_indexing/README.md) — retrieval spike implementation and research

Why this is the right next step

- progress_report.md now makes retrieval the active feature focus.
- architecture.md already defines the correct insertion point: upstream of the existing lesson pipeline, with fallback to the current generation flow.
- project_scale.md identifies the real missing piece: canonical node and branch schemas do not exist yet.
- development_history.md now makes the multilingual story clear: multilingual pipeline support already exists, so the next job is not “add multilingual” but “add retrieval and reusable multilingual content storage”.

Recommended next implementation order

1. Define the minimal retrieval data model
   Put in production code:
   - canonical lesson node
   - language branch
   - metadata tags
   - retrieval result envelope

   Goal:
   make the schema compatible with the current pipeline without changing rendering or lesson compilation.

2. Add a small retrieval module boundary
   Create a narrow API such as:
   - ingest canonical node
   - attach branch
   - search with metadata filters
   - return pipeline-friendly lesson material

   Goal:
   isolate retrieval from the rest of the app so it can be enabled or bypassed cleanly.

3. Integrate retrieval as optional upstream enrichment
   Flow should become:
   - try retrieval
   - if coverage is good enough, use retrieved material
   - otherwise fall back to the current LLM-first generation path

   Goal:
   no regression in lesson generation.

4. Log retrieval traces
   Capture:
   - query
   - filters
   - top candidates
   - fallback reason

   Goal:
   give yourself real evidence before expanding the database design.

5. Only after that, harden vocab durability
   Then address:
   - overwrite safety
   - difficulty metadata
   - cross-theme deduplication

   Reason:
   retrieval quality will depend on that source layer, but you first need the retrieval boundary in code.

What I would not do next

- not checkpointing first
- not Anki export
- not broader architecture docs
- not full vector platform buildout

Those are valid, but they are downstream of the retrieval boundary.

Concrete next deliverable

The best next commit would be:

- add retrieval models
- add a retrieval service interface
- add a no-op or file-backed implementation
- wire it into lesson generation behind a safe fallback path
- add tests for “retrieval hit” and “retrieval miss → fallback”

If you want, I can implement that next and start with the smallest viable retrieval skeleton in the codebase.