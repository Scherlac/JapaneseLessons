# Japanese Learning Material — Progress Report

## Project Goal

Build a CLI tool that generates structured LLM prompts for Japanese lessons combining vocabulary and grammar with high repetition, following YAGNI/KISS/DRY principles.

---

## Completed

### 1. Structure Document (`structure.md`)
- Defined the problem (isolated focus, low repetition count)
- Designed 3-phase unit structure: Nouns → Verbs → Grammar
- Documented 10 common Japanese grammar structures with examples
- Mapped 11 grammar dimensions (person, tense, polarity, politeness, verb type, aspect, mood, voice, sentence type, adjective type, sentence pattern)
- Created beginner priority ranking and combination grid

### 2. Vocabulary Database (`vocab/`)
- `food.json` — 12 nouns, 10 verbs (water, rice, fish, eat, drink, cook, …)
- `travel.json` — 12 nouns, 10 verbs (station, airport, hotel, go, come, return, …)
- Schema: english, japanese (kana), kanji, romaji; verbs also include type + masu_form

### 3. Prompt Template (`prompt_template.py`)
- `build_lesson_prompt()` — assembles a full LLM instruction from vocab + config
- Configurable: persons, grammar patterns, dimensions, repetition counts
- Beginner defaults: 3 persons × 2 tenses × 2 polarities × 3 patterns
- Helper formatters for nouns, verbs, combination instructions
- No external dependencies (stdlib only)

### 4. CLI Tool (`generate_lesson.py`)
- `--theme <name>` — select vocabulary theme
- `--list-themes` — show available themes
- `--nouns N` / `--verbs N` — control item count (default 6)
- `--seed N` — reproducible random selection
- `--no-shuffle` — pick items in order
- `--output FILE` — write to file instead of stdout
- Tested with both `food` and `travel` themes ✓

---

## Architecture

```
japanese/
├── structure.md          # Design doc & grammar reference
├── progress_report.md    # This file
├── generate_lesson.py    # CLI entry point
├── prompt_template.py    # Prompt builder (pure functions)
├── requirements.txt      # No deps (stdlib only)
├── .gitignore            # Excludes generated outputs
├── vocab/
│   ├── food.json         # 12 nouns + 10 verbs
│   └── travel.json       # 12 nouns + 10 verbs
├── docs/
│   ├── decision_tts_engine.md
│   ├── decision_video_pipeline.md
│   └── decision_fonts_rendering.md
└── spike/
    ├── spike_01_tts.py           # edge-tts proof-of-concept
    ├── spike_02_cards.py         # Pillow card rendering PoC
    ├── spike_03_video.py         # moviepy assembly PoC
    ├── spike_04_full_pipeline.py # End-to-end PoC
    └── output/                   # Generated spike outputs (gitignored)
```

**Design principles applied:**
- **YAGNI** — no templating engine, no ORM, no web framework; stdlib only
- **KISS** — two Python files, flat JSON vocab, argparse CLI
- **DRY** — shared repetition cycle logic, single `build_lesson_prompt()` entry point
- **Low coupling** — `prompt_template.py` knows nothing about files/CLI; `generate_lesson.py` handles I/O
- **High cohesion** — prompt logic in one module, CLI/loading in another
- **Composition** — functions composed together, no class hierarchies

---

## Test Results (2026-03-14)

| Command | Result |
|---------|--------|
| `python generate_lesson.py --list-themes` | ✓ Lists food, travel |
| `python generate_lesson.py --theme food --seed 42 -o lesson_food.md` | ✓ 94-line prompt written |
| `python generate_lesson.py --theme travel --nouns 4 --verbs 4 --seed 7` | ✓ Correct output to stdout |

---

### 5. Vocabulary Generation via LLM (`--generate-vocab`)
- `--generate-vocab <theme>` — produces an LLM prompt that outputs valid vocab JSON
- `--level beginner|intermediate|advanced` — controls difficulty
- `--nouns N` / `--verbs N` — override default counts (12/10)
- LLM output can be saved directly as `vocab/<theme>.json`
- Tested with `shopping` and `school` themes ✓

### 6. Decision Documents (`docs/`)
Researched and documented multiple options for each technology choice:
- **`decision_tts_engine.md`** — Compared 6 TTS engines (edge-tts, Google Cloud, Azure, Coqui TTS, gTTS, pyttsx3). Recommended: **edge-tts** (free, neural, Japanese voices, no API key)
- **`decision_video_pipeline.md`** — Compared 5 video composition approaches (moviepy, ffmpeg subprocess, ffmpeg-python, Manim, Pillow+ffmpeg). Recommended: **Pillow for cards + moviepy for assembly**
- **`decision_fonts_rendering.md`** — Compared 5 font options (Noto Sans JP, Noto Serif JP, M PLUS Rounded 1c, Zen Maru Gothic, system fonts). Recommended: **Noto Sans JP** (with Yu Gothic Bold as working fallback)

### 7. Spike Implementations (`spike/`)
Minimal proof-of-concept scripts validating the recommended tech stack. All 4 pass.

| Spike | Script | Result | Key Findings |
|-------|--------|--------|--------------|
| 01 — TTS | `spike_01_tts.py` | ✓ 7 audio files + SRT | edge-tts 7.x API: `SubMaker.feed()` + `get_srt()`. NanamiNeural (female) & KeitaNeural (male) both work. Rate control (`-20%`, `-30%`) works for learner pacing. |
| 02 — Cards | `spike_02_cards.py` | ✓ 3 PNG cards (1920×1080) | Yu Gothic Bold (`YuGothB.ttc`) renders Japanese cleanly at 1080p. Three card types: INTRODUCE, RECALL, TRANSLATE. |
| 03 — Video | `spike_03_video.py` | ✓ 19s MP4 (4 clips) | moviepy `concatenate_videoclips(method="compose")` works. Audio delay via `with_start()` for thinking pauses. Export: libx264 + aac. |
| 04 — Full pipeline | `spike_04_full_pipeline.py` | ✓ 16s MP4 (3 items) | End-to-end: hardcoded vocab → Pillow cards → edge-tts audio → moviepy video. Proves the pipeline concept. |

**Installed dependencies:**
- `edge-tts` 7.2.7 (pip)
- `ffmpeg` 4.3.1 (conda-forge)

**System fonts available:**
- `C:/Windows/Fonts/YuGothB.ttc` (Yu Gothic Bold) — used for Japanese text
- `C:/Windows/Fonts/segoeui.ttf` / `segoeuib.ttf` — used for English text

---

## Video Generation Pipeline — Plan

### Goal

Turn a generated lesson (text) into a **learning video** with:
- Visual text cards showing English ↔ Japanese  
- Audio narration (TTS) for pronunciation  
- Timed pauses for learner recall  

### End-to-End Pipeline

```
[1] CLI generates       [2] LLM produces       [3] Parser extracts      [4] TTS generates     [5] Video assembler
    lesson prompt  --->     lesson text    --->     structured items --->     audio clips   --->   final .mp4
    (existing)              (manual/API)            (new: parser)            (new: tts)           (new: compose)
```

### Step Breakdown

| Step | Module | Input | Output | Status |
|------|--------|-------|--------|--------|
| 1. Generate prompt | `generate_lesson.py` | vocab JSON | prompt text | ✅ Done |
| 2. Run LLM | Manual paste or API call | prompt text | lesson markdown | 🔧 Manual for now |
| 3. Parse lesson | `lesson_parser.py` (new) | lesson markdown | list of `LessonItem` dicts | ❌ To build |
| 4. Generate audio | `tts_engine.py` (new) | text per item | `.mp3`/`.wav` per item | 🔬 Spiked (spike_01) |
| 5. Render frames | `video_cards.py` (new) | text per item | image per item (Pillow) | 🔬 Spiked (spike_02) |
| 6. Compose video | `video_builder.py` (new) | images + audio | `.mp4` | 🔬 Spiked (spike_03/04) |

### Available Libraries (in py312 env)

| Library | Version | Source | Purpose |
|---------|---------|--------|---------|
| **moviepy** | 2.1.2 | pre-installed | ✅ Video composition, clip sequencing, audio overlay |
| **Pillow** | 12.0.0 | pre-installed | ✅ Text card rendering (English/Japanese on image) |
| **edge-tts** | 7.2.7 | pip | ✅ Neural TTS — Japanese + English voices, rate control, subtitles |
| **ffmpeg** | 4.3.1 | conda-forge | ✅ Video encoding backend for moviepy |

### Proposed Module Design

```
japanese/
├── generate_lesson.py       # CLI (existing)
├── prompt_template.py       # Prompt builder (existing)
├── lesson_parser.py         # NEW: parse LLM lesson output → structured items
├── tts_engine.py            # NEW: text → audio files via edge-tts
├── video_cards.py           # NEW: text → image cards via Pillow
├── video_builder.py         # NEW: images + audio → mp4 via moviepy
├── vocab/                   # Vocabulary JSON files
└── output/                  # Generated audio, images, video (gitignored)
```

**Principles:**
- **Low coupling** — each module does one thing, communicates via simple data (dicts/paths)
- **Composition** — `video_builder` composes outputs from `tts_engine` + `video_cards`
- **KISS** — no complex orchestration; a single `--render-video` CLI flag runs the pipeline
- **YAGNI** — no web UI, no real-time preview; just generate an .mp4

### Lesson Item Schema (what the parser produces)

```python
{
    "phase": "nouns" | "verbs" | "grammar",
    "step": "INTRODUCE" | "RECALL" | "REINFORCE" | "SELF-CHECK" | "LOCK-IN" | "TRANSLATE" | "COMPREHEND",
    "display_text": "water → 水 (みず, mizu)",       # shown on screen
    "tts_english": "water",                           # spoken in English
    "tts_japanese": "mizu",                           # spoken in Japanese
    "pause_seconds": 2.0,                             # think time before reveal
}
```

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
| Show English text | 1.5s |
| English TTS plays | ~1s (auto) |
| Pause (learner thinks) | 2.0s |
| Reveal Japanese + TTS | ~1.5s (auto) |
| Hold both visible | 1.5s |
| **Total per touch** | **~7.5s** |

Estimated video length: 87 touches × 7.5s ≈ **~11 minutes** per unit.

### Implementation Order

1. ~~Install `edge-tts` + `ffmpeg`~~ ✅ Done
2. ~~Spike implementations (TTS, cards, video, full pipeline)~~ ✅ Done — all 4 pass
3. Build `lesson_parser.py` — parse lesson markdown into item list
4. Build `tts_engine.py` — generate audio clips (based on spike_01)
5. Build `video_cards.py` — render text cards as images (based on spike_02)
6. Build `video_builder.py` — assemble final video (based on spike_03/04)
7. Add `--render-video` flag to CLI
8. Test end-to-end with food theme

---

## Next Steps

- [x] Install ffmpeg + edge-tts
- [x] Decision documents (TTS, video pipeline, fonts)
- [x] Spike implementations (all 4 pass)
- [ ] Build lesson parser (step 3 of pipeline)
- [ ] Build TTS engine (step 4) — extract from spike_01
- [ ] Build video card renderer (step 5) — extract from spike_02
- [ ] Build video assembler (step 6) — extract from spike_03/04
- [ ] Add `--render-video` CLI flag
- [ ] Add more vocabulary themes (daily routine, shopping, school, etc.)
- [ ] Optional: pipe output directly to an LLM API (OpenAI / Ollama)
- [ ] Optional: export generated lessons to Anki-compatible format
- [ ] Optional: download & use Noto Sans JP instead of system Yu Gothic
