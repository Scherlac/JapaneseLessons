# Japanese Lesson Generator

CLI tool that generates structured Japanese learning lessons with high repetition, combining vocabulary and grammar in a single unit.

## Problem

Most Japanese learning materials:
1. **Focus on one area only** — just vocab, just grammar, just kanji — never combined
2. **Low repetition** — you see a word once or twice, then move on

This tool produces lessons where every word gets **5 touches** (introduce → recall → reinforce → self-check → lock-in) and grammar sentences get **3 touches** (translate → comprehend → reinforce), totalling **87 items per unit**.

## Quick Start

```bash
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

## Video Pipeline (In Progress)

The tool can also generate learning videos from lessons:

```
Lesson items → TTS audio (edge-tts) → Card images (Pillow) → Video (moviepy) → .mp4
```

All components have been validated via spike implementations. Production modules are next.

Install video dependencies:
```bash
pip install edge-tts moviepy Pillow
conda install -c conda-forge ffmpeg
```

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

## License

MIT
