# Japanese Learning Material — Progress Report

> **Architect review**: 2026-03-15  
> Historical spike details and model evaluation results → [`docs/development_history.md`](docs/development_history.md)

---

## Project Goal

Build a CLI tool that generates structured Japanese lessons combining vocabulary and grammar
with high repetition.  The tool supports LLM-enhanced generation for natural sentences and
renders each lesson as a narrated MP4 video.

Core principles: Cohesion / Coupling / Composition / YAGNI / KISS / DRY, spike-before-scale, no over-engineering.

---

## Current Status (2026-03-15)

| Area | Status |
|------|--------|
| Grammar progression model (15 steps, levels 1-4) | ✅ Done |
| Vocabulary database (food + travel) | ✅ Done |
| LLM prompt templates (8 functions) | ✅ Done |
| LLM client (OpenAI-compatible, JSON extraction) | ✅ Done |
| Vocab generator (LLM-driven + schema validation) | ✅ Done |
| Curriculum / lesson dictionary CRUD | ✅ Done |
| TTS engine (edge-tts) | ✅ Done |
| Video card renderer (Pillow 1080p) | ✅ Done |
| Video assembler (moviepy + FFmpeg) | ✅ Done |
| Unit test suite (184 unit / 204 total) | ✅ Done |
| End-to-end demo: 2 lessons, LLM + video render | ✅ Done |
| **Full pipeline wired into CLI** | ✅ Done — `lesson_pipeline.py` + `jlesson lesson next` |
| **Lesson content persistence** | ✅ Done — `lesson_store.py` → `output/<id>/content.json` |
| **Verb practice step in pipeline** | ✅ Done — stage 5 of 8 in pipeline |
| CLI refactored to click subcommands | ✅ Done — `vocab` / `lesson` / `curriculum` groups |
| Pydantic data models (`models.py`) | ✅ Done — `NounItem`, `VerbItem`, `Sentence`, `LessonContent` |
| **`PERSONS` tuple standardised (TD-08)** | ✅ Done — `PERSONS_BEGINNER` now 3-tuple; all prompt builders consistent |
| **Seeded vocab shuffle (TD-04)** | ✅ Done — `suggest_new_vocab(seed=)` uses local RNG; CLI `--seed` wired through |
| **LLM response cache (`llm_cache.py`)** | ✅ Done — `ask_llm_cached()`, `--no-cache` flag; sha256 file cache; stdlib only |
| Unit test suite (254 unit / 274 total) | ✅ Done — +22 tests for cache + shuffle |
| **Markdown lesson report (`lesson_report.py`)** | ✅ Done — `generate_report()`, mirrors video structure; `--dry-run` flag |
| Unit test suite (279 unit / 299 total) | ✅ Done — +25 tests for report |
| **Compilation pipeline models** | ✅ Done — `Phase`, `TouchType`, `TouchIntent`, `RepetitionStep`, `ItemAssets`, `CompiledItem`, `Touch` |
| **Profile system (`profiles.py`)** | ✅ Done — `passive_video` (3+2 cycles) + `active_flash_cards` (5+3 cycles); touch-type ↔ asset mappings |
| **Asset compiler (`asset_compiler.py`)** | ✅ Done — Stage 2: sync (cards only) + async (cards + TTS); profile-driven asset selection |
| **Touch compiler (`touch_compiler.py`)** | ✅ Done — Stage 3: round-robin interleaved touch sequence from compiled items + profile |
| **Touch-system card renderers** | ✅ Done — `render_en_card`, `render_jp_card`, `render_bilingual_card` in `cards.py` |
| Unit test suite (366 unit / 392 total) | ✅ Done — +87 tests for compilation pipeline |
| **Compilation pipeline wired into lesson_pipeline.py** | ✅ Done — `CompileAssetsStep` (stage 9) + `CompileTouchesStep` (stage 10); `RenderVideoStep` reads from touch sequence; 12-step pipeline |
| **`--profile` CLI option** | ✅ Done — `passive_video` (default) / `active_flash_cards`; flows through `LessonConfig.profile` |
| **Multi-audio video clips (`builder.py`)** | ✅ Done — `create_multi_audio_clip()` supports sequential audio tracks per card |
| **Profile-aware lesson report** | ✅ Done — `SaveReportStep._summary()` uses `count_touches()` with actual profile |
| Unit test suite (388 unit / 414 total) | ✅ Done — +22 tests for pipeline integration |
| **Sentence review step (TD-10)** | ✅ Done — `ReviewSentencesStep` (step 4); `build_sentence_review_prompt()`; naturalness scoring + LLM rewrite; 12-step pipeline |
| Unit test suite (424 unit / 437 total) | ✅ Done — +23 tests for review step |

---

## Architecture

```
jlesson/                        ← all production Python source
├── __init__.py
├── cli.py                      ← click subcommands (was generate_lesson.py)
├── config.py                   ← LLM connection parameters
├── models.py                   ← NEW: pydantic schemas for all data shapes
├── curriculum.py               ← grammar progression + lesson dictionary CRUD
├── prompt_template.py          ← LLM prompt builder (7 pure functions)
├── vocab_generator.py          ← LLM vocab generation + schema validation
├── llm_client.py               ← OpenAI-compatible HTTP client
├── llm_cache.py                ← NEW: sha256 file cache for dev
├── lesson_pipeline.py          ← LessonContext + 12-step pipeline (compile + render)
├── lesson_store.py             ← NEW: output/<id>/content.json I/O
├── lesson_report.py            ← NEW: Markdown lesson report generator
├── profiles.py                 ← NEW: touch profile definitions (passive_video, active_flash_cards)
├── asset_compiler.py           ← NEW: Stage 2 — render cards + TTS per item
├── touch_compiler.py           ← NEW: Stage 3 — profile-driven touch sequencing
├── video/
│   ├── __init__.py
│   ├── tts_engine.py           ← edge-tts async wrapper
│   ├── cards.py                ← Pillow 1920×1080 card renderer (was video_cards.py)
│   └── builder.py             ← moviepy/FFmpeg assembler (was video_builder.py)
└── exporters/                  ← NEW: format adapters
    ├── __init__.py
    ├── video_exporter.py
    ├── anki_exporter.py
    └── text_exporter.py

vocab/                          ← vocabulary source data (stays at root)
curriculum/                     ← lesson-progress state (stays at root)
tests/                          ← unit test suite (imports update to jlesson.X)
spike/                          ← proof-of-concept scripts (spike_01–spike_09)
docs/                           ← decision documents + development history
output/                         ← generated artifacts (gitignored)
```

### Module Responsibilities

| Module | Responsibility | Coupling |
|--------|---------------|---------|
| `jlesson/curriculum.py` | Grammar progression table; lesson dictionary CRUD; vocab selection | Data only — no LLM, no I/O |
| `jlesson/prompt_template.py` | Build LLM prompt strings from vocab + grammar specs | Pure functions — no project imports |
| `jlesson/models.py` | Pydantic schemas: `Noun`, `Verb`, `VocabFile`, `LessonContent`, `Person` | `pydantic` only |
| `jlesson/vocab_generator.py` | LLM vocab generation + schema validation + file save | Calls `llm_client`, `prompt_template` |
| `jlesson/llm_client.py` | OpenAI-compatible HTTP client; JSON extraction; think-stripping | Calls `config` |
| `jlesson/llm_cache.py` | File-based LLM response cache (dev mode) | stdlib only |
| `jlesson/config.py` | LLM connection parameters (env-overridable) | stdlib + dotenv |
| `jlesson/lesson_pipeline.py` | `LessonContext` dataclass + 12 pipeline steps + `run_pipeline()` | Application layer — composes all others |
| `jlesson/lesson_report.py` | Markdown report generator — mirrors video lesson structure | `models` only |
| `jlesson/profiles.py` | Touch profile definitions; touch-type → asset mappings; repetition cycles | `models` only |
| `jlesson/asset_compiler.py` | Stage 2: render card images + TTS audio per item based on profile | `models`, `profiles`, `video.cards`, `video.tts_engine` |
| `jlesson/touch_compiler.py` | Stage 3: compile interleaved touch sequence from compiled items + profile | `models`, `profiles` |
| `jlesson/lesson_store.py` | `save_lesson_content()` / `load_lesson_content()` | stdlib only |
| `jlesson/video/tts_engine.py` | edge-tts async audio generation | Third-party only |
| `jlesson/video/cards.py` | Pillow card rendering (1920×1080 PNG) | Third-party only |
| `jlesson/video/builder.py` | moviepy/FFmpeg clip assembly → MP4 | Third-party only |
| `jlesson/cli.py` | click subcommand groups + command dispatch | Imports pipeline, curriculum, vocab_generator |

---

## Software Design Principles

**Design principles:**
- **High cohesion** — each module has one responsibility
- **Low coupling** — modules communicate via well-defined interfaces; no circular dependencies
- **Composition** — composition over inheritance; implementations are composed 
- **YAGNI** — focus on implementing the required features; don't reinvent the wheel; 
- **KISS** — keep complexity in check; readable code; 
- **DRY** — avoid duplication; generalize patterns into cohesive modules/functions
- **Spike-before-scale** — validate technology choices with minimal code before building full features
- **Performance** — LLM calls, video rendering, and TTS are inherently slow; keeping an optimal quality / performance balance is a key design consideration.


## Development Cycle

This project follows an **iterative, research-driven development cycle** designed for solo development with high documentation standards:

### Cycle Phases

1. **Research & Design** 📋
   - Define problem and requirements
   - Research technology options
   - Document decisions in `docs/` 
   - Design architecture and data structures

2. **Spike Implementation** 🔬
   - Create minimal proof-of-concept scripts (`spike/`)
   - Validate technology choices
   - Reduce risk before full implementation
   - Document findings and key learnings

3. **Core Development** 🛠️
   - Implement production-ready features
   - Adhere to software design principles (high cohesion, low coupling, composition, etc.)
   - Keep dependencies minimal (stdlib-first)
   - Write pure functions with clear interfaces

4. **Testing & Validation** ✅
   - Manual testing of all CLI commands
   - Verify output formats and functionality
   - Test edge cases and error conditions
   - Document test results

5. **Documentation & Planning** 📝
   - Update progress report with completed work, maintained technical debts. 
   - Document architecture and design decisions
   - Plan next iteration's scope
   - Maintain comprehensive README

6. **Repository Management** 🌳
   - Organize code into modules and directories
   - Use version control effectively (commits, branches)
   - Keep generated outputs gitignored
   - Ensure reproducibility with fixed seeds and documented dependencies

### Cycle Characteristics

- **Documentation-first**: Every decision and implementation is documented before/after
- **Spike-before-scale**: Prove concepts with minimal code before building full features
- **Incremental delivery**: Working features over big releases
- **Validation-driven**: Test and verify at each step
- **Research-heavy**: Technology decisions are well-researched and documented

---

## Dependencies

### Core (stdlib only)
`json`, `random`, `pathlib`, `hashlib`

### CLI
`click` — subcommand groups, `CliRunner` for tests (already installed)

### Video Pipeline
| Library | Version | Purpose |
|---------|---------|---------|
| edge-tts | 7.2.7 | Neural TTS — ja-JP-NanamiNeural |
| Pillow | 12.0.0 | Card rendering |
| moviepy | 2.1.2 | Video composition |
| ffmpeg | 4.3.1 | Video encoding backend |

### LLM
| Library | Version | Purpose |
|---------|---------|---------|
| openai | 2.28.0 | Universal client (LM Studio / OpenAI / Ollama) |

### System Fonts (Windows)
- `C:/Windows/Fonts/YuGothB.ttc` — Japanese text (fallback: `msgothic.ttc`)
- `C:/Windows/Fonts/segoeui.ttf` / `segoeuib.ttf` — English text

### LLM Provider (Local)
- LM Studio (OpenAI-compatible endpoint); default model `qwen/qwen3-14b`
- `json_schema` structured output required (LM Studio rejects `json_object`)
- Recommended model: `qwen/qwen3-14b` — best Japanese quality; 6.5s avg JSON response
- See [`docs/development_history.md`](docs/development_history.md) for full model evaluation table

---

## Unit Test Suite

```
pytest tests/ -m "not integration and not internet and not video"
→ 424 passed, 13 deselected in 61.81s
```

| Test file | Unit tests | Slow markers |
|-----------|-----------|------|
| `test_curriculum.py` | 43 | — |
| `test_prompt_template.py` | 53 | — |
| `test_llm_client.py` | 20 | 14 `integration` |
| `test_video_cards.py` | 43 | — |
| `test_tts_engine.py` | 25 | 4 `internet` |
| `test_video_builder.py` | 19 | 2 `video` |
| `test_vocab_generator.py` | 19 | — |
| `test_lesson_store.py` | 19 | — |
| `test_lesson_pipeline.py` | 64 | — |
| `test_llm_cache.py` | 18 | — |
| `test_lesson_report.py` | 27 | — |
| `test_profiles.py` | 29 | — |
| `test_touch_compiler.py` | 22 | — |
| `test_asset_compiler.py` | 23 | — |

---

## Technical Debt

### ~~TD-01 — Pipeline not in CLI~~  ✅ RESOLVED
`lesson_pipeline.py` implements `LessonConfig` + `LessonContext` + 8 stage functions +
`run_pipeline()`. CLI command `jlesson lesson next --theme <T>` triggers the full pipeline.
Spike_09 is retained as reference only.

### ~~TD-02 — No lesson content persistence~~  ✅ RESOLVED
`lesson_store.py` exposes `save_lesson_content()` / `load_lesson_content()`. Pydantic models
in `models.py` define the schema. Content is saved to `output/<id>/content.json` as stage 7
of the pipeline — before video render, so LLM work survives render failures.

### ~~TD-03 — Verb practice not wired~~  ✅ RESOLVED
`stage_verb_practice()` is now stage 5 of the pipeline, calling `build_verb_practice_prompt()`
and persisting results to `LessonContent.verb_items`.

### ~~TD-04 — `suggest_new_vocab` is deterministic / ordered~~  ✅ RESOLVED
`suggest_new_vocab()` now accepts an optional `seed: int | None = None` keyword
argument. When provided, a `random.Random(seed)` local instance shuffles the fresh
noun/verb pools without touching global random state. `seed=None` (default) preserves
original list order — all existing tests pass unchanged. The `seed` value flows from
`LessonConfig.seed` through `stage_select_vocab` and is also exposed via
`jlesson lesson next --seed`.

### TD-05 — Windows-only font paths hardcoded  `MEDIUM`
`video_cards.py` contains `C:/Windows/Fonts/YuGothB.ttc`. Fails silently on Linux/macOS with
a fallback to a lower-quality font.  
**Fix**: Abstract font paths into `config.py` with platform detection; document Noto Sans JP
download as the cross-platform alternative (decision already made in `decision_fonts_rendering.md`).

### TD-06 — Global singleton in `llm_client.py`  `LOW`
`get_llm_client()` returns a module-level `_client` singleton. All callers share one `LLM_MODEL`
and one connection config. Makes multi-model workflows and isolated testing harder.  
**Fix**: Pass an `LLMClient` instance explicitly to functions that need it, or accept optional
`client=` kwargs. Low priority while the project remains single-model.

### TD-07 — No error recovery in long pipelines  `LOW` (now) → `HIGH` (production)
If an LLM call fails mid-lesson (timeout, OOM, network drop), the entire pipeline crashes with
no checkpoint. All prior LLM work is lost.  
**Fix**: Write a checkpoint file after each stage in `lesson_pipeline.py`; re-load and skip
completed stages on re-run. See `decision_pipeline_orchestration.md` for the strategy.

### ~~TD-08 — `PERSONS` tuple format inconsistency~~  ✅ RESOLVED
`PERSONS_BEGINNER` is now a `list[tuple[str, str, str]]` matching the 3-tuple format
(label, japanese, romaji) used by `build_grammar_generate_prompt`. All prompt builder
functions now have consistent type signatures; `person_block` formatting renders
`"  - I: 私 (watashi)"` correctly.

### TD-09 — Vocab generation overwrites and lacks difficulty metadata  `MEDIUM`
`generate_vocab()` writes to `vocab/<theme>.json` unconditionally — re-running for an
existing theme silently overwrites the file, losing any previous words. Additionally:
- **No difficulty level** — words have no beginner/intermediate/advanced tag, so the
  generator cannot filter by learner level.
- **No deduplication across themes** — the LLM has no awareness of words already
  generated in other theme files, risking duplicates (e.g. "water" in both food and travel).
- **Curriculum tracks covered words** via `covered_nouns` / `covered_verbs` in
  `curriculum.json`, so lesson-level deduplication works — but the vocab *source files*
  themselves have no such guard.

**Fix options:**
1. Merge-on-save: load existing file, union new words, write back.
2. Add a `level` field (beginner/intermediate/advanced) per word in the vocab schema.
3. Pass existing word lists to the LLM prompt so it avoids repeats.
4. Warn (or abort) when the target file already exists unless `--force` is passed.

### ~~TD-10 — Sentence generation produces nonsensical combinations~~  ✅ RESOLVED
`ReviewSentencesStep` is now step 4 of the 12-step pipeline, inserted between
`GenerateSentencesStep` (step 3) and `NounPracticeStep` (step 5).

**Approach taken:** Option 1 — Review/lector step.

`build_sentence_review_prompt()` in `prompt_template.py` sends all generated sentences
back to the LLM along with the grammar specs and vocabulary pool. The LLM rates each
sentence 1–5 for naturalness. Sentences scoring below 3 are rewritten using the same
grammar pattern but with better-fitting vocabulary combinations. The step:

- Adds one LLM call (~6.5s) per lesson — acceptable quality/performance tradeoff
- Skips the call entirely when there are no sentences (zero cost for empty pipelines)
- Is individually testable and purely additive (no restructuring of existing steps)
- Logs revised sentences and adds a "Sentence Review" section to the lesson report
- Guards against out-of-bounds indices, null revisions, and non-dict responses

Original analysis and alternative options preserved below for reference.

<details>
<summary>Original analysis (superseded)</summary>

The pipeline selects nouns (step 1), verbs (step 1), and grammar points (step 2)
independently, then asks the LLM to generate sentences combining all three (step 3).
Because each selection is made without considering the others, the LLM is sometimes
forced to combine words and grammar patterns that don't fit naturally — producing
awkward or nonsensical sentences (e.g. forcing an existence pattern with action verbs,
or pairing unrelated nouns with transitive verbs).

**Root cause:** no feedback loop — the pipeline is strictly forward (select → generate),
with no validation or revision pass on the generated output.

**Fix options (not mutually exclusive):**
1. **Review/lector step** ← IMPLEMENTED
2. **Grammar-aware vocab selection** — after selecting grammar points, filter the vocab
   pool to items that pair naturally with those patterns before finalising the noun/verb
   selection. Requires reordering steps 1 and 2.
3. **Joint generation** — instead of selecting vocab first and grammar second, give the
   LLM the full pool and let it pick a coherent subset of nouns + verbs + grammar in one
   call. Reduces control but improves naturalness.
4. **Sentence-level retry** — if a generated sentence fails a quality heuristic (e.g.
   short length, repeated words, missing expected particles), retry that sentence with
   a more constrained prompt.

</details>

---

## Compilation Pipeline Design

The rendering side of the pipeline follows a **three-stage transformation**,
each producing an explicit, inspectable data structure. This replaces the
current approach where `_build_video_items` constructs ad-hoc dicts and
`_render_async` reads/writes folders directly.

```
item_sequence  ──→  compiled_items  ──→  touch_sequence  ──→  output
   (raw data)       (items + assets)     (ordered touches)    (video / report / anki)
```

Touch system domain concepts (profiles, touch types, repetition cycles) are
defined in [`docs/structure.md`](docs/structure.md).

### Stage 1 — Item Sequence (steps 1–8, already implemented)

Raw lesson items (nouns, verbs, sentences) with LLM-enriched data.
Persisted as `output/<id>/content.json` by `PersistContentStep`.

```
ItemSequence = list[NounItem | VerbItem | Sentence]
```

### Stage 2 — Compiled Items (asset rendering) ✅ IMPLEMENTED

For each item, render the unique assets required by the profile's touch types.
Assets are rendered once per item and de-duplicated across touches.
Implemented in `asset_compiler.py` with sync (cards-only) and async (cards+TTS) modes.

```
CompiledItem
  ├── item          NounItem | VerbItem | Sentence
  ├── phase         "nouns" | "verbs" | "grammar"
  └── assets
        ├── card_en       Path | None
        ├── card_jp       Path | None
        ├── card_en_jp    Path | None
        ├── audio_en      Path | None
        ├── audio_jp_f    Path | None
        └── audio_jp_m    Path | None
```

This is the **quality-control checkpoint** — every card image and audio clip
exists on disk and can be inspected before proceeding.

### Stage 3 — Touch Sequence (profile-driven ordering) ✅ IMPLEMENTED

The compiler reads the repetition cycles and produces a flat, ordered list of
touches — interleaved by round — ready for output rendering.
Implemented in `touch_compiler.py`. Profile definitions in `profiles.py`.

```
Touch
  ├── compiled_item   ref → CompiledItem
  ├── touch_index     1-based within the item's cycle
  ├── touch_type      "en→jp" | "listen:en,jp-m,jp-f" | …
  ├── intent          "introduce" | "recall" | "reinforce" | …
  ├── card_path       Path   (resolved from compiled_item.assets)
  └── audio_paths     list[Path]  (resolved, ordered for playback)
```

Separating Stage 2 from Stage 3 means:
- Changing repetition cycles or interleaving does **not** re-render assets.
- Multiple profiles can share the **same compiled items**.

### Stage 4 — Output Rendering (format-specific)

| Output format | Deliverable | Reads from each touch |
|--------------|-------------|------------------------|
| Video (MP4) | Clips assembled in sequence order | card PNG + audio MP3s |
| Lesson report (Markdown) | Structured `.md` file | item metadata + touch intent |
| Anki export (TSV / `.apkg`) | Flashcard deck | card images + audio + text fields |

Fast and repeatable — re-running with a different format does not re-render.

### Pipeline Step Mapping

```
Steps 1–8:  content generation + persistence     (unchanged, produces item_sequence)
Step 9:     compile_assets    — Stage 2: item_sequence → compiled_items
Step 10:    compile_touches   — Stage 3: compiled_items + profile → touch_sequence
Step 11:    render_video      — Stage 4: touch_sequence → MP4
Step 12:    save_report       — Stage 4: touch_sequence → Markdown
```

`compile_assets` is item-aware (renders cards and TTS).  
`compile_touches` is profile-aware (reads the rulebook).  
Stage 4 steps are format-aware but profile-agnostic.

**Integration status:** ✅ WIRED — `CompileAssetsStep` (step 9), `CompileTouchesStep`
(step 10), `RenderVideoStep` (step 11, reads from touch sequence), `SaveReportStep`
(step 12, profile-aware summary). `--profile` option on CLI. 22 new tests.

---

## Anticipated Next Features (Ranked by Value)

### Priority 1 — High value, natural next steps

1. ~~**Touch system + compilation pipeline**~~ ✅ DONE — `models.py` (7 new types),
   `profiles.py` (2 profiles, touch-type mappings), `asset_compiler.py` (Stage 2),
   `touch_compiler.py` (Stage 3), 3 new card renderers in `cards.py`. 87 new tests.

2. ~~**Wire compilation pipeline into lesson_pipeline.py**~~ ✅ DONE — `CompileAssetsStep`
   + `CompileTouchesStep` added as steps 8–9; `RenderVideoStep` reads from touch sequence;
   `SaveReportStep` uses profile-aware `count_touches()`; `--profile` CLI option;
   `create_multi_audio_clip()` in VideoBuilder. 22 new tests.

3. **Passive video profile** — Listen-first touch types (`listen:en,jp-m,jp-f`,
   `listen:jp-f,jp-m`, `listen:en,jp-f`). The profile is defined; requires wiring the
   video builder to render multi-audio touches (sequential audio clips per card).

4. **More vocab themes** — animals, school, weather, work, time, numbers  
   Expands learning surface; each theme is one `--create-vocab <theme>` call away.
   Blocked by TD-09 (overwrite risk, no difficulty level, no cross-theme dedup).

5. **Anki export** — `.apkg` or Anki-compatible CSV  
   High retention value; consumes compiled items from Stage 2. Requires `genanki`.
   Design: see [`docs/decision_anki_export.md`](docs/decision_anki_export.md).

### Priority 2 — Quality improvements

5. **Interactive text review mode** — CLI-based: show English, learner types romaji/Japanese  
   Alternative to video for quick review. Consumes touch sequence.

6. **Progress tracking + scoring** — correct/incorrect per item, due-date scheduling  
   Moves toward spaced-repetition. Needs lesson runner first.

7. **Cross-platform font support** (TD-05)  
   Low complexity; unblocks non-Windows use.

### Priority 3 — Infrastructure

8. **Pipeline checkpointing** (TD-07) — crash resilience for long LLM runs
9. **Multi-model flag** — `--model <id>` override per invocation

---

## Package Research Decisions (2026-03-15)

Seven areas researched. Key finding: `click`, `pydantic`, `python-dotenv`, and `rich` are
**already installed** — four major decisions cost zero new dependencies.

| Area | Decision | Install cost | Document |
|------|----------|-------------|---------|
| CLI framework | **`click`** — subcommand groups, `CliRunner` for tests | 0 (already installed) | [decision_cli_framework.md](docs/decision_cli_framework.md) |
| Pipeline orchestration | **Dataclasses + linear functions** — `LessonContext` + stage functions | 0 (stdlib) | [decision_pipeline_orchestration.md](docs/decision_pipeline_orchestration.md) |
| Persistence / storage | **JSON per-lesson files** — `output/<id>/content.json` | 0 (stdlib) | [decision_persistence.md](docs/decision_persistence.md) |
| LLM response caching | **Custom file cache** — `sha256(prompt)` → `output/.cache/<hash>.json` | 0 (stdlib) | [decision_caching.md](docs/decision_caching.md) |
| Config + data validation | **`python-dotenv`** for `.env` files; **`pydantic` v2** models for all schemas | 0 (both already installed) | [decision_config_validation.md](docs/decision_config_validation.md) |
| Progress + logging | **`rich`** — spinners + `TimeElapsedColumn` for pipeline stages; `RichHandler` for logs | 0 (already installed) | [decision_progress_logging.md](docs/decision_progress_logging.md) |
| Anki export | **TSV** (interim, 0 cost) → **`genanki`** (polished `.apkg` with audio) | `pip install genanki` when ready | [decision_anki_export.md](docs/decision_anki_export.md) |

### Packages to install when needed
- `genanki` — only when Anki export is implemented (Priority 2)

### New modules implied by these decisions
| Module | Purpose | Status |
|--------|---------|--------|
| `models.py` | Pydantic models for all data shapes | ✅ Done |
| `lesson_pipeline.py` | Pipeline orchestrator with `LessonContext` dataclass + stage functions | ✅ Done |
| `lesson_store.py` | `save_lesson_content()` / `load_lesson_content()` | ✅ Done |
| `llm_cache.py` | `ask_llm_cached()` — file-based dev cache for LLM calls | ✅ Done |
| `profiles.py` | Touch profiles (passive_video, active_flash_cards) + touch-type mappings | ✅ Done |
| `asset_compiler.py` | Stage 2 — compile card images + TTS audio per item | ✅ Done |
| `touch_compiler.py` | Stage 3 — compile interleaved touch sequence | ✅ Done |

---

## Project Structure Decision (2026-03-15)

Full analysis in [`docs/decision_project_structure.md`](docs/decision_project_structure.md).

**Decision:** Move all production Python source into a `jlesson/` package with `video/` and
`exporters/` sub-packages. Replace `py-modules` in `pyproject.toml` with `packages.find`.
Rename CLI entry point from `japanese-lesson` → `jlesson`.

**Migration status:** DONE — all files in `jlesson/` package; entry point is `jlesson`.

| Change | Detail |
|--------|--------|
| Package directory | `jlesson/` at project root (flat layout, no `src/`) |
| Sub-packages | `jlesson/video/` (3 modules), `jlesson/exporters/` (3 new modules) |
| Renamed files | `generate_lesson.py` → `cli.py`; `video_cards.py` → `cards.py`; `video_builder.py` → `builder.py` |
| `pyproject.toml` | `py-modules` → `packages.find`; entry point `jlesson = "jlesson.cli:main"` |
| All 7 test files | Flat imports → `from jlesson.X import ...` / `from jlesson.video.X import ...` |
| Files deleted | `requirements.txt` (redundant), `progress_report_prev.md` (archived) |
| Files moved | `structure.md` → `docs/structure.md` |
| Path fix | `VOCAB_DIR` in `cli.py`: `parent` → `parent.parent` (one level up from `jlesson/`) |

**Migration prerequisite:** complete before implementing TD-01 (`lesson_pipeline.py`) and TD-02
(`lesson_store.py`) — new modules belong in `jlesson/`, not at the root.

---

## Architectural Concepts to Introduce Next

### 1. `lesson_pipeline.py` — Pipeline Orchestrator
The lesson generation workflow currently exists only as procedural code in `spike_09_demo.py`.
It needs to become a first-class module with a clear entry point:

```python
def run_lesson(theme, curriculum, config) -> LessonResult:
    # grammar select → sentence generate → noun practice → verb practice → validate → render
```

This module composes the existing `curriculum`, `prompt_template`, `llm_client`, `tts_engine`,
`video_cards`, and `video_builder` modules. It is the "application layer" sitting above the
domain and infrastructure layers.

### 2. `lesson_store.py` — Content Storage Layer
Currently there is no persistence for generated lesson text. A store module should:
- Write `output/<lesson_id>/content.json` with noun_items + sentences
- Expose `load_lesson_content(lesson_id)` for re-render and export
- Keep `curriculum.json` as the index; content files as the payloads

### 3. Export Adapter Pattern — `exporters/`
Multiple output formats are planned (MP4 video, Anki, plain-text review). Rather than
embedding format logic in the pipeline, define a clean exporter interface:

```
exporters/
  video_exporter.py     ← wraps tts_engine + video_cards + video_builder
  anki_exporter.py      ← produces .apkg or CSV
  text_exporter.py      ← Markdown / terminal review
```

The pipeline calls `exporter.export(lesson_content, output_dir)` regardless of format.

### 4. CLI Subcommand Refactor
The current flat argparse structure will become unmaintainable as flags grow. Migrate to
subcommands:

```
python generate_lesson.py vocab list
python generate_lesson.py vocab create <theme>
python generate_lesson.py lesson next [--theme food]
python generate_lesson.py lesson render <id>
python generate_lesson.py lesson export <id> --format anki
python generate_lesson.py curriculum show
```

---

## Installation

```powershell
.\install.ps1   # installs edge-tts, ffmpeg (conda-forge), openai
```

> Run all commands in an already-activated conda environment.
> Do **not** use `conda run` — it buffers output until exit, hiding LLM progress.
