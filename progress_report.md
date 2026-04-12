# Japanese Learning Material — Current Feature Development

> Updated: 2026-03-21  
> Project history: [docs/development_history.md](docs/development_history.md)  
> Project scale topics: [docs/project_scale.md](docs/project_scale.md)  
> Architecture overview: [docs/architecture.md](docs/architecture.md)

---

## Purpose

This report is the active-development view of the project.

It answers three questions only:

1. What is the current feature focus?
2. What is the next implementation slice?
3. What is currently blocking or constraining that slice?

Current development focus is at [docs/feature_progress.md](docs/feature_progress.md).
Historical detail has been moved to [docs/development_history.md](docs/development_history.md).
System-wide concerns live in [docs/project_scale.md](docs/project_scale.md).

---

## Current Development Focus

### 1. Retrieval foundation for reusable lesson material

Primary next feature: a unified lesson material database with:

- English as the canonical node language
- vector search as the primary retrieval mechanism
- metadata tags as the secondary filter / boost mechanism
- multilingual branches attached to shared canonical nodes

Source spec: [docs/vector_indexing.md](docs/vector_indexing.md)

### 2. Documentation structure hardening

The documentation model is now split into:

- `progress_report.md` — active feature development only
- `docs/development_history.md` — completed work and chronology
- `docs/project_scale.md` — system-level scope, scale, and roadmap concerns
- `docs/architecture.md` — compact arc42-style architecture reference

### 3. Keep the lesson pipeline stable while adding retrieval

The retrieval work should integrate into `jlesson` with a safe fallback to the current
generation flow. Existing lesson generation, compilation, report generation, and video
rendering remain the production path until retrieval proves useful in real usage.

### 4. Evaluate internal suite / runtime-service boundaries without committing yet

An internal architecture concept is now under evaluation to reduce module coupling and
prepare future pipeline variants:

- `generation suite`
- `render suite`
- `runtime services`

This is documentation and boundary-evaluation work only. No implementation decision has
been made, and the current production modules remain authoritative.

---

## Current Baseline

### Implemented baseline

- Full 12-step lesson pipeline is wired into CLI
- Content persistence, asset compilation, touch compilation, video render, and markdown report are working
- Sentence review step is in place to improve naturalness before downstream stages
- Passive and active touch profiles are implemented
- Unit test baseline remains strong for the non-network, non-video path

### Working assumption

The current application already has a stable content generation and rendering spine.
The next feature wave should therefore improve content retrieval and reuse, not replace
the existing pipeline prematurely.

---

## LLM Optimization Audit

This audit concentrates on the project’s prompt/response workflow, cache traceability,
and lesson artifact associations.

Key findings so far:

- The local LLM cache is a simple prompt-hash store (`~/.jlesson/cache`) with prompt
  text and raw JSON response pairs. It does not record step provenance, prompt version,
  model or schema metadata, or lesson/curriculum linkage.
- Current lesson output artifacts (`output/**/curriculum*.json`) capture lesson structure
  and vocabulary but do not preserve prompt or response metadata at the block level.
- A quick audit found 878 cached response entries, 228 prompt files, and 228 matched
  prompt/response pairs. That leaves 650 response-only cached entries without an
  associated saved prompt text, which is a major traceability gap.
- Prompt builders are expressive and rich, but some of the prompt text is very long and
  may be brittle for larger lessons or models with constrained context windows.
- The JSON parser pipeline is permissive and relies on heuristics. There is a risk of
  silent failure if the LLM returns invalid JSON, extra commentary, or structure drift.

First optimization priorities:

1. Add a traceable prompt/response metadata layer or lesson-generation log.
2. Strengthen output-schema enforcement for the major prompt types.
3. Reduce prompt size where possible by summarizing rather than fully enumerating
   large vocab/grammar pools.
4. Improve prompt cache semantics with versioning and step metadata.

Audit tooling:
- `tools/llm_audit.py` now scans `~/.jlesson/cache` and `output/` to summarize prompt/response
  traces and curriculum artifacts.
- The latest audit output is written to `output/llm_audit_summary.json`.

This report will be updated as the audit script and issue-tracing work proceed.

---

## Active Next Slice

### Slice A — Lean retrieval integration

Goal:
- integrate retrieval into `jlesson` in a way that can be turned on safely and bypassed cleanly

Expected output:
- a small retrieval module boundary
- canonical node and branch schemas
- optional retrieval step before LLM generation
- fallback to current generation when retrieval has insufficient coverage

Acceptance signals:
- no schema mismatch with `lesson_pipeline.py`
- lesson generation still succeeds when retrieval returns nothing useful
- retrieval traces can be logged for later evaluation

### Slice B — Spike 2 hardening

Before committing to a larger knowledge-base buildout:

- increase metadata-constrained query coverage
- add ambiguous cross-theme queries
- capture per-query-class quality notes
- document retrieval model/version/indexing parameters for every run

### Slice C — Vocabulary source hardening

The vocab source layer still needs protection before large-scale ingest:

- prevent accidental overwrite by default
- add or formalize difficulty metadata
- strengthen deduplication across themes

This remains important because retrieval quality depends on source-data quality.

### Slice D — Architecture boundary preparation

Goal:
- evaluate whether the current module graph should be reorganized around a small number
  of higher-level engines/services without committing to that structure yet

Expected output:
- concept notes in architecture documentation
- one decision-preparation document listing options, benefits, risks, and open questions
- no production architecture switch and no migration commitment yet

Acceptance signals:
- candidate boundaries are explicit enough to critique
- ambiguous ownership areas are listed instead of hidden
- follow-up refactors can be prioritized without pretending a decision already exists

---

## Active Constraints

### High-value constraints now

1. No canonical node / branch schema exists yet in production code.
2. Retrieval must not destabilize the current lesson pipeline.
3. Vocabulary files are still not optimized for large-scale reuse across themes.
4. Cross-platform font handling remains unresolved for broader portability.

### Deferred but visible constraints

1. Pipeline checkpointing is still missing for long LLM-driven lesson builds.
2. LLM client configuration still relies on a shared singleton model/client path.
3. Retrieval quality governance is not yet defined beyond structural validity.
4. Internal module ownership is improving, but the long-term composition model is not yet decided.

---

## Open Technical Debt Relevant To The Next Phase

### TD-05 — Cross-platform font support

Current state:
- Windows font paths are still effectively the happy-path rendering setup.

Why it matters now:
- retrieval and multilingual expansion increase the chance that this project will be
  exercised outside the current local Windows setup.

### TD-07 — Pipeline checkpointing

Current state:
- long lesson runs still fail as one large unit of work.

Why it matters now:
- retrieval integration adds more moving parts, making crash recovery more important.

### TD-09 — Vocab source durability and metadata

Current state:
- vocab files need stronger overwrite protection, richer metadata, and cross-theme dedup.

Why it matters now:
- retrieval quality will be bounded by source-data consistency and tagging quality.

---

## What Is Explicitly Not The Focus Right Now

- replacing curriculum progression logic
- building a full translation management platform
- gating branch publication on AI quality scoring
- broad multi-model orchestration work
- redesigning the existing lesson rendering pipeline

Those can return later if retrieval evidence justifies them.

---

## Current Recommended Order Of Work

1. Keep this documentation split in place and use it consistently.
2. Harden Spike 2 evaluation from [docs/vector_indexing.md](docs/vector_indexing.md).
3. Implement a lean retrieval integration with explicit fallback behavior.
4. Run multilingual branch projection against real retrieval traces.
5. Revisit checkpointing and vocab durability if retrieval becomes part of normal flow.

---

## Reference Documents

- [docs/architecture.md](docs/architecture.md) — compact architecture reference
- [docs/decision_engine_service_boundaries.md](docs/decision_engine_service_boundaries.md) — concept preparation for generator/render/storage split
- [docs/project_scale.md](docs/project_scale.md) — scale-oriented system view
- [docs/development_history.md](docs/development_history.md) — completed work and chronology
- [docs/software_engineering.md](docs/software_engineering.md) — process and working principles
- [docs/structure.md](docs/structure.md) — touch-system and repetition structure
- [docs/vector_indexing.md](docs/vector_indexing.md) — retrieval feature specification