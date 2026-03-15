# Japanese Learning Material — Progress Report

## Project Goal

Build a CLI tool that generates structured Japanese lessons combining vocabulary and grammar with high repetition, following YAGNI/KISS/DRY principles. Supports both deterministic generation (no LLM needed) and LLM-enhanced generation for natural sentences.

---

## Completed

### 1. Structure Document (`structure.md`)
- Defined the problem (isolated focus, low repetition count)
- Designed 3-phase unit structure: Nouns → Verbs → Grammar
- Documented 10 common Japanese grammar structures with examples
- Mapped 11 grammar dimensions (person, tense, polarity, politeness, verb type, aspect, mood, voice, sentence type, adjective type, sentence pattern)
- Created beginner priority ranking and combination grid

### 2. Vocabulary Database (`vocab/`)
- `food.json` — 12 nouns, 10 verbs + explicit grammar_pairs (eat+fish, drink+water, cook+meat)
- `travel.json` — 12 nouns, 10 verbs (station, airport, hotel, go, come, return, …)
- Schema: english, japanese (kana), kanji, romaji; verbs also include type + masu_form

### 3. Prompt Template (`prompt_template.py`)
- `build_lesson_prompt()` — assembles a full LLM instruction from vocab + config
- `build_vocab_prompt()` — generates LLM prompt for new vocabulary themes
- Configurable: persons, grammar patterns, dimensions, repetition counts
- Beginner defaults: 3 persons × 2 tenses × 2 polarities × 3 patterns
- No external dependencies (stdlib only)
- `build_noun_practice_prompt(nouns, lesson_number)` — JSON prompt returning `{noun_items}` with example sentences and memory tips
- `build_verb_practice_prompt(verbs, lesson_number)` — JSON prompt returning `{verb_items}` with all four polite conjugation forms
- `build_grammar_select_prompt(unlocked_grammar, nouns, verbs, lesson_number, covered_ids)` — Level-1 grammar prompt: LLM picks which grammar points to teach, returns `{selected_ids, rationale}`
- `build_grammar_generate_prompt(grammar_specs, nouns, verbs, persons, sentences_per_grammar)` — Level-2 grammar prompt: LLM writes practice sentences per grammar point, returns `{sentences}`
- `build_content_validate_prompt(sentences)` — cross-check prompt: LLM validates accuracy of generated sentences, returns `{score, corrections, summary}`

### 4. CLI Tool (`generate_lesson.py`)
- `--theme <name>` — select vocabulary theme
- `--list-themes` — show available themes
- `--nouns N` / `--verbs N` — control item count (default 6)
- `--seed N` — reproducible random selection
- `--no-shuffle` — pick items in order
- `--output FILE` — write to file instead of stdout
- `--generate-vocab <theme>` — produce LLM prompt for new vocab JSON
- `--level beginner|intermediate|advanced` — difficulty level
- `--create-vocab THEME` — generate vocab JSON for a new theme via LLM; saves to `vocab/<theme>.json`
- `--show-curriculum` — display current grammar progression and lesson summary from curriculum file
- `--curriculum-path FILE` — override default curriculum path (`curriculum/curriculum.json`)
- Tested with `food` and `travel` themes ✓
- **Cleaned (2026-03-15)**: removed all `lesson_generator` imports; removed `--create`, `--llm`, `--render-video`, `--video-method` flags and their handlers (module deleted from repo)

### 5. Deterministic Lesson Generator (`lesson_generator.py`) — **REMOVED**
- This module was deleted from the repo (last seen in commit `8837a15`)
- All references removed from `generate_lesson.py` and demo spikes
- Functionality superseded by the LLM-driven curriculum pipeline in `spike_09_demo.py`

### 6. Decision Documents (`docs/`)
Researched and documented multiple options for each technology choice:
- **`decision_tts_engine.md`** — 6 TTS engines compared → **edge-tts**
- **`decision_video_pipeline.md`** — 5 video approaches compared → **Pillow + moviepy**
- **`decision_fonts_rendering.md`** — 5 font options compared → **Noto Sans JP** (Yu Gothic Bold fallback)
- **`decision_llm_integration.md`** — 5 LLM options compared → **OpenAI SDK + Ollama** (hybrid: deterministic + LLM)

### 8. Production Modules (Extracted from Spikes)
- **`tts_engine.py`** — Production TTS engine using edge-tts (extracted from spike_01)
- **`video_cards.py`** — Card renderer for 1080p video cards (extracted from spike_02)
- **`video_builder.py`** — Video assembler using moviepy (extracted from spike_03/04)
- **CLI Integration** — Added `--render-video` flag to `generate_lesson.py`
- **Module Packaging** — Updated `pyproject.toml` to include new modules

### 10. LLM Integration (Validated via Spikes)
- **LLM Client**: `llm_client.py` — universal OpenAI SDK interface
- **Configuration**: `config.py` — provider settings, timeout, temperature
- **Enhanced Grammar**: `--llm` flag falls back silently to deterministic if LLM unavailable
- **`<think>` stripping**: `llm_client.py` strips `<think>...</think>` reasoning blocks from thinking models (Qwen3, phi-4-reasoning-plus, ministral-reasoning)
- **JSON structured output**: LM Studio uses llama.cpp grammar-based sampling — requires `response_format: {"type": "json_schema"}` (NOT `json_object`); `json_schema` enforces valid JSON at the token level, bypassing verbose reasoning output entirely
- **Mistral chat template fix**: `mistral-7b-instruct-v0.3` GGUF has no system-role slot in its `[INST]` template — system content must be prepended to the user turn to avoid HTTP 400
- **`ask_llm_json_free()`**: New function for free-form JSON responses — uses `generate_text(json_mode=False)` + `_extract_json()`; no fixed schema; used when response shape varies per call (vocab dicts, sentence arrays, validation reports)
- **Dependencies**: `openai` added to requirements

### 11. LLM Evaluation Spikes
- **`spike_06_llm_evaluation.py`** — Multi-provider benchmark (Ollama, LM Studio, OpenAI); added host reachability pre-check, 15s per-provider budget, 10s per-request timeout
- **`spike_07_lmstudio_api.py`** — Deep LM Studio API evaluation (iteratively improved across 3 runs):
  - Connectivity check, full model list, embedding model filtering, per-model evaluation loop
  - **Run 1**: Plain text + `json_object` + prompt JSON — discovered `json_object` rejected (HTTP 400)
  - **Run 2**: Switched to `json_schema` + extended all models; added `qwen/qwen3.5-9b` (new model); `mistral-7b-instruct-v0.3` still failing (400 on system message)
  - **Run 3** (latest): Added `build_messages()` helper to fold system content into user turn for old Mistral GGUF template; added `extract_json()` helper to fish JSON out of verbose reasoning output; upgraded `test_json_via_prompt` with stricter empty-field validation
  - **Final result**: All 8 generation models pass `json_schema` structured output — 8/8 ✅

### 14. End-to-End Demo (`spike/spike_09_demo.py`) — **NEW (2026-03-15)**
- Two-lesson curriculum demo with fully rendered MP4 videos; no `lesson_generator` dependency
- Auto-generates missing vocab via LLM (`_load_vocab` calls `generate_vocab` if `vocab/<theme>.json` absent)
- LLM pipeline per lesson: grammar select → sentence generate → noun practice → add/complete lesson → render video
- Fixed 4 bugs during first successful run:
  1. **`_extract_json()` nested JSON** — replaced flat-object regex `r'\{[^{}]+\}'` with a brace-depth scanner (`_find_json_objects`) that correctly extracts nested dicts (vocab has `{"nouns":[...]}` which the old regex couldn't match)
  2. **Vocab string whitespace** — LLM returned `' irregular'` (leading space) causing schema validation failure; added strip pass over all string values in `vocab_generator.generate_vocab()`
  3. **`PERSONS` format** — constant was `["I", "you", "she"]` (plain strings) but `build_grammar_generate_prompt` expects `list[tuple[str,str,str]]`; fixed to `[("I","私","watashi"), ...]`
  4. **moviepy 2.x audio API** — `CompositeVideoClip([img, audio])` raises `AttributeError: 'AudioFileClip' has no attribute 'layer_index'`; fixed to `img_clip.with_audio(audio_clip)`
- **Demo result** (2026-03-15, `qwen/qwen3-14b`, 192s total):
  - Lesson 1 (food): 6 sentences, 3 noun items → `output/demo/lesson_01_food.mp4` (482 KB)
  - Lesson 2 (travel): 6 sentences, 3 noun items → `output/demo/lesson_02_travel.mp4` (571 KB)
  - Curriculum saved → `output/demo/curriculum_demo.json`

### 13. Curriculum & Lesson Dictionary System
- **`curriculum.py`** — grammar progression tracker and lesson dictionary
  - `GRAMMAR_PROGRESSION`: 15-step table (levels 1-4) with prerequisite graph
  - Level 1 (2 steps, no prerequisites): `action_present_affirmative`, `identity_present_affirmative`
  - Level 2 (5 steps): `action_present_negative`, `action_past_affirmative`, `question_ka`, `direction_ni_ikimasu`, `existence_arimasu`/`adjective_na`
  - Level 3 (4 steps): `action_past_negative`, `desire_tai`, `desire_hoshii`, `reason_kara`
  - Level 4 (3 steps): `te_form_request`, `te_form_progressive`, `potential_dekimasu`
  - `create_curriculum()`, `load_curriculum()`, `save_curriculum()` — CRUD for `curriculum/curriculum.json`
  - `add_lesson()`, `complete_lesson()` — lesson lifecycle management
  - `get_next_grammar(covered_ids)` — returns all unlocked-but-uncovered grammar steps sorted by level
  - `suggest_new_vocab(curriculum, vocab)` — fresh-first selection; fills from covered items if pool exhausted
  - `summary()` — formatted multiline string showing lesson count, covered grammar, covered vocab
- **`vocab_generator.py`** — LLM-driven vocab generation
  - `validate_vocab_schema(vocab)` — validates noun/verb field presence and verb type values; returns error list
  - `generate_vocab(theme, ...)` — calls `ask_llm_json_free()`, validates schema, saves to `vocab/<theme>.json`
  - Valid verb types: `{"る-verb", "う-verb", "irregular", "な-adj"}`
- **`spike/spike_08_curriculum.py`** — end-to-end validation of the full curriculum LLM workflow
  - Steps: grammar table display, vocab loading, curriculum creation, vocab suggestion, grammar select (LLM), grammar generate (LLM), content validation (LLM), noun practice (LLM), lesson save
  - **Run result**: `qwen/qwen3-14b` — LLM grammar select 12.1s, grammar generate 21.4s, validation **10/10** 2.6s, noun practice 11.5s
  - Output: `spike/output/spike_08_curriculum.json`, `curriculum/curriculum.json` (Lesson 1 created)
- **`curriculum/curriculum.json`** — lesson dictionary file; created by spike_08; contains Lesson 1 (food theme, both level-1 grammar points, 4 nouns + 3 verbs)

### 12. Model Research (16 GB GDDR)
All 8 models evaluated with `json_schema` structured output (grammar-sampled by llama.cpp). Quality ranked by Japanese translation accuracy:

| Model | JSON schema | Plain text | Japanese quality | Notes |
|---|---|---|---|---|
| `qwen/qwen3-14b` | ✅ 6.5s | ✅ 16s | ⭐⭐⭐ | Best Japanese; thinking model, verbose plain text |
| `qwen/qwen3.5-9b` | ✅ 4.5s | ✅ 22s | ⭐⭐⭐ | Good Japanese; extremely verbose plain text (reasoning exposed) |
| `microsoft/phi-4-reasoning-plus` | ✅ 3.7s | ✅ 16s | ⭐⭐⭐ | Correct Japanese; thinking model, needs `<think>` stripping |
| `mistralai/ministral-3-14b-reasoning` | ✅ 6.7s | ✅ 17s | ⭐⭐⭐ | Correct Japanese + romaji; appends raw Japanese in romaji field |
| `mistral-7b-instruct-v0.3` | ✅ 5.5s | ✅ 9s | ⭐⭐ | Good; no system role — must merge into user turn |
| `meta-llama-3.1-8b-instruct` | ✅ 2.8s | ✅ 5s | ⭐ | Fastest; Japanese field empty in schema mode |
| `stable-code-instruct-3b` | ✅ 8.3s | ✅ 5s | ⭐ | Romaji field contains Japanese text — code model |
| `deepseek-math-7b-instruct` | ✅ 10.9s | ✅ 9s | ❌ | english="eat", Japanese/romaji empty — math model |

- **Recommended for this project**: `qwen/qwen3-14b` (best quality) or `qwen/qwen3.5-9b` (slightly faster JSON)
- **Avoid for language tasks**: `deepseek-math`, `stable-code` — wrong domain
- **Recommended download**: `Qwen2.5-7B-Instruct Q4_K_M` — non-thinking, fast, excellent Japanese
- **Key insight**: `json_schema` with llama.cpp grammar sampling works on ALL models regardless of thinking/verbose tendencies — the token constraint enforces structure before reasoning can pollute the output

---

---

## Architecture

```
japanese/
├── generate_lesson.py    # CLI entry point
├── prompt_template.py    # LLM prompt builder (pure functions, 7 functions)
├── curriculum.py         # Grammar progression table + lesson dictionary CRUD
├── vocab_generator.py    # LLM-driven vocab generation + schema validation
├── config.py             # LLM configuration settings
├── llm_client.py         # Universal LLM client (OpenAI SDK); ask_llm_json_free()
├── structure.md          # Design doc & grammar reference
├── progress_report.md    # This file
├── pyproject.toml        # Project metadata & dependencies
├── requirements.txt      # Legacy deps file
├── .gitignore            # Excludes generated outputs
├── vocab/
│   ├── food.json         # 12 nouns + 10 verbs + grammar_pairs
│   └── travel.json       # 12 nouns + 10 verbs
├── curriculum/
│   └── curriculum.json   # Lesson dictionary (created per project; lesson-by-lesson)
├── docs/
│   ├── decision_tts_engine.md
│   ├── decision_video_pipeline.md
│   ├── decision_fonts_rendering.md
│   └── decision_llm_integration.md
├── tests/
│   ├── test_llm_client.py       # 20 unit + 14 integration
│   ├── test_video_cards.py      # 29 unit
│   ├── test_tts_engine.py       # 22 unit + 4 internet
│   ├── test_video_builder.py    # 13 unit + 2 video
│   ├── test_curriculum.py       # 42 unit  ← NEW
│   ├── test_vocab_generator.py  # 18 unit (mocked LLM)  ← NEW
│   └── test_prompt_template.py  # 37 unit  ← NEW
├── spike/
│   ├── spike_01_tts.py
│   ├── spike_02_cards.py
│   ├── spike_03_video.py
│   ├── spike_04_full_pipeline.py
│   ├── spike_05_performance.py
│   ├── spike_06_llm_evaluation.py  # LLM provider benchmark (multi-provider, budgeted)
│   ├── spike_07_lmstudio_api.py    # LM Studio deep API evaluation
│   ├── spike_08_curriculum.py      # Curriculum workflow end-to-end (LLM required)
│   ├── spike_09_demo.py            # Two-lesson demo with rendered MP4 videos  ← NEW
│   └── output/           # Spike outputs (gitignored)
└── output/               # Generated lessons (gitignored)
```


---

## Software Design Principles

**Design principles:**
- **High cohesion** — each module has one responsibility
- **Low coupling** — modules communicate via well-defined interfaces; no circular dependencies
- **Composition** — composition over inheritance; implementations are composed 
- **YAGNI** — focus on implementing the required features; don't reinvent the wheel; 
- **KISS** — keep complexity in check; readable code; 
- **DRY** — avoid duplication; generalize patterns into cohesive modules/functions 
- **🚀 Performance** — FFmpeg stream copying for 12.5x faster video generation


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

### Current Cycle Status

- ✅ **Completed**: Research, design, spikes, core CLI, lesson generation, video pipeline
- ✅ **Completed**: LLM integration validated — all 8 LM Studio models pass `json_schema` structured output; `mistral-7b` system-role fix applied; `qwen3.5-9b` new model evaluated
- ✅ **Completed**: End-to-end curriculum demo — two lessons, LLM-driven, auto vocab generation, rendered MP4 videos
- 📋 **Planned**: Expand vocab themes, Anki export, interactive lesson runner, more grammar levels

---

## Dependencies

### Core (stdlib only — no pip install needed)
- `argparse`, `json`, `random`, `pathlib`

### Video Pipeline
| Library | Version | Source | Purpose |
|---------|---------|--------|---------|
| **edge-tts** | 7.2.7 | pip | Neural TTS — Japanese + English voices |
| **Pillow** | 12.0.0 | pre-installed | Text card rendering at 1080p |
| **moviepy** | 2.1.2 | pre-installed | Video composition + audio overlay |
| **ffmpeg** | 4.3.1 | conda-forge | Video encoding backend |
| **Internet** | - | Required | Microsoft Edge TTS service access |

### LLM Integration
| Library | Version | Purpose |
|---------|---------|---------|
| **openai** | 2.28.0 | Universal LLM client (OpenAI, LM Studio, Ollama) |

### System Fonts
- `C:/Windows/Fonts/YuGothB.ttc` (Yu Gothic Bold) — Japanese text
- `C:/Windows/Fonts/segoeui.ttf` / `segoeuib.ttf` — English text

---

## Test Results (2026-03-14)

> **Note**: All commands are run in an already-activated conda environment (`conda activate base`).
> Do **not** use `conda run` — it buffers all output until the process exits, hiding intermediate
> progress that shows whether a long-running LLM or video task is on track.

| Command | Result |
|---------|--------|
| `python generate_lesson.py --list-themes` | ✓ Lists food, travel |
| `python generate_lesson.py --theme food --seed 42 -o lesson_food.md` | ✓ LLM prompt written |
| `python generate_lesson.py --theme travel --nouns 4 --verbs 4 --seed 7` | ✓ Correct output |
| `python generate_lesson.py --generate-vocab shopping` | ✓ Vocab prompt generated |
| `python generate_lesson.py --create --theme food --no-shuffle` | ✓ 87 items (JSON + MD) |
| `python generate_lesson.py --create --theme food --nouns 1 --verbs 0 --no-shuffle --render-video --video-method ffmpeg` | ✓ Video generated (69.9 KB, fast method) |
| `python generate_lesson.py --create --theme food --nouns 1 --verbs 0 --no-shuffle --render-video --video-method moviepy` | ✓ Video generated (slower method, compatible) |
| `python generate_lesson.py --create --theme food --nouns 1 --verbs 0 --no-shuffle --llm` | ⚠️ Ran but fell back to deterministic (no LLM server running at the time) |
| `python spike/spike_07_lmstudio_api.py` (run 1) | ✅ LM Studio confirmed: plain text 2.4s, JSON via prompt 7.3s, `qwen3-14b` with `/no_think` |
| `python spike/spike_06_llm_evaluation.py` | ✅ Ran: Ollama not running (skipped), LM Studio hit 15s budget (model slow to load) |
| `python spike/spike_07_lmstudio_api.py` (run 2, all models) | ✅ Added `qwen/qwen3.5-9b`; switched to `json_schema`; 6/8 pass, `mistral-7b` still 400 |
| `python spike/spike_07_lmstudio_api.py` (run 3, fixed) | ✅ All 8/8 models pass `json_schema` — `mistral-7b` fixed via `build_messages()` helper |
| `python spike/spike_08_curriculum.py` | ✅ Full curriculum workflow — grammar select 12.1s, generate 21.4s, validate **10/10** 2.6s, noun practice 11.5s |
| `python spike/spike_09_demo.py` (2026-03-15) | ✅ Two lessons rendered — food 482 KB + travel 571 KB MP4; 192s total; all LLM stages passed |

## Unit Test Suite (2026-05-30)

| Test file | Tests | Markers |
|-----------|-------|---------|
| `test_llm_client.py` | 34 | 14 `integration` |
| `test_video_cards.py` | 29 | — |
| `test_tts_engine.py` | 26 | 4 `internet` |
| `test_video_builder.py` | 15 | 2 `video` |
| `test_curriculum.py` | 42 | — |
| `test_vocab_generator.py` | 18 | — |
| `test_prompt_template.py` | 37 | — |
| **Total** | **204** | **20 non-unit deselected** |

```
pytest tests/ -m "not integration and not internet and not video"
→ 184 passed, 20 deselected in 6.65s
```

---

## Repo Status Verification (2026-03-14)

### ✅ Working Features
- Core CLI fully functional (stdlib only)
- Lesson generation (deterministic)
- LLM prompt generation
- Vocab prompt generation
- Output file creation (JSON + Markdown)

### ❌ Missing Dependencies
- **edge-tts** — Required for TTS audio generation (video pipeline)
- **ffmpeg** — Required for video encoding (moviepy backend)
- **openai** — Required for LLM integration (optional, install with `pip install openai`)

### ✅ Installed Dependencies
- **Pillow** — Text card rendering
- **moviepy** — Video composition
- **openai** — LLM client (universal interface, confirmed working)

### ✅ LLM Provider (LM Studio)
- **Provider**: LM Studio running locally on port 1234
- **Active model**: `qwen/qwen3-14b`
- **Available models**: qwen3-14b, qwen3.5-9b, phi-4-reasoning-plus, meta-llama-3.1-8b-instruct, mistral-7b-instruct-v0.3, ministral-3-14b-reasoning, deepseek-math-7b-instruct, stable-code-3b, text-embedding-nomic-embed-text-v1.5
- **Config**: `config.py` → `LLM_BASE_URL=http://localhost:1234/v1`, `LLM_MODEL=qwen/qwen3-14b`
- **Status**: ✅ Connected — all 8 generation models confirmed working with `json_schema` structured output
- **Known quirks**:
  - `json_object` response_format rejected (HTTP 400) — use `json_schema` instead
  - `qwen3-14b`, `qwen3.5-9b`, `phi-4-reasoning-plus`, `ministral-3-14b-reasoning` are thinking models — use `/no_think` system message and `<think>` stripping
  - `mistral-7b-instruct-v0.3` GGUF has no system-role token — system content must be merged into user turn
  - `deepseek-math` and `stable-code` produce structurally valid JSON but wrong/empty language content

### 📦 Installation
Run `install.ps1` to install missing dependencies:
```powershell
.\install.ps1
```

This installs:
- `pip install edge-tts`
- `conda install -c conda-forge ffmpeg`
- `pip install openai`

After installation, video pipeline spikes should work.

---

## Video Generation Pipeline — Plan

### Goal

Turn a generated lesson into a **learning video** with:
- Visual text cards showing English ↔ Japanese
- Audio narration (TTS) for pronunciation
- Timed pauses for learner recall

### End-to-End Pipeline

```
[1] CLI --create        [2] Lesson items         [3] TTS generates     [4] Card renderer     [5] Video assembler
    vocab JSON     --->     (deterministic   --->     audio clips   --->   1080p PNGs    --->   final .mp4
    (existing)              or LLM-enhanced)          (spiked)             (spiked)              (spiked)
```

### Step Breakdown

| Step | Module | Input | Output | Status |
|------|--------|-------|--------|--------|
| 1. Generate items | `lesson_generator.py` | vocab JSON | structured item dicts | ✅ Done |
| 2. Generate audio | `tts_engine.py` (new) | text per item | `.mp3` per item | 🔬 Spiked |
| 3. Render cards | `video_cards.py` (new) | text per item | PNG per item | 🔬 Spiked |
| 4. Compose video | `video_builder.py` (new) | PNGs + audio | `.mp4` | � **12.5x faster** |
| 5. LLM enhance | `llm_client.py` (new) | prompt + config | natural sentences | 📋 Planned |

### Video Card Layout (per frame)

```
┌─────────────────────────────────┐
│         [INTRODUCE] 1/30        │  ← step label + counter
│                                 │
│           water                 │  ← English (large)
│                                 │
│        ─── pause ───            │  ← blank/thinking gap
│                                 │
│      水 (みず, mizu)            │  ← Japanese reveal
│                                 │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━   │  ← progress bar
└─────────────────────────────────┘
```

### Timing Model

| Event | Duration |
|-------|----------|
| Show prompt text | 1.5s |
| Pause (learner thinks) | 2.0s |
| Reveal + TTS plays | ~1.5s (auto) |
| Hold both visible | 1.5s |
| **Total per touch** | **~7.5s** |

Estimated video length: 87 touches × 7.5s ≈ **~11 minutes** per unit.

---

## Next Steps

- [x] Install ffmpeg + edge-tts
- [x] Decision documents (TTS, video pipeline, fonts, LLM integration)
- [x] Spike implementations (all 4 pass)
- [x] Deterministic lesson generator with `--create`
- [x] First lesson: food theme (87 items)
- [x] Build TTS engine module — extract from spike_01
- [x] Build video card renderer — extract from spike_02
- [x] Build video assembler — extract from spike_03/04
- [x] Add `--render-video` CLI flag
- [x] **Test Full Pipeline**: Generate complete 87-item video (requires ~15-20 minutes)
  - **RESOLVED**: TTS generation was failing due to rate limiting from Microsoft Edge TTS service
  - **Solution**: Added 1-second delays between TTS requests and retry logic with exponential backoff
  - **Tested**: Successfully generated 5-item video; full pipeline now works
  - **Note**: TTS requires internet access to Microsoft servers; may fail in restricted networks
  - **🚀 Performance**: Video composition optimized with FFmpeg stream copying (12.5x faster)
- [~] **LLM Integration**: Code written (`llm_client.py`, `config.py`, `--llm` flag) — falls back to deterministic; end-to-end not yet validated
- [x] **LLM Provider Setup**: LM Studio running with `qwen/qwen3-14b`; plain text + JSON generation confirmed
- [x] **LLM Evaluation**: `spike_06_llm_evaluation.py` run — host reachability check, 15s budget, provider comparison
- [x] **LM Studio Deep Eval**: `spike_07_lmstudio_api.py` — 3 runs; all 8 models pass `json_schema`; Mistral system-role fix; `qwen3.5-9b` new model evaluated; quality table compiled
- [x] **Model Research**: All 8 models benchmarked — `qwen3-14b` / `qwen3.5-9b` best for Japanese; `deepseek-math` / `stable-code` unsuitable
- [x] **Fix `llm_client.py` JSON mode**: Switched to `json_schema`; added `build_messages()` + `_extract_json()` + `ask_llm_json_free()` for free-form JSON
- [x] **Wire `/no_think`**: Added `<think>` stripping and system-message `/no_think` via `llm_client.py`
- [x] **Curriculum System**: `curriculum.py` — 15-step grammar progression table (levels 1-4), lesson dictionary CRUD, `get_next_grammar()`, `suggest_new_vocab()`
- [x] **Vocab Generator**: `vocab_generator.py` — LLM vocab generation with schema validation; saves to `vocab/<theme>.json`
- [x] **Prompt Template Extensions**: 5 new JSON-output prompts (noun practice, verb practice, grammar select L1, grammar generate L2, content validate)
- [x] **spike_08**: End-to-end curriculum workflow validated — LLM select + generate + validate (10/10) + noun practice all passing
- [x] **Unit Tests**: 184/184 unit tests pass (42 curriculum + 18 vocab_generator + 37 prompt_template + existing 87)
- [ ] **LLM Validation**: Test `--llm` flag produces actual LLM sentences end-to-end (not fallback)
- [ ] **Generate Lesson 2**: Run full curriculum flow to create Lesson 2 (unlocks level-2 grammar)
- [ ] **`--create-vocab` end-to-end**: Run `python generate_lesson.py --create-vocab animals` with LM Studio live
- [ ] **More Vocab Themes**: Expand beyond food/travel themes
- [ ] **Performance Optimization**: Video generation speed improvements
- [ ] Optional: export generated lessons to Anki-compatible format
- [ ] Optional: download & use Noto Sans JP instead of system Yu Gothic
