# Japanese Lesson Generator

CLI tool that generates structured Japanese learning lessons with high repetition, combining vocabulary and grammar in a single unit.

## Problem

Most Japanese learning materials:
1. **Focus on one area only** — just vocab, just grammar, just kanji — never combined
2. **Low repetition** — you see a word once or twice, then move on

This tool produces lessons where every word gets **5 touches** (introduce → recall → reinforce → self-check → lock-in) and grammar sentences get **3 touches** (translate → comprehend → reinforce), totalling **87 items per unit**.

## Quick Start

```bash
# Install dependencies (optional, for video/LLM features)
pip install -e .[all]
conda install -c conda-forge ffmpeg

# No dependencies needed for core CLI (stdlib only)
python generate_lesson.py --create --theme food

# Output:
#   output/lesson_food.json   ← structured items (for video pipeline)
#   output/lesson_food.md     ← human-readable lesson
```

## Usage

```bash
# List available themes
python generate_lesson.py --list-themes

# Generate a complete lesson (deterministic, no LLM needed)
python generate_lesson.py --create --theme food
python generate_lesson.py --create --theme food --nouns 4 --verbs 4
python generate_lesson.py --create --theme food --seed 42

# Generate video from lesson (fast FFmpeg method by default)
python generate_lesson.py --create --theme food --render-video
python generate_lesson.py --create --theme food --render-video --video-method moviepy

# Generate an LLM prompt instead (for pasting into ChatGPT etc.)
python generate_lesson.py --theme food -o prompt.md

# Generate vocab for a new theme (via LLM)
python generate_lesson.py --generate-vocab shopping
python generate_lesson.py --generate-vocab school --level intermediate
```

## Lesson Structure

Each lesson has 3 phases:

| Phase | Items | Touches/Item | Total |
|-------|-------|-------------|-------|
| **Nouns** | 6 | 5 (INTRODUCE → RECALL → REINFORCE → SELF-CHECK → LOCK-IN) | 30 |
| **Verbs** | 6 | 5 (same cycle) | 30 |
| **Grammar** | 9 sentences | 3 (TRANSLATE → COMPREHEND → REINFORCE) | 27 |
| **Total** | | | **87** |

Grammar covers 3 persons (I, You, He/She) × 3 verb-noun pairs with polite-form conjugation.

## Vocabulary Themes

Themes are JSON files in `vocab/`:

| Theme | Nouns | Verbs | Grammar Pairs |
|-------|-------|-------|---------------|
| `food` | 12 (water, rice, fish, …) | 10 (eat, drink, cook, …) | eat+fish, drink+water, cook+meat |
| `travel` | 12 (station, airport, …) | 10 (go, come, return, …) | — |

Add new themes by saving LLM output from `--generate-vocab` as `vocab/<theme>.json`.

## Project Structure

```
japanese/
├── generate_lesson.py    # CLI entry point
├── lesson_generator.py   # Deterministic lesson builder
├── prompt_template.py    # LLM prompt templates
├── vocab/                # Vocabulary JSON files
├── docs/                 # Decision documents
├── spike/                # Proof-of-concept scripts
└── output/               # Generated lessons (gitignored)
```

## Installation

### Core CLI (No Dependencies)
The core CLI works with Python 3.10+ stdlib only:
```bash
python generate_lesson.py --create --theme food
```

### Full Installation (Video + LLM Features)
Install all dependencies using the project's pyproject.toml:
```bash
# Install Python dependencies
pip install -e .[all]

# Install ffmpeg (required for video encoding)
conda install -c conda-forge ffmpeg
```

Or install components separately:
```bash
# Video features only
pip install -e .[video]
conda install -c conda-forge ffmpeg

# LLM features only  
pip install -e .[llm]
```

Or use the automated script:
```powershell
.\install.ps1
```

This installs:
- **Video pipeline**: `edge-tts`, `moviepy`, `Pillow`
- **LLM integration**: `openai`
- **System dependency**: `ffmpeg`

**⚠️ Note**: Video generation requires internet access for TTS (Microsoft Edge TTS service).

## Design Principles

- **YAGNI** — no frameworks, no databases, stdlib-only core
- **KISS** — flat JSON vocab, argparse CLI, pure functions
- **DRY** — shared repetition cycle logic
- **Low coupling** — modules communicate via dicts and paths
- **Deterministic first** — works fully offline with no LLM; LLM enhances quality when available

## Requirements

- Python 3.10+
- No pip dependencies for core CLI
- Video pipeline: `edge-tts`, `moviepy`, `Pillow`, `ffmpeg`
- LLM integration (planned): `openai` + Ollama server

Install all dependencies with: `pip install -e .[all]` and `conda install -c conda-forge ffmpeg`

## License

MIT
