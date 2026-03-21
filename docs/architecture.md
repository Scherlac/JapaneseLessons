# Japanese Learning Material — Architecture

Status: Current reference  
Style: Minimal arc42-inspired structure  
Updated: 2026-03-21

---

## 1. Introduction And Goals

The system generates structured Japanese lessons that combine:

- curriculum-aware grammar progression
- theme-based vocabulary selection
- LLM-assisted sentence and practice generation
- repeated touches compiled into learning outputs
- narrated video and markdown lesson artifacts

Primary quality goals:

1. Keep the pipeline understandable and inspectable.
2. Preserve a stable lesson-generation path while adding new capabilities.
3. Separate content generation, compilation, and rendering concerns.
4. Make future retrieval and multilingual expansion possible without rewriting the whole app.

---

## 2. Constraints

- Python-first implementation with relatively small dependency surface
- local JSON files instead of a database for the current production path
- OpenAI-compatible LLM backends, with LM Studio as the main tested setup
- FFmpeg-backed media output
- current local Windows environment is the most exercised rendering platform

---

## 3. Context And Scope

### External actors and systems

| Actor / system | Role |
|----------------|------|
| Learner / operator | Runs CLI commands to generate lessons or vocab |
| LM Studio / OpenAI-compatible API | Produces structured content and revisions |
| Edge TTS service | Generates spoken audio clips |
| FFmpeg / moviepy | Encodes video output |
| File system | Stores vocab, curriculum state, lesson content, assets, and outputs |

### System boundary

Inside this repository:

- curriculum logic
- prompt construction
- LLM client behavior
- lesson pipeline orchestration
- asset compilation and touch sequencing
- report and video rendering

Outside the current production boundary:

- durable semantic database
- vector index service
- hosted web application
- user scoring / spaced-repetition runtime

---

## 4. Solution Strategy

The system uses a layered, staged strategy:

1. Select or generate lesson content.
2. Persist lesson content before expensive downstream rendering.
3. Compile required assets for each item.
4. Compile touches from items according to a profile.
5. Render format-specific outputs from the touch sequence.

Key strategic choices:

- use explicit intermediate data structures instead of ad-hoc rendering dicts
- keep profile behavior declarative so repetition logic stays separate from output code
- keep the current pipeline operational while future retrieval is added as an upstream enhancer

---

## 5. Building Block View

### Candidate future internal architecture (under evaluation)

The current codebase still reflects a module-first evolution. A candidate next
internal architecture is being evaluated to reduce coupling and make future
multilingual, retrieval, and rendering variants easier to compose.

This candidate introduces three higher-level seams:

| Candidate component | Intended role | Likely current modules |
|---------------------|---------------|------------------------|
| `generation suite` | configure and connect specialised generation steps from a selected profile/request | `item_generator.py`, `vocab_generator.py`, `prompt_template.py` |
| `render suite` | configure and connect specialised render/compilation steps from a selected profile/request | `touch_compiler.py`, `asset_compiler.py`, `profiles.py`, `video/` |
| `runtime services` | runtime-facing retrieval, persistence, cache, and state access used by pipeline steps | `retrieval.py`, `llm_cache.py`, `llm_client.py`, `curriculum.py`, `lesson_store.py` |

Current interpretation of the candidate:

- the CLI would talk to suite configurators first
- configured suites would then be passed into the orchestrator
- the orchestrator would assemble and run the final pipeline
- runtime services would be used mainly by configured pipeline steps during execution

The main complexity in a suite is not simply grouping modules. It is expressing which specialised
steps produce intermediate outputs, which later steps consume them, and whether the profile is a
simple step list or a more explicit step graph.

The suite itself would not own the concrete generation or rendering work. Its primary role would
be to configure specialised steps and connect them into an execution-ready flow.

Example under evaluation:

- narrative frame generation
- sentence generation constrained by grammar progression and the narrative
- coherence review over the generated narrative lesson content

Important status note:

- this is a concept evaluation only
- no architectural decision has been made yet
- existing production orchestration remains the source of truth

Key expected benefits if adopted:

1. make pipeline assembly more declarative
2. separate content-generation concerns from rendering concerns
3. reduce direct dependency pressure on orchestration modules
4. create clearer plugin seams for future rendering variants

Current risks under evaluation:

1. the term `engine` may hide too many responsibilities if boundaries are not strict
2. `runtime services` may become an over-broad bucket if curriculum and retrieval are forced together prematurely
3. render plugins need a stable intermediate representation or the abstraction will leak
4. a step-producing architecture adds indirection and may not be worth it unless multiple concrete pipelines are really needed

### Top-level modules

| Module | Responsibility |
|--------|----------------|
| `jlesson/cli.py` | CLI entry point and command dispatch |
| `jlesson/curriculum.py` | Grammar progression and curriculum state |
| `jlesson/prompt_template.py` | Pure prompt builders |
| `jlesson/llm_client.py` | OpenAI-compatible LLM communication |
| `jlesson/llm_cache.py` | File-based cache for LLM responses |
| `jlesson/models.py` | Core typed lesson and compilation models |
| `jlesson/lesson_pipeline.py` | Application orchestration across stages |
| `jlesson/lesson_store.py` | Persist / load lesson content |
| `jlesson/profiles.py` | Touch-profile definitions |
| `jlesson/asset_compiler.py` | Render cards and audio per item |
| `jlesson/touch_compiler.py` | Build ordered touch sequences |
| `jlesson/video/cards.py` | Card rendering |
| `jlesson/video/tts_engine.py` | TTS generation |
| `jlesson/video/builder.py` | MP4 assembly |
| `jlesson/lesson_report.py` | Markdown lesson reports |

### Structural decomposition

```text
CLI
  -> lesson pipeline
      -> curriculum + prompt templates + LLM client
      -> lesson content persistence
      -> asset compilation
      -> touch compilation
      -> output renderers
```

Detailed touch and profile semantics live in [structure.md](structure.md).
Decision preparation for the candidate suite/runtime-services split lives in
[decision_engine_service_boundaries.md](decision_engine_service_boundaries.md).

---

## 6. Runtime View

### Main lesson generation flow

1. CLI receives `lesson next` request.
2. Curriculum selects next lesson scope and grammar progression.
3. Vocab is selected or generated as needed.
4. LLM generates sentences and practice content.
5. Sentence review optionally revises low-quality outputs.
6. Lesson content is persisted to `output/<lesson_id>/content.json`.
7. Assets are compiled for the chosen profile.
8. Touch sequence is compiled.
9. Video and markdown outputs are rendered from the compiled touches.

### Future retrieval-enhanced flow

Planned upstream insertion point:

1. Retrieve canonical candidates.
2. Project requested branch content.
3. Fall back to current generation if retrieval coverage is insufficient.
4. Continue through the existing lesson pipeline unchanged downstream.

---

## 7. Deployment View

### Current deployment style

- local CLI execution
- local JSON-backed repository state
- local output directory for generated artifacts
- external LLM and TTS services called over network interfaces

### Important runtime artifacts

| Path | Purpose |
|------|---------|
| `vocab/` | source vocabulary files |
| `curriculum/` | curriculum progression state |
| `output/<lesson_id>/content.json` | persisted lesson content |
| `output/` | rendered assets and lesson outputs |
| `docs/` | architecture, decisions, history, scale documents |

---

## 8. Cross-Cutting Concepts

### Pipeline staging

The project prefers explicit phases and inspectable intermediate results over opaque end-to-end calls.

### Profiles and touches

Repetition policy is expressed through profiles and touch types so the same lesson content can feed different outputs.

### Documentation discipline

The documentation model is intentionally split:

- active work in [../progress_report.md](../progress_report.md)
- completed detail in [development_history.md](development_history.md)
- scale concerns in [project_scale.md](project_scale.md)
- architecture truth here

### Spike-before-scale

New high-uncertainty areas are explored in `spike/` before they become production architecture.

---

## 9. Risks And Technical Debt

### Current important risks

1. Retrieval integration could add complexity before schemas and boundaries are clear.
2. Long-running lesson generation still lacks checkpoint recovery.
3. Rendering portability is limited by Windows-centered font assumptions.
4. Theme-based vocab storage is not yet a strong long-term semantic content model.

### Current technical-debt priorities

1. TD-09 — vocab durability, metadata, and deduplication
2. TD-07 — pipeline checkpointing
3. TD-05 — cross-platform font configuration
4. TD-06 — reduce shared singleton behavior in LLM client configuration

---

## 10. Related Documents

- [../progress_report.md](../progress_report.md)
- [project_scale.md](project_scale.md)
- [development_history.md](development_history.md)
- [structure.md](structure.md)
- [vector_indexing.md](vector_indexing.md)
- `docs/decision_*.md` decision records