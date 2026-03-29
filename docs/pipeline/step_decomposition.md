# Pipeline Step Decomposition

**Status:** Implemented  
**Date:** 2026-03-29  
**Migrated steps:** `generate_sentences`, `grammar_select`, `noun_practice`, `verb_practice`, `narrative_generator`, `extract_narrative_vocab`, `generate_narrative_vocab`

---

## Motivation

Every `PipelineStep.execute` method historically mixed three distinct concerns into one body:

1. **Iteration** — looping over blocks, batching items, deciding when to stop.
2. **I/O** — calling the LLM, reading retrieval results, writing to disk.
3. **Transformation** — building prompts, converting LLM responses to typed models.

This made steps hard to test in isolation (every test had to set up a full `LessonContext`
and patch deep into the step) and made iteration patterns duplicated across steps.

The decomposition separates these concerns without breaking existing steps.

---

## New Abstractions

Three new abstractions live in `pipeline_core.py` and `runtime/`.
All pre-existing `PipelineStep` subclasses continue to work unchanged.

```
runtime/
  interfaces.py        RuntimeServices protocol (I/O facade)
  _base.py             ContextRuntime (live implementation)

pipeline_steps/
  pipeline_core.py     ActionConfig, BlockChunk, ItemBatch,
                       StepAction[I,O], ActionStep[I,O]
```

---

### `RuntimeServices` — `jlesson/runtime/interfaces.py`

A structural `Protocol` (checked at runtime via `@runtime_checkable`) that
decouples step actions from the concrete `PipelineRuntime` and `LessonContext`.

```python
class RuntimeServices(Protocol):
    def call_llm(self, prompt: str) -> dict[str, Any]: ...

    def query_retrieval(self, theme: str, **kwargs) -> RetrievalResult: ...
    def update_retrieval(self, theme: str, items: list) -> None: ...

    def read_content(self, lesson_id: int) -> dict[str, Any]: ...
    def write_content(self, lesson_id: int, data: dict[str, Any]) -> None: ...

    def read_curriculum(self) -> CurriculumData: ...
    def write_curriculum(self, data: CurriculumData) -> None: ...

    def query_cache(self, key: str) -> dict[str, Any] | None: ...
    def update_cache(self, key: str, value: dict[str, Any]) -> None: ...
```

**Migration status** — only `call_llm` is fully wired in `ContextRuntime`;
the remaining operations raise `NotImplementedError` until the corresponding
steps are migrated.

---

### `ContextRuntime` — `jlesson/runtime/_base.py`

Concrete `RuntimeServices` backed by a live `LessonContext`.
Constructed once per `execute` call inside `ActionStep.execute`.

```python
class ContextRuntime:
    def __init__(self, ctx: LessonContext) -> None: ...
    def call_llm(self, prompt: str) -> dict[str, Any]: ...
    # remaining operations: NotImplementedError until migrated
```

`call_llm` delegates to `PipelineRuntime.ask_llm(ctx, prompt)`, preserving the
existing cache/direct routing based on `ctx.config.use_cache`.

---

### Typed chunk types

Two standard chunk types cover the two dominant iteration patterns across all steps.

#### `BlockChunk` — per-block iteration

Used by steps that make one LLM call per lesson block.

```python
@dataclass
class BlockChunk:
    block_index: int
    narrative: str
    nouns: list[GeneralItem]
    verbs: list[GeneralItem]
    grammar: list[GrammarItem]
```

Example steps: `generate_sentences`, `review_sentences` (future), `narrative_generator` (future).

#### `ItemBatch[T]` — batched-item iteration

Used by steps that process a flat list of items in fixed-size batches.

```python
@dataclass
class ItemBatch(Generic[T]):
    batch_index: int
    block_index: int   # -1 when items span multiple blocks
    items: list[T]
```

Example steps (future): `noun_practice` (25-item batches), `verb_practice` (20-item batches),
`review_sentences` (30-item batches).

---

### `ActionConfig` — per-invocation scope

Immutable configuration passed to every `StepAction.run` call.

```python
@dataclass
class ActionConfig:
    lesson: LessonConfig        # lesson-level settings (num_nouns, etc.)
    block_index: int            # 0-based block index for this invocation
    language: LanguageConfig    # language-pair prompts and generators
    runtime: RuntimeServices    # I/O facade
```

The action never touches `LessonContext` directly.

---

### `StepAction[I, O]` — stateless transformation

```python
class StepAction(ABC, Generic[I, O]):
    @abstractmethod
    def run(self, config: ActionConfig, chunk: I) -> O: ...
```

One implementation, one concern: map one typed input chunk to one typed output.
No iteration, no context mutation, no side effects beyond `config.runtime` calls.

---

### `ActionStep[I, O]` — iteration engine

`ActionStep` is a `PipelineStep` that drives a `StepAction` over a list of
typed input chunks.  Subclasses implement four declarative methods; the
inherited `execute` handles everything else.

```python
class ActionStep(PipelineStep, Generic[I, O]):
    @property
    @abstractmethod
    def action(self) -> StepAction[I, O]: ...

    @abstractmethod
    def should_skip(self, ctx: LessonContext) -> bool: ...

    @abstractmethod
    def build_chunks(self, ctx: LessonContext) -> list[I]: ...

    @abstractmethod
    def merge_outputs(self, ctx: LessonContext, outputs: list[O]) -> LessonContext: ...

    def execute(self, ctx: LessonContext) -> LessonContext:
        if self.should_skip(ctx):
            return ctx
        rt = ContextRuntime(ctx)
        for loop_index, chunk in enumerate(self.build_chunks(ctx)):
            block_index = getattr(chunk, "block_index", loop_index)
            cfg = ActionConfig(lesson=ctx.config, block_index=block_index,
                               language=ctx.language_config, runtime=rt)
            outputs.append(self.action.run(cfg, chunk))
        return self.merge_outputs(ctx, outputs)
```

The `block_index` for `ActionConfig` is read from `chunk.block_index` when the
attribute is present (`BlockChunk`, `ItemBatch`); it falls back to the loop index
for custom chunk types.

---

## Responsibility Map

| Concern | Owner |
|---------|-------|
| Idempotency guard | `ActionStep.should_skip` |
| Chunk decomposition | `ActionStep.build_chunks` |
| Iteration | `ActionStep.execute` (inherited) |
| Per-invocation config | `ActionConfig` (constructed by `ActionStep.execute`) |
| I/O (LLM, retrieval, cache) | `RuntimeServices` / `ContextRuntime` |
| Transformation logic | `StepAction.run` |
| Result assembly + ctx mutation | `ActionStep.merge_outputs` |

---

## Migrated Steps

| Step | Chunk type | Pattern |
|------|-----------|--------|
| `generate_sentences` | `BlockChunk` | one LLM call per lesson block |
| `grammar_select` | `GrammarSelectChunk` | single LLM call + pure post-processing |
| `noun_practice` | `NounPracticeBatch(ItemBatch[GeneralItem])` | batched LLM enrichment ×25 |
| `verb_practice` | `VerbPracticeBatch(ItemBatch[GeneralItem])` | batched LLM enrichment ×20 |

---

## Reference Implementations

### `generate_sentences` — per-block iteration (`BlockChunk`)

The reference for steps that make one LLM call per lesson block. See also
[step_narrative_grammar.md](step_narrative_grammar.md).

```
Input:   BlockChunk  (narrative, nouns, verbs, grammar for one block)
Output:  list[Sentence]
Action:  one call_llm per chunk
```

### `grammar_select` — single LLM call with pure post-processing

Demonstrates single-call steps where most of the complexity is in deterministic
transformation rather than I/O. The action performs three phases:

1. LLM call to get `selected_ids`
2. `_project_grammar` extension — fills the selection so multi-block lessons
   have enough grammar points to assign one per block
3. `_build_block_progression` — slices the extended list into per-block windows

```
Input:   GrammarSelectChunk  (unlocked grammar, nouns/verbs, lesson_number)
Output:  GrammarSelectResult (selected_grammar + selected_grammar_blocks)
Action:  one call_llm + deterministic extension + block slicing
```

`_project_grammar` and `_build_block_progression` are module-level pure functions
accessible to both the action (for post-processing) and the step (for `build_chunks`,
which needs `_project_grammar` to compute the unlocked set before the LLM call).

### `noun_practice` / `verb_practice` — batched enrichment (`ItemBatch`)

The reference for steps that call the LLM in fixed-size batches over a flat list
of items. `NounPracticeBatch` and `VerbPracticeBatch` extend `ItemBatch[GeneralItem]`
with `lesson_number` — an extra field that cannot be carried in `ActionConfig` alone
because it depends on curriculum state at execution time.

```
Input:   NounPracticeBatch / VerbPracticeBatch  (up to 25 / 20 items + lesson_number)
Output:  list[GeneralItem]  (enriched items for the batch)
Action:  one call_llm per batch chunk
```

`merge_outputs` concatenates all batch outputs, applies phase + block_index
assignment, and falls back to the raw input items when the LLM returns nothing.

### `narrative_generator` / `extract_narrative_vocab` — inter-step typed artifact (`NarrativeFrame`)

Demonstrates the dependency-aware flow goal: one generated artifact becomes the
typed input of the successor step rather than an implicit `list[str]` field on
`LessonContext`.

**`NarrativeFrame`** is defined in `pipeline_core.py` as the shared inter-step
type.  It is the output of `NarrativeGeneratorStep` and the direct input chunk
for `ExtractNarrativeVocabStep`.

```
NarrativeGeneratorStep
  Input chunk:  NarrativeGenChunk  (theme, lesson_number, lesson_blocks, seed_blocks)
  Output:       NarrativeFrame     (blocks: list[str])
  Action:       zero or one call_llm (skipped when seed_blocks covers all blocks)

ExtractNarrativeVocabStep
  Input chunk:  NarrativeFrame     ← direct output type of the preceding step
  Output:       list[NarrativeVocabBlock]
  Action:       one call_llm
```

The `build_chunks` of `ExtractNarrativeVocabStep` wraps `ctx.narrative_blocks`
in a `NarrativeFrame`:

```python
def build_chunks(self, ctx: LessonContext) -> list[NarrativeFrame]:
    if not ctx.narrative_blocks:
        return []
    return [NarrativeFrame(blocks=ctx.narrative_blocks)]
```

This makes the dependency visible in the type signature rather than buried in
prose documentation: any step whose `build_chunks` returns `list[NarrativeFrame]`
declares, at the type level, that it follows `NarrativeGeneratorStep`.

---

## Inter-Step Type Alignment

The decomposition pattern converges toward a dependency-aware flow where one
step's output type is the next step's chunk type.  The table below records the
current typed connections.

| Producing step | Artifact type | Consuming step |
|----------------|---------------|----------------|
| `NarrativeGeneratorStep` | `NarrativeFrame` | `ExtractNarrativeVocabStep` |
| `ExtractNarrativeVocabStep` | `NarrativeVocabPlan` | `GenerateNarrativeVocabStep` |

Goal: extend this table as more steps are migrated so that the pipeline's
dependency graph is expressed entirely through types, not through shared mutable
fields on `LessonContext`.

---

## Testing Actions in Isolation

With a `RuntimeServices` mock, a `StepAction` can be tested without a full
pipeline context:

```python
from unittest.mock import MagicMock
from jlesson.pipeline_steps.pipeline_core import ActionConfig, BlockChunk
from jlesson.pipeline_steps.generate_sentences.action import GenerateSentencesAction

def test_action_converts_llm_response():
    rt = MagicMock()
    rt.call_llm.return_value = {
        "sentences": [{
            "grammar_id": "action_present_affirmative",
            "english": "I eat bread.",
            "japanese": "私はパンを食べます。",
            "romaji": "watashi wa pan wo tabemasu",
            "person": "I",
        }]
    }
    config = ActionConfig(
        lesson=lesson_config,
        block_index=0,
        language=get_language_config("eng-jap"),
        runtime=rt,
    )
    chunk = BlockChunk(block_index=0, narrative="", nouns=[], verbs=[], grammar=[grammar])
    sentences = GenerateSentencesAction().run(config, chunk)

    assert len(sentences) == 1
    assert sentences[0].source.display_text == "I eat bread."
    rt.call_llm.assert_called_once()
```

---

## Migration Guide for Existing Steps

To migrate any existing `PipelineStep` to this pattern:

1. **Create `action.py`** — extract the core transformation into
   `YourAction(StepAction[ChunkType, OutputType])`.
   Replace `PipelineRuntime.ask_llm(ctx, prompt)` with `config.runtime.call_llm(prompt)`.

2. **Choose a chunk type** — `BlockChunk` for per-block steps,
   `ItemBatch[T]` for batched enrichment steps, or a custom `@dataclass`.

3. **Refactor `step.py`** — change the base class from `PipelineStep` to
   `ActionStep[ChunkType, OutputType]` and implement the four abstract methods.

4. **Update test patches** — change
   `"jlesson.pipeline_steps.<step>.step.PipelineRuntime.ask_llm"`
   to `"jlesson.runtime._base.PipelineRuntime.ask_llm"`.

5. **Wire `ContextRuntime`** — if the step uses retrieval, storage, or cache,
   implement the corresponding method in `ContextRuntime` before migrating.

---

## Migration Candidates

Steps ordered by iteration pattern clarity and migration effort.

| Step | Chunk type | LLM calls | Status |
|------|-----------|-----------|--------|
| `generate_sentences` | `BlockChunk` | 1 per block | **done** |
| `noun_practice` | `NounPracticeBatch(ItemBatch)` | batched ×25 | **done** |
| `verb_practice` | `VerbPracticeBatch(ItemBatch)` | batched ×20 | **done** |
| `grammar_select` | `GrammarSelectChunk` | 1 | **done** |
| `narrative_generator` | `NarrativeGenChunk` | 0–1 | **done** — emits `NarrativeFrame` |
| `extract_narrative_vocab` | `NarrativeFrame` ← from `narrative_generator` | 1 | **done** — emits `NarrativeVocabPlan` |
| `generate_narrative_vocab` | `NarrativeVocabPlan` ← from `extract_narrative_vocab` | 1 per batch | **done** — emits `VocabFile` |
| `review_sentences` | `ItemBatch[Sentence]` | batched ×30 | not started |
| `generate_narrative_vocab` | `ItemBatch[str]` | batched ×60 | not started |
| `select_vocab` | per-block + LLM gap-fill | conditional | not started |
| `retrieve_material` | single query | retrieval only | not started (needs `query_retrieval` wired) |
| `register_lesson` | no LLM | storage only | not started (needs `write_curriculum` wired) |
| `persist_content` | no LLM | storage only | not started (needs `write_content` wired) |
