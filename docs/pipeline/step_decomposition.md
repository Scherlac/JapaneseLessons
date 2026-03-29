# Pipeline Step Decomposition

**Status:** Implemented  
**Date:** 2026-03-29  
**Reference implementation:** `generate_sentences` step

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

## Reference Implementation: `generate_sentences`

The `generate_sentences` step is the canonical reference for the per-block
iteration pattern.

### Files

```
jlesson/pipeline_steps/generate_sentences/
  action.py   ← GenerateSentencesAction  (new — pure transformation)
  step.py     ← NarrativeGrammarStep     (refactored — ActionStep subclass)
  config.py   ← NarrativeGrammarLanguageConfig (unchanged)
  prompt.py   ← build_grammar_sentences_prompt (unchanged)
```

### `GenerateSentencesAction` — `action.py`

```
Input:  BlockChunk  (narrative, nouns, verbs, grammar for one block)
Output: list[Sentence]
I/O:    config.runtime.call_llm(prompt)  — one LLM call per chunk
```

Has no knowledge of `LessonContext`.  Can be tested with any object that
satisfies `RuntimeServices`.

### `NarrativeGrammarStep` — `step.py`

```
should_skip:    return bool(ctx.sentences)   # retrieval pre-populated
build_chunks:   one BlockChunk per lesson block, slicing nouns/verbs/grammar
merge_outputs:  ctx.sentences = flatten(outputs); add grammar_practice report section
```

No iteration loop, no `PipelineRuntime` import, no direct LLM call.

### Before / after comparison

**Before (all concerns mixed in `execute`)**

```python
class NarrativeGrammarStep(PipelineStep):
    def execute(self, ctx):
        if ctx.sentences:             # guard
            return ctx
        for block_index in range(total_blocks):   # iteration
            prompt = build_grammar_sentences_prompt(...)  # transformation
            result = PipelineRuntime.ask_llm(ctx, prompt) # I/O
            for s in result["sentences"]:                 # transformation
                ctx.sentences.append(...)
        ctx.report.add(...)           # assembly
        return ctx
```

**After (concerns separated)**

```python
# action.py — transformation + I/O only
class GenerateSentencesAction(StepAction[BlockChunk, list[Sentence]]):
    def run(self, config, chunk):
        prompt = build_grammar_sentences_prompt(...)
        result = config.runtime.call_llm(prompt)    # I/O via facade
        return [convert(s) for s in result["sentences"]]

# step.py — structure only
class NarrativeGrammarStep(ActionStep[BlockChunk, list[Sentence]]):
    action = GenerateSentencesAction()

    def should_skip(self, ctx):   return bool(ctx.sentences)
    def build_chunks(self, ctx):  return [BlockChunk(...) for i in range(blocks)]
    def merge_outputs(self, ctx, outputs):
        ctx.sentences = flatten(outputs)
        ctx.report.add(...)
        return ctx
```

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

| Step | Chunk type | LLM calls | Migration effort |
|------|-----------|-----------|-----------------|
| `noun_practice` | `ItemBatch[GeneralItem]` | batched ×25 | low |
| `verb_practice` | `ItemBatch[GeneralItem]` | batched ×20 | low |
| `review_sentences` | `ItemBatch[Sentence]` | batched ×30 | low |
| `extract_narrative_vocab` | single `BlockChunk` list | 1 | low |
| `grammar_select` | single chunk | 1 | medium |
| `narrative_generator` | single chunk | 1 | medium |
| `generate_narrative_vocab` | `ItemBatch[str]` | batched ×60 | medium |
| `select_vocab` | per-block + LLM gap-fill | conditional | high |
| `retrieve_material` | single query | retrieval only | high (needs `query_retrieval` wired) |
| `register_lesson` | no LLM | storage only | high (needs `write_curriculum` wired) |
| `persist_content` | no LLM | storage only | high (needs `write_content` wired) |
