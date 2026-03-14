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

### 4. CLI Tool (`generate_lesson.py`)
- `--theme <name>` — select vocabulary theme
- `--list-themes` — show available themes
- `--nouns N` / `--verbs N` — control item count (default 6)
- `--seed N` — reproducible random selection
- `--no-shuffle` — pick items in order
- `--output FILE` — write to file instead of stdout
- `--generate-vocab <theme>` — produce LLM prompt for new vocab JSON
- `--level beginner|intermediate|advanced` — difficulty level
- `--create` — generate a complete lesson deterministically (JSON + Markdown)
- Tested with `food` and `travel` themes ✓

### 5. Deterministic Lesson Generator (`lesson_generator.py`)
- Produces structured lesson items directly from vocab (no LLM required)
- Japanese polite-form conjugation: ます/ません/ました/ませんでした + な-adj (です)
- Romaji conjugation for all verb types (る/う/irregular/な-adj)
- English conjugation with irregular past tense support (40+ irregular verbs)
- 3 phases: nouns (5 touches each), verbs (5 touches each), grammar (3 touches each)
- Explicit grammar pairs from vocab JSON for natural sentences
- Markdown renderer for human review
- First lesson: 87 items (30 nouns + 30 verbs + 27 grammar)

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

### 9. Video Pipeline Integration
- Video rendering integrated into CLI with `--create --render-video`
- Automatic audio generation for all lesson items
- Automatic card generation matching lesson structure
- Full pipeline: JSON → Audio → Cards → Video
- Tested: Audio generation starts successfully (87 files would take ~10-15 minutes)

---

---

## Architecture

```
japanese/
├── generate_lesson.py    # CLI entry point
├── lesson_generator.py   # Deterministic lesson generator (no LLM)
├── prompt_template.py    # LLM prompt builder (pure functions)
├── structure.md          # Design doc & grammar reference
├── progress_report.md    # This file
├── pyproject.toml        # Project metadata & dependencies
├── requirements.txt      # Legacy deps file
├── .gitignore            # Excludes generated outputs
├── vocab/
│   ├── food.json         # 12 nouns + 10 verbs + grammar_pairs
│   └── travel.json       # 12 nouns + 10 verbs
├── docs/
│   ├── decision_tts_engine.md
│   ├── decision_video_pipeline.md
│   ├── decision_fonts_rendering.md
│   └── decision_llm_integration.md
├── spike/
│   ├── spike_01_tts.py
│   ├── spike_02_cards.py
│   ├── spike_03_video.py
│   ├── spike_04_full_pipeline.py
│   └── output/           # Spike outputs (gitignored)
└── output/               # Generated lessons (gitignored)
```

**Design principles:**
- **YAGNI** — no templating engine, no ORM, no web framework
- **KISS** — flat JSON vocab, argparse CLI, pure functions
- **DRY** — shared repetition cycle logic, single entry points
- **Low coupling** — modules communicate via simple data (dicts/paths)
- **High cohesion** — each module has one responsibility
- **Composition** — functions composed together, no class hierarchies

---

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
   - Follow YAGNI/KISS/DRY principles
   - Keep dependencies minimal (stdlib-first)
   - Write pure functions with clear interfaces

4. **Testing & Validation** ✅
   - Manual testing of all CLI commands
   - Verify output formats and functionality
   - Test edge cases and error conditions
   - Document test results

5. **Documentation & Planning** 📝
   - Update progress report with completed work
   - Document architecture and design decisions
   - Plan next iteration's scope
   - Maintain comprehensive README

### Cycle Characteristics

- **Documentation-first**: Every decision and implementation is documented before/after
- **Spike-before-scale**: Prove concepts with minimal code before building full features
- **Incremental delivery**: Working features over big releases
- **Validation-driven**: Test and verify at each step
- **Research-heavy**: Technology decisions are well-researched and documented

### Current Cycle Status

- ✅ **Completed**: Research, design, spikes, core CLI, lesson generation
- 🔄 **Active**: Extracting production modules from spikes (TTS, video rendering)
- 📋 **Planned**: LLM integration, video pipeline completion, additional themes

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

### LLM Integration (planned)
| Library | Version | Purpose |
|---------|---------|---------|
| **openai** | 2.28.0 | Universal LLM client (OpenAI, Ollama, llama.cpp) |

### System Fonts
- `C:/Windows/Fonts/YuGothB.ttc` (Yu Gothic Bold) — Japanese text
- `C:/Windows/Fonts/segoeui.ttf` / `segoeuib.ttf` — English text

---

## Test Results (2026-03-14)

| Command | Result |
|---------|--------|
| `python generate_lesson.py --list-themes` | ✓ Lists food, travel |
| `python generate_lesson.py --theme food --seed 42 -o lesson_food.md` | ✓ LLM prompt written |
| `python generate_lesson.py --theme travel --nouns 4 --verbs 4 --seed 7` | ✓ Correct output |
| `python generate_lesson.py --generate-vocab shopping` | ✓ Vocab prompt generated |
| `python generate_lesson.py --create --theme food --no-shuffle` | ✓ 87 items (JSON + MD) |
| `python generate_lesson.py --create --theme food --seed 42` | ✓ Shuffled selection works |

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
- **openai** — Required for LLM integration (planned feature)

### ✅ Installed Dependencies
- **Pillow** — Text card rendering
- **moviepy** — Video composition

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
| 4. Compose video | `video_builder.py` (new) | PNGs + audio | `.mp4` | 🔬 Spiked |
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
- [ ] Test full video pipeline (generate complete lesson video)
- [ ] LLM integration (OpenAI SDK + Ollama) for enhanced grammar
- [ ] Add more vocabulary themes (daily routine, shopping, school, etc.)
- [ ] Optional: export generated lessons to Anki-compatible format
- [ ] Optional: download & use Noto Sans JP instead of system Yu Gothic
