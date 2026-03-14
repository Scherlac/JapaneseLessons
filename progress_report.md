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
└── vocab/
    ├── food.json         # 12 nouns + 10 verbs
    └── travel.json       # 12 nouns + 10 verbs
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

## Next Steps

- [ ] Add more vocabulary themes (daily routine, shopping, school, etc.)
- [ ] Optional: pipe output directly to an LLM API (OpenAI / Ollama)
- [ ] Optional: add an `--interactive` mode that feeds the prompt and streams back the lesson
- [ ] Optional: export generated lessons to Anki-compatible format
- [ ] Consider adding dimension selection flags (e.g. `--tense past` to limit scope)
