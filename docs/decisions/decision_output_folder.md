# Decision: Output Folder Structure

**Status:** Decided — language/theme/lesson bundle with user-scoped cache  
**Date:** 2026-03-28  
**Context:** The original output layout was inconsistent — eng-jap lessons had no
language subfolder, cards and audio sat alongside lesson folders rather than inside
them, video was named `lesson_001_food.mp4` next to the lesson bundle, and the LLM
cache lived under `output/.cache/` inside the project tree. As the tool gained
support for multiple language pairs (eng-jap, hun-eng) and multiple themes, the
flat layout became unnavigable and made lesson re-render and Anki export fragile.

---

## Problems with the Old Layout

```
output/
  lesson_001/              ← eng-jap only, no lang prefix
    content.json
  cards/                   ← shared, not lesson-scoped
    card_001.png
  audio/                   ← shared, not lesson-scoped
    item_001.mp3
  lesson_001_food.mp4      ← alongside folder, not inside
  hun-eng/
    food/
      lesson_001/          ← different depth for hun-eng
        content.json
  .cache/                  ← dev cache inside project tree, ends up in backups / git
    abc123.json
```

| Problem | Impact |
|---------|--------|
| No language prefix for eng-jap | Adding a second eng-* pair would collide |
| Cards/audio not in lesson bundle | Re-rendering one lesson clobbered another's assets |
| Video outside lesson folder | Anki export couldn't locate all lesson files by path prefix |
| Cache inside project | Cache bloats git status, gets included in zip backups, wrong scope |
| `_DEFAULT_OUTPUT_DIR` baked into `lesson_store` | Callers couldn't override path per lesson |

---

## Decision: Fully Self-Contained Lesson Bundle

Every lesson output is isolated in a single directory. The language code is always
present at the top level, regardless of language pair.

```
output/
└── {language}/                    ← always present (e.g. "eng-jap", "hun-eng")
    ├── vocab/
    │   └── {theme}.json           ← accumulated shared vocab across all lessons for this lang+theme
    └── {theme}/                   ← e.g. "totoro", "food"
        └── lesson_{id:03d}/       ← zero-padded three digits
            ├── content.json       ← LLM-generated lesson content
            ├── report.md          ← per-lesson generation report
            ├── lesson.mp4         ← rendered video (simplified name, no redundant theme suffix)
            ├── cards/
            │   └── card_001.png
            └── audio/
                └── item_001.mp3

~/.jlesson/
└── cache/
    └── {sha256}.json              ← LLM prompt cache (user-scoped, not project-scoped)
```

---

## Path Resolution: Single Source of Truth

All output paths are resolved by `jlesson/lesson_pipeline/pipeline_paths.py`.
No other module constructs output paths independently.

```python
resolve_lang_dir(config)              # output/{language}/
resolve_lesson_dir(config, lesson_id) # output/{language}/{theme}/lesson_{id:03d}/
```

`resolve_output_dir` is retained as a backward-compatibility shim that delegates to
`resolve_lang_dir`.

---

## LLM Cache: Moved to User Home

| | Old | New |
|---|---|---|
| **Path** | `output/.cache/{sha256}.json` | `~/.jlesson/cache/{sha256}.json` |
| **Scope** | Project | User |
| **Override** | `LLM_CACHE_DIR` env var | Same |

**Rationale:** The cache is a developer speed tool, not lesson content. It should
persist across project checkouts and not appear in `git status`. The user home
location is consistent with tools like `pip`, `npm`, and VS Code extensions.

---

## Lesson Store API Change

The `lesson_store` module no longer constructs the lesson directory path internally.
Callers are responsible for providing the full `lesson_dir` path, obtained via
`resolve_lesson_dir`.

```python
# Old
save_lesson_content(content, output_dir=Path("output"))
# → internally appended lesson_001/

# New
lesson_dir = resolve_lesson_dir(config, lesson_id)
save_lesson_content(content, lesson_dir)
# caller owns the full path
```

This makes the contract explicit and removes hidden coupling between `lesson_store`
and the path resolution strategy.

---

## Rejected Alternatives

### Flat lesson folder (no theme subfolder)
`output/{language}/lesson_{id:03d}/` — rejected because lesson IDs are per-theme and
would collide when a user runs multiple themes. Two separate `lesson_001` folders under
the same language would overwrite each other.

### Theme in filename instead of folder
`output/{language}/food_lesson_001/` — rejected because it complicates glob patterns
and prefix-based lookups; a folder per theme is a natural container.

### Keep cache in project
Rejected: pollutes `git status`, ends up in backups and zip archives, shared per-project
instead of per-user — wrong scope for a speed-optimisation artefact.
