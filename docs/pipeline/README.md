# Lesson Pipeline

The lesson pipeline is a flat list of `PipelineStep` objects executed sequentially by
`run_pipeline()` in `pipeline_orchestrator.py`.  Each step receives a `LessonContext`,
mutates it, and returns it.  Steps are idempotent: if the relevant context fields are
already populated (e.g. from retrieval), the step skips its work and returns early.

---

## Runtime contracts

### `LessonConfig` — input (immutable)

| Field | Type | Purpose |
|---|---|---|
| `theme` | `str` | Lesson subject (e.g. "a day on a farm") |
| `curriculum_path` | `Path` | Path to `curriculum.json` |
| `lesson_blocks` | `int` | Number of narrative/content blocks (default 1) |
| `num_nouns` / `num_verbs` | `int` | Vocab counts per block |
| `sentences_per_grammar` | `int` | Sentences generated per grammar point |
| `grammar_points_per_lesson` | `int` | Grammar points selected per lesson |
| `narrative` | `list[str]` | Optional pre-written narrative blocks (CLI `--narrative`) |
| `language` | `str` | Language pair code, e.g. `"eng-jap"` |
| `profile` | `str` | Render profile name, e.g. `"passive_video"` |
| `seed` | `int \| None` | Random seed for reproducible vocab selection |
| `use_cache` / `dry_run` / `verbose` | `bool` | LLM cache, dry-run mode, verbose output |

### `LessonContext` — accumulated state (mutable)

| Field | Type | Set by |
|---|---|---|
| `curriculum` | `CurriculumData` | Orchestrator (pre-pipeline) |
| `vocab` | `dict` | `SelectVocabStep` |
| `nouns` / `verbs` | `list[GeneralItem]` | `SelectVocabStep` or `RetrieveLessonMaterialStep` |
| `narrative_blocks` | `list[str]` | `NarrativeGeneratorStep` |
| `narrative_vocab_terms` | `list[dict]` | `ExtractNarrativeVocabStep` |
| `selected_grammar` | `list[GrammarItem]` | `GrammarSelectStep` |
| `selected_grammar_blocks` | `list[list[GrammarItem]]` | `GrammarSelectStep` |
| `sentences` | `list[Sentence]` | `NarrativeGrammarStep` |
| `noun_items` / `verb_items` | `list[GeneralItem]` | `NounPracticeStep` / `VerbPracticeStep` |
| `compiled_items` | `list[CompiledItem]` | `CompileAssetsStep` |
| `touches` | `list[Touch]` | `CompileTouchesStep` |
| `lesson_id` | `int \| None` | `RegisterLessonStep` |
| `content_path` / `report_path` | `Path \| None` | `PersistContentStep` / `SaveReportStep` |
| `video_path` | `Path \| None` | `RenderVideoStep` |

---

## Step sequence (default full pipeline)

| # | Name | File | LLM | Reads | Writes |
|---|---|---|---|---|---|
| 1 | `retrieve_material` | `retrieve_material.py` | No | retrieval store | `nouns`, `verbs`, `sentences` |
| 2 | `select_vocab` | `select_vocab.py` | No | `curriculum`, vocab file | `nouns`, `verbs` |
| 3 | `narrative_generator` | `narrative_generator/` | **Yes** | `config.theme`, `curriculum`, `language_config` | `narrative_blocks` |
| 4 | `extract_narrative_vocab` | `extract_narrative_vocab.py` | **Yes** | `narrative_blocks` | `narrative_vocab_terms` |
| 5 | `grammar_select` | `grammar_select.py` | **Yes** | `curriculum`, `language_config` | `selected_grammar`, `selected_grammar_blocks` |
| 6 | `narrative_grammar` | `generate_sentences.py` | **Yes** | `nouns`, `verbs`, `narrative_blocks`, `selected_grammar*` | `sentences` |
| 7 | `review_sentences` | `review_sentences.py` | **Yes** | `sentences` | `sentences` (rewritten) |
| 8 | `noun_practice` | `noun_practice.py` | **Yes** | `nouns`, `curriculum` | `noun_items` |
| 9 | `verb_practice` | `verb_practice.py` | **Yes** | `verbs`, `curriculum` | `verb_items` |
| 10 | `register_lesson` | `register_lesson.py` | No | `noun_items`, `sentences`, `selected_grammar` | `curriculum` (persisted), `lesson_id` |
| 11 | `persist_content` | `persist_content.py` | No | `noun_items`, `sentences`, etc. | `content_path` |
| 12 | `save_report` | `save_report.py` | No | `report` | `report_path` |
| 13 | `compile_touches` | `compile_touches.py` | No | `noun_items`, `sentences`, `language_config` | `touches` |
| 14 | `compile_assets` | `compile_assets.py` | No | `touches` | `compiled_items` |
| 15 | `render_video` | `render_video.py` | No | `compiled_items`, `touches` | `video_path` |

---

## Runtime services

Steps call runtime services rather than directly importing low-level modules:

| Service | Location | Provides |
|---|---|---|
| `PipelineRuntime` | `runtime.py` | `ask_llm`, `read_json`, `write_json` |
| `PipelineGadgets` | `pipeline_gadgets.py` | `ask_llm`, `load_vocab` (legacy, to be migrated) |

`NarrativeGeneratorStep` is the first step fully migrated to `PipelineRuntime`.
All other LLM steps still use `PipelineGadgets` — migration is in progress.

---

## Data flow diagram

```
LessonConfig
     │
     ▼
[retrieve_material] ──────────────────────────────► nouns, verbs, sentences (if hit)
     │
     ▼
[select_vocab] ◄── curriculum.covered_*, vocab file
     │                                               ► nouns, verbs
     ▼
[narrative_generator] ◄── theme, curriculum, language_config
     │                                               ► narrative_blocks (list[str])
     ▼
[extract_narrative_vocab] ◄── narrative_blocks
     │                                               ► narrative_vocab_terms
     ▼
[grammar_select] ◄── curriculum.covered_grammar_ids
     │                                               ► selected_grammar, selected_grammar_blocks
     ▼
[narrative_grammar] ◄── nouns, verbs, narrative_blocks, selected_grammar_blocks
     │                                               ► sentences (list[Sentence])
     ▼
[review_sentences]                                   ► sentences (rewritten)
     │
     ▼
[noun_practice]  ► noun_items
[verb_practice]  ► verb_items
     │
     ▼
[register_lesson] ── persists curriculum.json        ► lesson_id
[persist_content] ── writes content.json             ► content_path
[save_report]    ── writes report.md                 ► report_path
     │
     ▼
[compile_touches] ► touches
[compile_assets]  ► compiled_items
[render_video]    ► video_path
```

---

## Step subpackage pattern

Steps with non-trivial language-specific configuration use a subpackage layout:

```
lesson_pipeline/
    narrative_generator/
        __init__.py     # re-exports NarrativeGeneratorStep
        step.py         # PipelineStep subclass
        config.py       # step-local NarrativeGeneratorLanguageConfig + builder
        prompt.py       # language-agnostic prompt builder
```

This pattern keeps step logic self-contained and removes the need for steps to
reach into `ctx.language_config.prompts` (the old `PromptInterface` coupling).

See [step_narrative_generator.md](step_narrative_generator.md) for a full breakdown
of the first step migrated to this pattern.

---

## Known technical debt (in-progress)

| Area | Status |
|---|---|
| `PipelineGadgets` → `PipelineRuntime` migration | In progress (narrative done) |
| `ctx.language_config.prompts` references in remaining steps | Not yet migrated |
| `ctx.language_config.generator` references in remaining steps | Not yet migrated |
