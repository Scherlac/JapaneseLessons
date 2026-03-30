# Pipeline Step Decomposition

**Status:** Implemented  
**Date:** 2026-03-29  
**Migrated steps:** `generate_sentences`, `grammar_select`, `noun_practice`, `verb_practice`, `narrative_generator`, `extract_narrative_vocab`, `generate_narrative_vocab`, `select_vocab`, `review_sentences`, `compile_assets`, `compile_touches`, `render_video`, `save_report`, `register_lesson`, `persist_content`

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

    def load_vocab(self, theme: str, vocab_dir: Path | None = None) -> VocabFile: ...

    def read_content(self, lesson_id: int) -> dict[str, Any]: ...
    def write_content(self, lesson_id: int, data: dict[str, Any]) -> Path: ...

    def read_curriculum(self) -> CurriculumData: ...
    def write_curriculum(self, data: CurriculumData) -> None: ...

    def query_cache(self, key: str) -> dict[str, Any] | None: ...
    def update_cache(self, key: str, value: dict[str, Any]) -> None: ...
```

**Migration status** — `call_llm`, `load_vocab`, `read_curriculum`,
`write_curriculum`, `read_content`, and `write_content` are wired in
`ContextRuntime`.
Retrieval and cache operations still raise `NotImplementedError` until the
corresponding steps are migrated.

---

### `ContextRuntime` — `jlesson/runtime/_base.py`

Concrete `RuntimeServices` backed by a live `LessonContext`.
Constructed once per `execute` call inside `ActionStep.execute`.

```python
class ContextRuntime:
    def __init__(self, ctx: LessonContext) -> None: ...
    def call_llm(self, prompt: str) -> dict[str, Any]: ...
    def load_vocab(self, theme: str, vocab_dir: Path | None = None) -> VocabFile: ...
    def read_curriculum(self) -> CurriculumData: ...
    def write_curriculum(self, data: CurriculumData) -> None: ...
    def read_content(self, lesson_id: int) -> dict[str, Any]: ...
    def write_content(self, lesson_id: int, data: dict[str, Any]) -> Path: ...
    # retrieval/cache operations: NotImplementedError until migrated
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

Example steps: `generate_sentences`.

#### `ItemBatch[T]` — batched-item iteration

Used by steps that process a flat list of items in fixed-size batches.

```python
@dataclass
class ItemBatch(Generic[T]):
    batch_index: int
    block_index: int   # -1 when items span multiple blocks
    items: list[T]
```

Example steps: `noun_practice` (25-item batches), `verb_practice` (20-item batches),
`review_sentences` (30-item batches).

#### Composite chunk types — when one action needs more than one input

The standard chunk types are intentionally small, but an aligned step does not
need to depend on exactly one upstream field.  When a step needs multiple
inputs, define a custom `@dataclass` chunk that preserves the main predecessor
artifact while carrying the extra context needed for the action.

Examples:

- `GrammarSelectChunk` keeps the lesson-wide grammar selection call explicit while carrying nouns, verbs, unlocked grammar, and lesson number.
- `SentenceReviewBatch` extends `ItemBatch[Sentence]` so the successor step still advertises that it consumes `Sentence`, even though the prompt also needs nouns, verbs, and grammar context.
- `BlockChunk` is already a composite setup artifact: narrative + nouns + verbs + grammar for one block.

Rule of thumb: keep the predecessor artifact visible in the chunk's type
signature, and add the other dependencies as fields on the chunk rather than
reading them imperatively from `LessonContext` inside the action.

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
| `select_vocab` | `SelectVocabRequest` | single vocab selection pass producing a typed successor artifact |
| `register_lesson` | `RegisterLessonRequest` | single storage write producing a typed registration artifact |
| `compile_assets` | `AssetCompileRequest` | single render compilation producing a typed successor artifact |
| `compile_touches` | `CompiledItemSequence` | single pure transform from compiled items to touch sequence |
| `render_video` | `RenderVideoRequest(TouchSequence)` | single render sink consuming the typed touch sequence |
| `save_report` | `SaveReportRequest(RenderedVideoArtifact)` | single sink write consuming the rendered-video artifact |
| `persist_content` | `PersistContentRequest` | single storage write consuming the typed registration artifact |

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

### `select_vocab` — bridge from `VocabFile` to grammar selection

This makes the vocabulary bridge dependency-aware instead of leaving it as a
context-only mutation. `SelectVocabRequest` keeps the predecessor `VocabFile`
visible while carrying the narrative term plan and curriculum coverage needed
to choose fresh lesson vocab.

`SelectVocabAction` emits `SelectedVocabSet`, and `GrammarSelectChunk` now
extends that artifact so the successor step advertises the dependency in its
type signature.

```
GenerateNarrativeVocabStep
    Output:        VocabFile

SelectVocabStep
    Input chunk:   SelectVocabRequest    (VocabFile + narrative plan + curriculum coverage)
    Output:        SelectedVocabSet      (vocab + nouns + verbs)
    Action:        load-or-reuse vocab + select narrative-aware fresh items

GrammarSelectStep
    Input chunk:   GrammarSelectChunk    (SelectedVocabSet + grammar progression state)
```

### `compile_touches` — render-side successor artifact (`CompiledItemSequence`)

Demonstrates the same dependency-aware flow on the render side: compiled render
items are wrapped in a typed artifact that becomes the direct input chunk of the
successor step.

**`CompiledItemSequence`** is defined in `pipeline_core.py` as the render-side
handoff artifact. It is the natural output type of `CompileAssetsStep` and the
direct input chunk for `CompileTouchesStep`.

```
CompileAssetsStep
    Output field:  ctx.compiled_items
    Target type:   CompiledItemSequence   (items: list[CompiledItem])

CompileTouchesStep
    Input chunk:   CompiledItemSequence   ← successor boundary made explicit
    Output:        TouchSequence          (items: list[Touch])
    Action:        one pure compile_touches call
```

### `compile_assets` — render predecessor aligned to `compile_touches`

This completes the render-side seam by making the predecessor step emit the same
typed artifact that the successor step consumes.

`AssetCompileRequest` is a step-local composite chunk that gathers the lesson's
reviewed sentences and enriched vocab into one render-compilation request. The
important aligned boundary is the output: `CompileAssetsAction` returns
`CompiledItemSequence`, and `CompileTouchesStep` consumes exactly that artifact
type.

```
CompileAssetsStep
    Input chunk:   AssetCompileRequest   (items_by_phase + lesson_dir + dry_run)
    Output:        CompiledItemSequence  (items: list[CompiledItem])
    Action:        one sync/async asset compiler call

CompileTouchesStep
    Input chunk:   CompiledItemSequence  ← direct output type of the preceding step
    Output:        TouchSequence         (items: list[Touch])
```

This is the target pattern for later migrations: even when a step needs a
composite request shape, its output should converge on a stable artifact that a
successor can consume directly.

### `render_video` — successor aligned to `compile_touches`

This extends the same render-side typed chain one step further. The core
predecessor artifact remains visible: `RenderVideoRequest` extends
`TouchSequence`, so the step signature still declares that video rendering is a
successor of touch compilation.

`RenderVideoAction` emits `RenderedVideoArtifact`, a typed sink result that can
be used by a later `save_report` migration instead of relying only on
`LessonContext.video_path`.

```
CompileTouchesStep
    Output:        TouchSequence          (items: list[Touch])

RenderVideoStep
    Input chunk:   RenderVideoRequest     (TouchSequence + lesson_dir)
    Output:        RenderedVideoArtifact  (video_path + render side artifacts)
    Action:        one video builder call
```

### `save_report` — successor aligned to `render_video`

This extends the terminal render chain to the final report sink. The core
predecessor artifact remains visible: `SaveReportRequest` extends
`RenderedVideoArtifact`, so the step signature still declares that report
finalisation follows the render-video result.

`SaveReportAction` emits `ReportArtifact`, which is the terminal report-output
artifact for the pipeline.

```
RenderVideoStep
    Output:        RenderedVideoArtifact  (video_path + render side artifacts)

SaveReportStep
    Input chunk:   SaveReportRequest      (RenderedVideoArtifact + report state)
    Output:        ReportArtifact         (report_path)
    Action:        one markdown render + file write
```

### `register_lesson` — predecessor aligned to `persist_content`

This opens the storage-side typed chain. `RegisterLessonAction` emits a
`LessonRegistrationArtifact` that carries the stable lesson identity and
creation timestamp needed by content persistence.

`RegisterLessonRequest` is still a composite request because lesson
registration depends on multiple finalized inputs, but the output is now a
stable artifact that a later `PersistContentStep` migration can consume
directly.

```
RegisterLessonStep
    Input chunk:   RegisterLessonRequest   (theme + nouns + verbs + grammar + counts)
    Output:        LessonRegistrationArtifact  (lesson_id + created_at + curriculum)
    Action:        one curriculum update + save

PersistContentStep
    Future input:  LessonRegistrationArtifact + finalized lesson content
```

### `persist_content` — successor aligned to `register_lesson`

This continues the storage-side typed chain. `PersistContentRequest` keeps the
registration artifact visible while adding the finalized lesson content fields
needed for persistence.

`PersistContentAction` emits `PersistedContentArtifact`, which makes the
content-write boundary explicit instead of relying only on
`LessonContext.content_path`.

```
RegisterLessonStep
    Output:        LessonRegistrationArtifact  (lesson_id + created_at + curriculum)

PersistContentStep
    Input chunk:   PersistContentRequest       (LessonRegistrationArtifact + finalized content)
    Output:        PersistedContentArtifact    (created_at + content_path + vocab_path)
    Action:        one lesson-content write + shared vocab update
```

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
| `GenerateNarrativeVocabStep` | `VocabFile` (via `SelectVocabRequest`) | `SelectVocabStep` |
| `SelectVocabStep` | `SelectedVocabSet` | `GrammarSelectStep` |
| `NarrativeGrammarStep` | `Sentence` (via `SentenceReviewBatch`) | `ReviewSentencesStep` |
| `RegisterLessonStep` | `LessonRegistrationArtifact` | `PersistContentStep` |
| `CompileAssetsStep` | `CompiledItemSequence` | `CompileTouchesStep` |
| `CompileTouchesStep` | `TouchSequence` | `RenderVideoStep` |
| `RenderVideoStep` | `RenderedVideoArtifact` | `SaveReportStep` |

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
| `review_sentences` | `SentenceReviewBatch(ItemBatch[Sentence])` ← from `generate_sentences` | batched ×30 | **done** — successor step; chunk item type = `Sentence` (output of `NarrativeGrammarStep`) |
| `register_lesson` | `RegisterLessonRequest` | 1 storage write | **done** — predecessor step; emits `LessonRegistrationArtifact` for later `persist_content` alignment |
| `compile_assets` | `AssetCompileRequest` | 1 sync/async render call | **done** — predecessor step; emits `CompiledItemSequence` for `compile_touches` |
| `compile_touches` | `CompiledItemSequence` ← from `compile_assets` | 1 pure transform | **done** — successor step; chunk type wraps predecessor render artifact |
| `render_video` | `RenderVideoRequest(TouchSequence)` ← from `compile_touches` | 1 sink render call | **done** — successor step; chunk type preserves `TouchSequence` as the predecessor artifact |
| `save_report` | `SaveReportRequest(RenderedVideoArtifact)` ← from `render_video` | 1 sink write | **done** — successor step; chunk type preserves `RenderedVideoArtifact` as the predecessor artifact |
| `generate_narrative_vocab` | `ItemBatch[str]` | batched ×60 | not started |
| `select_vocab` | `SelectVocabRequest` ← from `generate_narrative_vocab` | conditional vocab load + gap-fill | **done** — bridge step; emits `SelectedVocabSet` for `grammar_select` |
| `retrieve_material` | single query | retrieval only | not started (needs `query_retrieval` wired) |
| `persist_content` | `PersistContentRequest` ← from `register_lesson` | storage only | **done** — successor step; request preserves `LessonRegistrationArtifact` as the predecessor artifact |
