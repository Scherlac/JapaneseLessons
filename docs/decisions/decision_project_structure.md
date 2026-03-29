# Decision: Project Folder Structure

**Status:** DECIDED  
**Date:** 2025-07  
**Context:** Pre-implementation planning before TD-01/TD-02 work begins

---

## Problem

All nine production Python modules live flat at the project root alongside test infrastructure,
documentation, data files, and tooling. Adding the four modules implied by the package research
decisions (`models.py`, `lesson_pipeline.py`, `lesson_store.py`, `llm_cache.py`) plus a new
`exporters/` sub-package would push the root to 13+ `.py` files with no grouping — unnavigable
and packaging-hostile (`py-modules` must list every file manually).

### Current root (annotated)

```
config.py               ← production: infrastructure
curriculum.py           ← production: domain
generate_lesson.py      ← production: CLI entry point
llm_client.py           ← production: infrastructure
prompt_template.py      ← production: domain
tts_engine.py           ← production: video pipeline
video_builder.py        ← production: video pipeline
video_cards.py          ← production: video pipeline
vocab_generator.py      ← production: application layer

pyproject.toml          ← ok •  uses py-modules (doesn't scale)
README.md               ← ok
install.ps1             ← ok
requirements.txt        ← ✗ redundant with pyproject.toml [delete]
structure.md            ← ✗ doc at root, should live in docs/ [move]
progress_report_prev.md ← ✗ archived to development_history.md [delete]
.coverage               ← ✗ not in .gitignore

curriculum/             ← ok: runtime state data
vocab/                  ← ok: vocabulary source data
output/                 ← ok: gitignored generated artifacts
docs/                   ← ok
spike/                  ← ok
tests/                  ← ok
```

### Root-level `py-modules` problem

```toml
# pyproject.toml today — every new file requires a manual entry
[tool.setuptools]
py-modules = [
    "generate_lesson", "curriculum", "vocab_generator",
    "prompt_template", "llm_client", "config",
    "tts_engine", "video_cards", "video_builder",
]
```

Setuptools `py-modules` lists individual `.py` files. It cannot express sub-packages or
auto-discover new modules. Switching to a proper package (`jlesson/`) unlocks
`packages.find` auto-discovery — no manual maintenance.

---

## Decision

**Move all production Python source into a `jlesson/` package at the project root.**

Group the three tightly-coupled video modules into a `jlesson/video/` sub-package.  
Reserve `jlesson/exporters/` for the planned adapter modules (video, Anki, text).  
Keep all data directories (`vocab/`, `curriculum/`), tooling, and test infrastructure where they are.

This is a **flat package layout** (package sits at project root, not inside `src/`). For a
single-developer CLI tool installed in editable mode, the `src/` layout provides no meaningful
benefit over a clearly-named top-level package.

---

## Proposed Structure

```
c:\01_dev\JapaneseLessons\
│
├── jlesson/                        ← NEW: all production Python source
│   ├── __init__.py                 ← NEW: marks directory as package
│   ├── cli.py                      ← MOVED: was generate_lesson.py
│   ├── config.py                   ← MOVED
│   ├── models.py                   ← NEW: pydantic schemas (all data shapes)
│   ├── curriculum.py               ← MOVED
│   ├── prompt_template.py          ← MOVED
│   ├── vocab_generator.py          ← MOVED
│   ├── llm_client.py               ← MOVED
│   ├── llm_cache.py                ← NEW: sha256 dev cache (stdlib only)
│   ├── lesson_pipeline.py          ← NEW: LessonContext + stage functions
│   ├── lesson_store.py             ← NEW: output/<id>/content.json I/O
│   │
│   ├── video/                      ← NEW: video production sub-package
│   │   ├── __init__.py
│   │   ├── tts_engine.py           ← MOVED (name kept for clarity)
│   │   ├── cards.py                ← MOVED: was video_cards.py
│   │   └── builder.py             ← MOVED: was video_builder.py
│   │
│   └── exporters/                  ← NEW: export adapters sub-package
│       ├── __init__.py
│       ├── video_exporter.py       ← NEW
│       ├── anki_exporter.py        ← NEW
│       └── text_exporter.py        ← NEW
│
├── tests/                          ← stays; all imports updated
│   ├── __init__.py
│   ├── test_curriculum.py
│   ├── test_llm_client.py
│   ├── test_prompt_template.py
│   ├── test_tts_engine.py
│   ├── test_video_builder.py
│   ├── test_video_cards.py
│   └── test_vocab_generator.py
│
├── spike/                          ← stays (sys.path.insert already present)
├── docs/                           ← stays
│   └── structure.md                ← MOVED from root
│
├── vocab/                          ← stays: vocabulary source data
├── curriculum/                     ← stays: runtime lesson-progress state
├── output/                         ← stays: gitignored generated artifacts
│
├── pyproject.toml                  ← UPDATED (see below)
├── README.md                       ← UPDATED (CLI command examples)
└── install.ps1
```

**Files deleted from root:**
- `requirements.txt` — superseded by `pyproject.toml` since project inception
- `progress_report_prev.md` — all content archived to `docs/development_history.md`

---

## Migration Impact

### 1. `pyproject.toml` changes

```toml
# BEFORE
[tool.setuptools]
py-modules = ["generate_lesson", "curriculum", ...]

[project.scripts]
japanese-lesson = "generate_lesson:main"

# AFTER
[tool.setuptools.packages.find]
where = ["."]
include = ["jlesson*"]

[project.scripts]
jlesson = "jlesson.cli:main"
```

The `package-data` entry for `vocab/*.json` is removed — vocab files are runtime data in the
`vocab/` directory, not package resources, and are found by path at runtime.

pytest config needs no change; `pythonpath = ["."]` continues to resolve `jlesson` correctly.

### 2. Test import updates (all 7 test files)

| Test file | Old import | New import |
|-----------|-----------|-----------|
| `test_curriculum.py` | `from curriculum import ...` | `from jlesson.curriculum import ...` |
| `test_llm_client.py` | `from llm_client import ...` | `from jlesson.llm_client import ...` |
| `test_prompt_template.py` | `from prompt_template import ...` | `from jlesson.prompt_template import ...` |
| `test_tts_engine.py` | `from tts_engine import ...` | `from jlesson.video.tts_engine import ...` |
| `test_video_builder.py` | `from video_builder import ...` | `from jlesson.video.builder import ...` |
| `test_video_cards.py` | `from video_cards import ...` | `from jlesson.video.cards import ...` |
| `test_vocab_generator.py` | `from vocab_generator import ...` | `from jlesson.vocab_generator import ...` |

### 3. Spike script updates (spike_08, spike_09 only)

Spikes already use `sys.path.insert(0, ROOT)`. After migration, their project-module imports
change from `from curriculum import ...` to `from jlesson.curriculum import ...`. The `sys.path`
trick continues to work unchanged.

Spikes 01–07 import nothing from the production package, so they need no changes.

### 4. Inter-module import updates (inside `jlesson/`)

Each moved module has imports of sibling modules that must be updated:

| File | Old | New |
|------|-----|-----|
| `cli.py` (was generate_lesson.py) | `from curriculum import ...` | `from jlesson.curriculum import ...` |
| `cli.py` | `from prompt_template import ...` | `from jlesson.prompt_template import ...` |
| `cli.py` | `from vocab_generator import ...` | `from jlesson.vocab_generator import ...` |
| `vocab_generator.py` | `from llm_client import ...` | `from jlesson.llm_client import ...` |
| `vocab_generator.py` | `from prompt_template import ...` | `from jlesson.prompt_template import ...` |

Alternatively, use **relative imports** inside the package (preferred once the package exists):

```python
# jlesson/vocab_generator.py
from .llm_client import ask_llm_json_free      # relative import
from .prompt_template import build_vocab_prompt
```

Relative imports are cleaner inside a package and avoid hard-coding the package name.

### 5. Path resolution fix in `cli.py`

`generate_lesson.py` line 35 resolves the vocab directory relative to `__file__`:

```python
# generate_lesson.py (current — works at root)
VOCAB_DIR = Path(__file__).parent / "vocab"

# jlesson/cli.py (after move — __file__ is now jlesson/cli.py)
VOCAB_DIR = Path(__file__).parent.parent / "vocab"   # one level up to project root
```

This is the only filesystem-path change required.

### 6. `.gitignore` addition

```
# coverage data
.coverage
```

---

## Migration Sequence

Execute in this order to keep tests passing at each step:

1. `git mv generate_lesson.py jlesson/cli.py` + create `jlesson/__init__.py`
2. `git mv curriculum.py jlesson/curriculum.py`
3. `git mv config.py jlesson/config.py`
4. `git mv prompt_template.py jlesson/prompt_template.py`
5. `git mv vocab_generator.py jlesson/vocab_generator.py`
6. `git mv llm_client.py jlesson/llm_client.py`
7. Create `jlesson/video/` + `jlesson/video/__init__.py`
8. `git mv tts_engine.py jlesson/video/tts_engine.py`
9. `git mv video_cards.py jlesson/video/cards.py`
10. `git mv video_builder.py jlesson/video/builder.py`
11. Update all inter-module imports inside `jlesson/` (relative imports)
12. Fix `VOCAB_DIR` path in `jlesson/cli.py` (`parent.parent`)
13. Update `pyproject.toml` (packages.find + entry point)
14. `pip install -e .` to re-register entry point
15. Update all 7 test files (flat → `jlesson.X` imports)
16. Update spike_08 and spike_09 imports
17. `pytest tests/ -m "not integration and not internet and not video"` — expect all pass
18. `git mv structure.md docs/structure.md`
19. `git rm requirements.txt`
20. `git rm progress_report_prev.md`
21. Add `.coverage` to `.gitignore`

---

## Alternatives Considered

### `src/` layout (`src/jlesson/`)

**Rejected.** The `src/` layout prevents accidental shadowing of an installed package by a
same-named directory at the project root. Here, the package is named `jlesson/` — a
project-specific name with no stdlib or common-library collision risk. The project is always
installed in editable mode by one developer. The extra directory nesting (`src/jlesson/X` vs
`jlesson/X`) adds indirection with no practical benefit.

### Keep flat root, add `__init__.py`

**Rejected.** Adding `__init__.py` at the project root makes the project root itself the package,
which pollutes the package namespace with every non-Python file in the directory. This is not a
supported packaging pattern with modern setuptools.

### Per-layer sub-packages (`jlesson/domain/`, `jlesson/infra/`, `jlesson/app/`)

**Rejected.** For a project of this size (≈12 modules), layered sub-packages impose navigation
overhead with no benefit. The video production trio (`cards`, `builder`, `tts_engine`) and the
future exporters trio are the only natural groupings.

---

## Verification

After migration, the full fast test suite must pass unchanged:

```bash
pytest tests/ -m "not integration and not internet and not video" -v
```

Expected: all unit tests pass (≈184 assertions across 7 test files).

The CLI entry point must also resolve:

```bash
jlesson --help          # replaces: python generate_lesson.py --help
```
