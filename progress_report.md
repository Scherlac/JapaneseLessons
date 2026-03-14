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

### 7. Spike Implementations (`spike/`)
Minimal proof-of-concept scripts validating the recommended tech stack. All 4 pass.

| Spike | Script | Result | Key Findings |
|-------|--------|--------|--------------|
| 01 — TTS | `spike_01_tts.py` | ✓ 7 audio files + SRT | edge-tts 7.x: `SubMaker.feed()` + `get_srt()`. NanamiNeural + KeitaNeural. Rate control works. |
| 02 — Cards | `spike_02_cards.py` | ✓ 3 PNG cards (1920×1080) | Yu Gothic Bold renders Japanese cleanly. Three card types: INTRODUCE, RECALL, TRANSLATE. |
| 03 — Video | `spike_03_video.py` | ✓ 19s MP4 (4 clips) | moviepy concatenation + audio delay via `with_start()`. Export: libx264 + aac. |
| 04 — Full pipeline | `spike_04_full_pipeline.py` | ✓ 16s MP4 (3 items) | End-to-end: vocab → cards → TTS → video. Pipeline concept proven. |

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
- [ ] Build TTS engine module — extract from spike_01
- [ ] Build video card renderer — extract from spike_02
- [ ] Build video assembler — extract from spike_03/04
- [ ] Add `--render-video` CLI flag
- [ ] LLM integration (OpenAI SDK + Ollama) for enhanced grammar
- [ ] Add more vocabulary themes (daily routine, shopping, school, etc.)
- [ ] Optional: export generated lessons to Anki-compatible format
- [ ] Optional: download & use Noto Sans JP instead of system Yu Gothic
