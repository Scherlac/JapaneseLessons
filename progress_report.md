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
| LLM prompt templates (7 functions) | ✅ Done |
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
| Unit test suite (232 unit / 252 total) | ✅ Done — +48 tests for new modules |

---

## Architecture

> **Migration pending** — current code is flat at project root. Planned package structure
> documented in [`docs/decision_project_structure.md`](docs/decision_project_structure.md).
> The tree below shows the target state after migration.

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
├── lesson_pipeline.py          ← NEW: LessonContext + stage functions
├── lesson_store.py             ← NEW: output/<id>/content.json I/O
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
| `jlesson/config.py` | LLM connection parameters (env-overridable) | stdlib only |
| `jlesson/lesson_pipeline.py` | `LessonContext` dataclass + stage functions + `run_pipeline()` | Application layer — composes all others |
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
`argparse`, `json`, `random`, `pathlib`

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
- LM Studio on `localhost:1234`; default model `qwen/qwen3-14b`
- `json_schema` structured output required (LM Studio rejects `json_object`)
- Recommended model: `qwen/qwen3-14b` — best Japanese quality; 6.5s avg JSON response
- See [`docs/development_history.md`](docs/development_history.md) for full model evaluation table

---

## Unit Test Suite

```
pytest tests/ -m "not integration and not internet and not video"
→ 232 passed, 20 deselected in 6.85s
```

| Test file | Unit tests | Slow markers |
|-----------|-----------|------|
| `test_curriculum.py` | 42 | — |
| `test_prompt_template.py` | 37 | — |
| `test_llm_client.py` | 20 | 14 `integration` |
| `test_video_cards.py` | 29 | — |
| `test_tts_engine.py` | 22 | 4 `internet` |
| `test_video_builder.py` | 13 | 2 `video` |
| `test_vocab_generator.py` | 18 | — |
| `test_lesson_store.py` | 20 | — |
| `test_lesson_pipeline.py` | 28 | — |

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

### TD-04 — `suggest_new_vocab` is deterministic / ordered  `MEDIUM`
Always picks the first N fresh items in list order. Lessons will always use the same vocab
subset. Adding more themes won't help variety if the vocabulary selection never shuffles.  
**Fix**: Add optional seeded shuffle to `suggest_new_vocab()`; expose `seed` parameter in CLI.

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

### TD-08 — `PERSONS` tuple format inconsistency  `LOW`
`PERSONS_BEGINNER` in `prompt_template.py` is `list[tuple[str,str]]` (2-tuple).
`build_grammar_generate_prompt` expects `list[tuple[str,str,str]]` (3-tuple with romaji).
The correct format is documented but lives in `spike_09_demo.py` rather than the module.  
**Fix**: Standardise on 3-tuple in `prompt_template.py` constants and update tests. Pydantic
model for `Person` will enforce the format when `models.py` is introduced.

---

## Anticipated Next Features (Ranked by Value)

### Priority 1 — High value, unblocks everything
1. **Extract pipeline → `lesson_pipeline.py` + `--next-lesson` CLI flag**  
   Addresses TD-01. Makes the project usable without running spike scripts.

2. **Lesson content persistence** (TD-02)  
   Required before any export format (Anki, text review, re-render) is possible.

### Priority 2 — High value, natural next steps
3. **Verb practice step in pipeline** (TD-03)  
   All code already exists; purely a wiring task.

4. **More vocab themes** — animals, school, weather, work, time, numbers  
   Expands learning surface; each theme is one `--create-vocab <theme>` call away.

5. **Anki export** — `.apkg` or Anki-compatible CSV  
   High retention value; requires content persistence (item 2) first.

### Priority 3 — Quality improvements
6. **Interactive text review mode** — CLI-based: show English, learner types romaji/Japanese  
   Alternative to video for quick review. Requires content persistence.

7. **Progress tracking + scoring** — correct/incorrect per item, due-date scheduling  
   Moves toward spaced-repetition. Needs lesson runner first.

8. **Cross-platform font support** (TD-05)  
   Low complexity; unblocks non-Windows use.

### Priority 4 — Infrastructure
9. **Pipeline checkpointing** (TD-07) — crash resilience for long LLM runs
10. **`suggest_new_vocab` shuffle** (TD-04) — lesson variety as vocab grows
11. **Multi-model flag** — `--model <id>` override per invocation

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
| Module | Purpose | Key dependencies |
|--------|---------|-----------------|
| `models.py` | Pydantic models for all data shapes (Noun, Verb, VocabFile, LessonContent…) | `pydantic` |
| `lesson_pipeline.py` | Pipeline orchestrator with `LessonContext` dataclass + stage functions | `rich` |
| `lesson_store.py` | `save_lesson_content()` / `load_lesson_content()` | stdlib |
| `llm_cache.py` | `ask_llm_cached()` — file-based dev cache for LLM calls | stdlib |

---

## Project Structure Decision (2026-03-15)

Full analysis in [`docs/decision_project_structure.md`](docs/decision_project_structure.md).

**Decision:** Move all production Python source into a `jlesson/` package with `video/` and
`exporters/` sub-packages. Replace `py-modules` in `pyproject.toml` with `packages.find`.
Rename CLI entry point from `japanese-lesson` → `jlesson`.

**Migration status:** PLANNED — no files moved yet.

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

> Run all commands in an already-activated conda environment (`conda activate base`).
> Do **not** use `conda run` — it buffers output until exit, hiding LLM progress.
