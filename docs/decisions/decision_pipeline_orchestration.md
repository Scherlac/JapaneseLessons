# Decision: Pipeline Orchestration

**Status:** Decided — lightweight dataclass pipeline (no framework)  
**Date:** 2026-03-15  
**Context:** The lesson generation pipeline (grammar select → sentence generate → noun practice →
verb practice → validate → TTS → render video) currently exists as unstructured procedural
code in `spike/spike_09_demo.py`. It needs to become a first-class production module (`lesson_pipeline.py`).
The question is whether to use a pipeline framework or build a minimal structure with stdlib.

---

## Current State

`spike_09_demo.py` contains a sequential script (~250 lines) that:
1. Loads vocab + curriculum
2. Calls `ask_llm_json_free()` for grammar select (12s)
3. Calls `ask_llm_json_free()` for sentence generate (21s)
4. Calls `ask_llm_json_free()` for noun practice (11s)
5. Renders TTS audio + video cards + MP4

Problems:
- Not modular — one script, no re-entry, no stages
- If the video render fails, all LLM work (44s) is lost
- Adding verb practice requires editing the script
- No progress visibility
- The CLI (`generate_lesson.py`) has no command to trigger it

---

## Options

### Option 1: No framework — dataclasses + linear functions

**What:** Define a `LessonContext` dataclass that accumulates state. Each pipeline stage is a
pure function: `stage(ctx: LessonContext) -> LessonContext`. The pipeline runner calls them
in sequence and can checkpoint between stages.

```python
@dataclass
class LessonContext:
    theme: str
    curriculum: dict
    vocab: dict
    selected_grammar: list[dict] = field(default_factory=list)
    sentences: list[dict] = field(default_factory=list)
    noun_items: list[dict] = field(default_factory=list)
    verb_items: list[dict] = field(default_factory=list)
    audio_paths: list[Path] = field(default_factory=list)
    video_path: Path | None = None
    stage_reached: str = "init"

def stage_grammar_select(ctx: LessonContext) -> LessonContext: ...
def stage_sentence_generate(ctx: LessonContext) -> LessonContext: ...
def stage_noun_practice(ctx: LessonContext) -> LessonContext: ...
def stage_verb_practice(ctx: LessonContext) -> LessonContext: ...
def stage_render(ctx: LessonContext) -> LessonContext: ...

PIPELINE: list[Callable] = [
    stage_grammar_select,
    stage_sentence_generate,
    stage_noun_practice,
    stage_verb_practice,
    stage_render,
]

def run_pipeline(ctx: LessonContext) -> LessonContext:
    for stage in PIPELINE:
        ctx = stage(ctx)
        checkpoint(ctx)   # save ctx to disk after each stage
    return ctx
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib dataclasses |
| **Checkpointing** | Manual JSON serialise/deserialise of `LessonContext` |
| **Stage skipping** | Check `ctx.stage_reached`; skip already-done stages |
| **Parallelism** | Not needed — stages depend on prior outputs |
| **Observability** | Depends on logging/progress implementation |
| **Testing** | Each stage is a pure function — easy to unit-test |

**Pros:** KISS; no new dependency; each stage is testable; context dataclass makes state explicit  
**Cons:** Checkpointing must be hand-rolled; no retry logic built-in

---

### Option 2: `prefect` (NOT INSTALLED)

**What:** Modern workflow orchestration platform. `@task` + `@flow` decorators.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install prefect` (~60MB, significant) |
| **Checkpointing** | Built-in — task results are cached to Prefect backend |
| **Retry** | `@task(retries=3, retry_delay_seconds=5)` |
| **Observability** | Web UI dashboard, task states, logs |
| **Async** | Native async support |

```python
from prefect import task, flow

@task(retries=2)
def grammar_select(vocab, curriculum): ...

@flow
def lesson_pipeline(theme): ...
```

**Pros:** Production-grade; retry/checkpoint built-in; UI for monitoring  
**Cons:** Heavy install (~60MB); requires server or Prefect Cloud; complete overkill for a 5-stage linear pipeline with no branching, no parallelism, and no scheduling

---

### Option 3: `dagster` (NOT INSTALLED)

**What:** Data-oriented pipeline framework with asset graph model.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install dagster` (~200MB) |
| **Model** | Asset-based: each stage produces a durable asset |
| **UI** | Full Dagster UI (Dagit) |

**Pros:** Very powerful for complex pipelines with many dependencies  
**Cons:** Extreme overkill; huge install; learning curve; designed for data engineering workflows, not interactive CLI tools

---

### Option 4: `luigi` (NOT INSTALLED)

**What:** Spotify's task dependency framework. Build pipelines by defining `requires()` and `output()`.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install luigi` (~5MB) |
| **Model** | Task classes with `requires()` for DAG + `output()` for file targets |
| **Checkpointing** | File-based — tasks are skipped if output file exists |

**Pros:** Lightweight vs prefect/dagster; file-based checkpointing aligns with our JSON-per-stage approach  
**Cons:** Object-oriented task classes add boilerplate; overkill for a linear pipeline; not actively developed; no reason to add a dependency when Option 1 achieves the same

---

## Decision: Dataclasses + linear functions (Option 1) ✅

**Rationale:**
- The pipeline is **strictly linear** — no branching, no fan-out, no DAG
- We have **exactly 5 stages** with clear inputs/outputs
- No new dependency needed — stdlib `dataclasses` + `json` covers checkpointing
- Each stage function is unit-testable in isolation
- Adding/removing a stage is a one-line change to the `PIPELINE` list
- Prefect/Dagster/Luigi are solutions to problems we don't have (scheduling, distributed execution, asset tracking across teams)

**Implementation plan:**

1. Create `lesson_pipeline.py` with:
   - `LessonContext` dataclass (accumulates all pipeline state)
   - One function per stage (`stage_grammar_select`, `stage_sentence_generate`, etc.)
   - `run_pipeline(ctx) -> LessonContext` — sequential runner with checkpointing
   - `checkpoint(ctx, path)` — serialises context to JSON after each stage
   - `load_checkpoint(path) -> LessonContext | None` — resume from partial run

2. Wire into CLI via `jlesson lesson next` (click command)

3. All LLM calls, TTS generation, and video rendering are delegated to existing modules —
   `lesson_pipeline.py` is orchestration only, containing no domain/render logic itself.

**Checkpoint strategy:**
- After each stage write `output/<lesson_id>/.checkpoint.json`
- On resume, read checkpoint and skip stages already in `ctx.stage_reached`
- Delete checkpoint on successful completion
- Addresses TD-07 (no error recovery in long pipelines)
