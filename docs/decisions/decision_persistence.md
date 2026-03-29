# Decision: Persistence / Storage

**Status:** Decided — JSON files (lesson content) + existing curriculum.json (index)  
**Date:** 2026-03-15  
**Context:** The curriculum system uses `curriculum/curriculum.json` as a lesson index, but
lesson-level content (generated sentences, noun items, memory tips) is discarded after each
video render. TD-02 (HIGH) — content must be persisted to enable re-render, Anki export,
and text review. The question is what storage technology to use.

---

## What Needs to Be Stored

| Data | Volume | Current | Need |
|------|--------|---------|------|
| Curriculum index (lesson list, covered vocab/grammar) | ~10KB | `curriculum/curriculum.json` | Keep as-is |
| Per-lesson content (sentences, noun_items, verb_items) | ~5-30KB per lesson | Discarded | **New** |
| LLM prompt cache (sha256 → response) | ~10-50KB per entry | None | See decision_caching.md |
| Generated audio files | ~50-200KB per lesson | `output/<id>/audio/` | Already written |
| Generated video | ~500KB-2MB per lesson | `output/<id>/` | Already written |

The primary gap is the structured JSON content produced by LLM calls — it needs a home.

---

## Options

### Option 1: JSON files per lesson (current pattern extended)

**What:** Write `output/<lesson_id>/content.json` containing all LLM-generated content.
The `curriculum.json` remains the index; content files are the payloads.

```
output/
  lesson_001/
    content.json      ← { noun_items, verb_items, sentences, grammar_ids }
    lesson_001.mp4
    audio/
      item_001.mp3
    cards/
      card_001.png
```

`content.json` schema:
```json
{
  "lesson_id": 1,
  "theme": "food",
  "grammar_ids": ["action_present_affirmative"],
  "noun_items": [{ "english": "water", "example_sentence_jp": "...", "memory_tip": "..." }],
  "verb_items": [{ "english": "to eat", "polite_forms": { ... } }],
  "sentences": [{ "japanese": "...", "english": "...", "grammar_id": "..." }],
  "created_at": "2026-03-15T12:00:00Z"
}
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib `json` + `pathlib` |
| **Schema** | Free-form dict; no enforcement unless pydantic model added |
| **Queryability** | Load-all-and-filter; no SQL queries needed for this scale |
| **Inspectability** | Fully human-readable; easy to diff, inspect, edit |
| **gitignore** | `output/` already gitignored |
| **Max scale** | 100+ lessons × ~20KB = ~2MB total — trivially small |

**Pros:** KISS; zero dependency; consistent with existing pattern; easy to gitignore; trivially human-readable  
**Cons:** No cross-lesson queries without loading all files; no ACID transactions

---

### Option 2: SQLite (`sqlite3` — stdlib)

**What:** Embedded SQL database. `sqlite3` is in the Python stdlib (3.42.0 confirmed installed).

```python
import sqlite3
conn = sqlite3.connect("output/lessons.db")
conn.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY,
        theme TEXT,
        content JSON,
        created_at TEXT
    )
""")
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib |
| **Schema** | Structured; migrations needed as schema evolves |
| **Queryability** | Full SQL; `SELECT * FROM lessons WHERE theme = 'food'` |
| **Inspectability** | Requires sqlite3 CLI or tool; not plain text |
| **Transactions** | ACID; safe for concurrent writes (though not needed here) |

**Pros:** Powerful queries; stdlib; single file database  
**Cons:** Schema migration headache as content shape evolves; overkill for document-like data where "query all lessons" is the only access pattern; not gitignore-friendly (binary file); harder to inspect manually

---

### Option 3: `shelve` (stdlib)

**What:** Python key-value store backed by `dbm`. `shelve.open("lessons")` returns a dict-like object.

```python
import shelve
with shelve.open("output/lessons") as db:
    db[str(lesson_id)] = lesson_content
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib |
| **Schema** | None — arbitrary Python objects |
| **Inspectability** | Not human-readable (binary dbm format) |
| **Platform** | Backend varies by platform (`gdbm`, `ndbm`, `dumbdbm`) |

**Pros:** Zero setup; arbitrary Python objects  
**Cons:** Not human-readable; platform-dependent backend; harder to test and inspect; JSON files are strictly better for this use case

---

### Option 4: `TinyDB` (NOT INSTALLED)

**What:** Lightweight document database in pure Python, JSON-backed.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install tinydb` (~40KB) |
| **Model** | JSON documents in a single `db.json` file |
| **Query** | `db.table('lessons').search(where('theme') == 'food')` |
| **Inspectability** | Single JSON file — human-readable |

**Pros:** Document-oriented; queryable; human-readable backing store  
**Cons:** New dependency; single JSON file for all lessons (vs one file per lesson → easier individual gitignore/delete); TinyDB provides query capability we don't need at this scale

---

## Decision: JSON files per lesson (Option 1) ✅

**Rationale:**
- Complete alignment with existing pattern (`curriculum.json`, `vocab/*.json`)
- Zero new dependency
- Fully human-readable and inspectable — important for debugging LLM output quality
- Scale is trivially small (~100 lessons max in foreseeable future)
- The only query pattern needed is "load lesson N" — no cross-lesson aggregation
- SQLite and TinyDB address problems we don't have (complex queries, concurrent writes)
- `shelve` is strictly worse than JSON files for this use case

**Implementation:**
- `lesson_store.py` module with:
  - `save_lesson_content(lesson_id, content, output_dir) -> Path`
  - `load_lesson_content(lesson_id, output_dir) -> dict`
  - `lesson_content_path(lesson_id, output_dir) -> Path`
- `content.json` validated by a `pydantic` model `LessonContent` (see `decision_config_validation.md`)
- `curriculum.json` keeps existing schema; lesson metadata stays there; content files are the detail layer

**Directory layout:**
```
output/
  lesson_001/
    content.json          ← LLM-generated sentences, noun/verb items
    .checkpoint.json      ← pipeline checkpoint (deleted on success)
    lesson_001.mp4
    audio/
    cards/
  lesson_002/
    ...
curriculum/
  curriculum.json         ← index only
```
