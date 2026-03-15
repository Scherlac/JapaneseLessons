# Decision: Anki Export

**Status:** Decided — `genanki` when ready; TSV as a quick interim option; blocked on TD-02  
**Date:** 2026-03-15  
**Context:** Anki is the dominant spaced-repetition flashcard tool. Exporting generated lessons
to Anki creates a strong study loop: video lessons introduce material, Anki cards ensure retention.
This feature is Priority 2 in the roadmap but is blocked on lesson content persistence (TD-02)
being implemented first. This document makes the technology decision now so implementation can
proceed immediately once the prerequisite is ready.

---

## What Anki Export Needs to Produce

For each lesson, export cards covering:
- **Vocabulary**: English → Japanese (kanji + kana + romaji) for each noun and verb
- **Grammar sentences**: English ↔ Japanese for each generated sentence
- **Verb conjugation**: English prompt → all four polite forms (present/past × aff/neg)

Minimum card schema (two-sided note):
```
Front: water
Back:  水 (みず, mizu)
```

Extended card schema (with tts or audio hint):
```
Front: water
Back:  水 (みず, mizu) [Sound:water.mp3]
```

---

## Anki File Formats

Anki supports three import mechanisms:

| Format | Description | Notes |
|--------|-------------|-------|
| `.apkg` (Anki Package) | Binary package — deck + cards + media + note types | The standard; requires `genanki` to generate |
| `.txt` / `.tsv` tab-separated | Plain text import via Anki's "Import File" UI | Simplest; no media; user must manually create note type |
| AnkiConnect REST API | HTTP API for running Anki instance | Requires Anki desktop running; complex setup |

---

## Options

### Option 1: `genanki` (NOT INSTALLED — requires pip install)

**What:** The de-facto Python library for generating Anki `.apkg` packages.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install genanki` (~100KB) |
| **Output** | `.apkg` binary — drag-and-drop into Anki, works immediately |
| **Note types** | Define custom note types (fields + card templates with CSS) |
| **Media** | Bundle audio files (`.mp3`) inside the package |
| **Tags** | Lesson/theme tags on each card |

```python
import genanki, random

model = genanki.Model(
    random.randrange(1 << 30, 1 << 31),
    "Japanese Vocab",
    fields=[
        {"name": "English"},
        {"name": "Japanese"},
        {"name": "Romaji"},
        {"name": "Audio"},
    ],
    templates=[{
        "name": "English → Japanese",
        "qfmt": "{{English}}",
        "afmt": "{{FrontSide}}<hr>{{Japanese}}<br>{{Romaji}}<br>{{Audio}}",
    }],
)

notes = [
    genanki.Note(model=model, fields=["water", "水 (みず)", "mizu", "[sound:water.mp3]"])
    for item in lesson_content.noun_items
]

deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), "Japanese: Lesson 1 — Food")
for note in notes: deck.add_note(note)

package = genanki.Package(deck)
package.media_files = [str(p) for p in audio_paths]
package.write_to_file("lesson_001.apkg")
```

**Pros:** Professional output; bundled audio; custom card templates; Anki reads natively; no user configuration needed  
**Cons:** New dependency (`genanki`); model/deck IDs must be stable across exports (random IDs cause duplicates on re-import)

---

### Option 2: Tab-separated text (TSV) export — no install

**What:** Anki can import tab-separated text files. Cards have `Front\tBack` format.

```python
def export_tsv(lesson_content, output_path):
    lines = []
    for noun in lesson_content.noun_items:
        front = noun["english"]
        back  = f"{noun['kanji']} ({noun['japanese']}, {noun['romaji']})"
        lines.append(f"{front}\t{back}")
    for s in lesson_content.sentences:
        lines.append(f"{s['english']}\t{s['japanese']}")
    output_path.write_text("\n".join(lines), encoding="utf-8")
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib |
| **Output** | `.txt` file — user imports via Anki UI |
| **Media** | Not supported in TSV |
| **Note type** | User must pre-create or use Anki's basic type |
| **Complexity** | ~15 lines of code |

**Pros:** Zero dependency; immediate to implement; useful as a quick win  
**Cons:** No audio; user must manually import and configure note type; not a polished deliverable

---

### Option 3: AnkiConnect REST API (NO INSTALL — requires Anki desktop)

**What:** Anki desktop has an add-on (AnkiConnect) that exposes a REST API. Cards can be
created via `POST http://localhost:8765` without file intermediaries.

```python
import requests
requests.post("http://localhost:8765", json={
    "action": "addNote",
    "params": {"note": {"deckName": "...", "modelName": "Basic", "fields": {...}}}
})
```

**Pros:** No file generation; cards appear in Anki immediately  
**Cons:** Requires AnkiConnect add-on installed; requires Anki desktop running; tight coupling to user's Anki setup; too fragile for a general-purpose tool

---

## Decision: `genanki` for `.apkg` (when ready) + TSV as interim ✅

**Rationale:**
- **TSV first** — zero dependency, ~15 lines, can be implemented immediately alongside TD-02. Provides an Anki export option with no additional blocking.
- **`genanki` for polished export** — when the export feature becomes Priority 1, `genanki` produces a professional result with bundled audio (the TTS `.mp3` files are already generated per lesson). The audio-in-Anki experience significantly improves pronunciation learning.
- AnkiConnect is too fragile and environment-dependent for a general CLI tool.

**Stable ID strategy for `genanki`:**
- Deck ID: `int(sha256(deck_name)[:8], 16)` — deterministic from lesson title
- Note ID: `int(sha256(front_text)[:8], 16)` — deterministic from card front
- Ensures re-importing the same lesson does not create duplicate cards

**Prerequisite:** Requires TD-02 (lesson content persistence) to be completed first.
Lesson content must be saved to `output/<id>/content.json` before it can be exported.

**Export command (target CLI):**
```
jlesson lesson export 1 --format anki   → output/lesson_001/lesson_001.apkg
jlesson lesson export 1 --format tsv    → output/lesson_001/lesson_001.tsv
```
