# Japanese Lesson Generator

CLI tool that generates structured Japanese lessons driven by an LLM, with a curriculum grammar progression system and rendered video output.

## Problem

Most Japanese learning materials:
1. **Focus on one area only** — just vocab, just grammar, just kanji — never combined
2. **Low repetition** — you see a word once or twice, then move on
3. **No progression** — grammar points introduced randomly, not built on prior knowledge

This tool produces lessons where vocabulary and grammar are always taught together, grammar unlocks progressively lesson-by-lesson, and every lesson is rendered as a video with TTS audio.

## Quick Start

```bash
# Activate your conda environment first (do NOT use conda run — it hides live output)
conda activate <your-env>

# Install dependencies
pip install -e .[all]
conda install -c conda-forge ffmpeg

# Run the two-lesson demo (requires LM Studio running on the network)
python spike/spike_09_demo.py

# Output:
#   output/demo/lesson_01_food.mp4    ← rendered video
#   output/demo/lesson_02_travel.mp4
#   output/demo/curriculum_demo.json  ← lesson dictionary
```

## CLI Usage

```bash
# List available vocab themes
jlesson vocab list

# Show current curriculum progress
jlesson curriculum show

# Generate the next lesson (full pipeline: LLM → content → video)
jlesson lesson next --theme food
jlesson lesson next --theme travel --nouns 5 --verbs 4 --seed 7
jlesson lesson next --theme food --no-video          # skip video render
jlesson lesson next --theme food --no-cache           # bypass LLM cache

# Print an LLM-ready lesson prompt to stdout (no LLM call)
jlesson lesson prompt food
jlesson lesson prompt travel -n 4 -v 4 -s 7
jlesson lesson prompt food -o prompt.md

# Generate a vocab file for a new theme via LLM (saves to vocab/<theme>.json)
jlesson vocab create animals
jlesson vocab create school --nouns 15 --verbs 12 --level intermediate
# Generate a total count while guaranteeing minimum nouns/verbs
jlesson vocab create school --count 120 --nouns 40 --verbs 20
# Include adjectives too (exact if no --count, minimum if --count is set)
jlesson vocab create school --count 120 --nouns 35 --verbs 20 --adjectives 15
# If theme exists, create is blocked by default (to prevent overwrite)
jlesson vocab create school --force

# Extend an existing theme by adding unique items (merge + dedup)
jlesson vocab extend animals --nouns 20 --verbs 8
# Extend by total count with minimum guarantees
jlesson vocab extend animals --count 60 --nouns 20 --verbs 10
jlesson vocab extend animals --count 60 --nouns 15 --verbs 10 --adjectives 10

# Print a vocab-generation prompt without calling the LLM
jlesson vocab generate-prompt shopping
```

## RCM — Runtime Content Management

The RCM store is a SQLite database that caches canonical items, compiled assets (audio, cards), and LLM usage records across lessons and language pairs. It allows later lessons to reuse already-generated content without re-calling the LLM or re-rendering assets.

Set the RCM directory once in `.env`:

```env
JLESSON_RCM_PATH=/path/to/.jlesson/rcm
```

All `rcm` subcommands read this by default; override per-run with `--rcm <dir>`.

### Importing existing lessons

```bash
# Import all lessons under a directory tree (language auto-detected from path)
python tools/import_lessons_to_rcm.py --source-dir output/northern_exposure

# With an explicit fallback language and curriculum for lesson ID mapping
python tools/import_lessons_to_rcm.py \
    --source-dir output/northern_exposure \
    --language eng-fre \
    --curriculum output/northern_exposure/curriculum_french.json
```

The importer walks the tree for `steps/lesson_planner/output.json` files, upserts items and branches, copies compiled audio/card assets into the central store, and imports LLM usage token records.

### Inspecting the store

```bash
# Overall database summary
jlesson rcm stats

# List all lessons and item counts
jlesson rcm lessons

# Query canonical items with filters
jlesson rcm items                               # all items (default limit 50)
jlesson rcm items --phase verbs                 # only verbs
jlesson rcm items --language eng-fre            # items with a French branch
jlesson rcm items --min-branches 2              # items resolved in 2+ languages
jlesson rcm items --text arriver                # substring match on canonical text
jlesson rcm items --phase nouns --language eng-fre --text matin --limit 100

# Check asset availability for a lesson
jlesson rcm lesson-assets 3 --language eng-fre
# Migrate legacy absolute paths to relative (makes store relocatable)
jlesson rcm lesson-assets 3 --language eng-fre --fix

# LLM token usage per lesson
jlesson rcm lesson-usage 3 --language eng-fre
jlesson rcm lesson-usage 3 --language eng-fre --verbose   # per-call breakdown

# LLM token usage for a single canonical item
jlesson rcm item-usage verbs_to_arrive_fe2171 --language eng-fre
```

When the wrong language is passed to a lesson command, the error message lists which languages are actually stored for that lesson.


## How a Lesson Works

Each lesson is driven by the LLM in three steps:

| Step | What happens |
|------|-------------|
| **Grammar select** | LLM picks 2 unlocked grammar points appropriate for this lesson number |
| **Sentence generate** | LLM writes practice sentences for each grammar point using lesson vocabulary |
| **Noun practice** | LLM produces example sentences and memory tips for each noun |

The results are assembled into a video: one card per item (nouns + sentences), TTS audio, exported as MP4.

## Curriculum & Grammar Progression

`curriculum.py` tracks which grammar points have been covered and unlocks new ones as lessons complete:

| Level | Grammar points |
|-------|---------------|
| 1 | `action_present_affirmative`, `identity_present_affirmative` |
| 2 | `action_present_negative`, `action_past_affirmative`, `question_ka`, `direction_ni_ikimasu`, `existence_arimasu`, `adjective_na` |
| 3 | `action_past_negative`, `desire_tai`, `desire_hoshii`, `reason_kara` |
| 4 | `te_form_request`, `te_form_progressive`, `potential_dekimasu` |

Level 2 grammar unlocks only after level 1 is covered, and so on up the chain.

## Vocabulary Themes

Themes are JSON files in `vocab/`. Missing theme files are auto-generated by the LLM when first needed.

| Theme | Nouns | Verbs |
|-------|-------|-------|
| `food` | 9 (rice, bread, meat, …) | 6 (eat, drink, cook, …) |
| `travel` | 9 (ticket, bag, map, …) | 6 (go, take a train, …) |

Add a new theme explicitly:
```bash
jlesson vocab create <theme>
```

Or pass a new theme name to the demo — it will generate the vocab automatically.

## Project Structure

```
jlesson/              ← all production Python source
├── cli.py            # CLI entry point (click subcommands)
├── curriculum.py     # Grammar progression table + lesson dictionary CRUD
├── vocab_generator.py# LLM-driven vocab generation + schema validation
├── prompt_template.py# LLM prompt builders (7 pure functions)
├── llm_client.py     # Universal LLM client (OpenAI SDK)
├── config.py         # LLM provider settings
├── video/
│   ├── tts_engine.py # TTS audio generation (edge-tts)
│   ├── cards.py      # 1080p lesson card renderer (Pillow)
│   └── builder.py    # Video assembler (moviepy + ffmpeg)
└── exporters/        # Export adapters (video, Anki, text — planned)
vocab/                # Vocabulary JSON files
curriculum/           # Lesson dictionary (curriculum.json)
docs/                 # Technology decision documents
tests/                # Unit test suite (274 tests)
spike/                # Proof-of-concept scripts
└── spike_09_demo.py  # End-to-end two-lesson demo with video output
output/               # Generated lessons and videos (gitignored)
```

## Documentation Map

Use the documentation set by intent:

- `progress_report.md` — current feature development and near-term priorities
- `docs/feature_progress.md` — feature-by-feature implementation status and milestones
- `docs/project_scale.md` — system-level scale topics and growth pressure
- `docs/architecture.md` — compact arc42-style architecture reference
- `docs/development_history.md` — completed work, spikes, and historical detail
- `docs/software_engineering.md` — engineering process and working principles
- `docs/structure.md` — touch-system and repetition model

## Installation

```bash
# Activate conda environment first
conda activate <your-env>

# Full install (video + LLM)
pip install -e .[all]
conda install -c conda-forge ffmpeg
```

Or install components separately:
```bash
pip install -e .[video]   # edge-tts, moviepy, Pillow
pip install -e .[llm]     # openai
conda install -c conda-forge ffmpeg
```

Or use the automated script:
```powershell
.\install.ps1
```

## Dependency Analysis

Generate the internal module dependency reports for `jlesson`:

```powershell
.\tools\analyze_internal_dependencies.ps1
```

Outputs:
- `docs/internal_module_dependencies.md` — main Markdown report with Mermaid diagram
- `docs/internal_module_dependency_details.md` — detailed paths and focused boundaries
- `docs/internal_module_dependencies.mmd` — raw Mermaid source
- `output/internal_module_dependencies.json` — raw graph data

Override the focused boundaries if needed:

```powershell
.\tools\analyze_internal_dependencies.ps1 -FocusGroup lesson_pipeline:video -FocusGroup lesson_pipeline:asset_compiler
```

**⚠️ Notes:**
- Video generation requires internet access for TTS (Microsoft Edge TTS service)
- LLM features require [LM Studio](https://lmstudio.ai) (or any OpenAI-compatible server) — configure URL in `.env`
- Recommended model: `qwen/qwen3-14b` (best Japanese quality in testing)

## LLM Setup

All runtime settings are in `.env` (project root, gitignored). A `.env.template` file is included with supported keys.

```env
LLM_BASE_URL=http://localhost:1234/v1   # LM Studio default
LLM_MODEL=qwen/qwen3-14b                # recommended model
LLM_NO_THINK=true
JLESSON_RCM_PATH=/path/to/.jlesson/rcm  # path to the RCM directory for lesson generation and rcm CLI commands
```

The client uses the OpenAI SDK and works with LM Studio, Ollama, or OpenAI. LM Studio requires `json_schema` response format (not `json_object`) — this is handled automatically.

## Design Principles

- **YAGNI** — no frameworks, no databases, stdlib-only core
- **KISS** — flat JSON vocab, click CLI, pure functions
- **DRY** — shared prompt builders, single LLM client
- **Low coupling** — modules communicate via plain dicts and file paths
- **LLM-driven** — natural sentences and grammar selection via LLM; video pipeline handles rendering

## Requirements

- Python 3.10+
- LM Studio (or compatible OpenAI server) for lesson generation
- `edge-tts`, `moviepy`, `Pillow`, `ffmpeg` for video output
- `openai` for LLM client

## License

MIT
