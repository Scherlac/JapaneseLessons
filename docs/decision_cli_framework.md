# Decision: CLI Framework

**Status:** Decided — migrate to `click`  
**Date:** 2026-03-15  
**Context:** The current CLI (`generate_lesson.py`) uses `argparse` with a flat flag structure.
As features grow (lesson pipeline, export formats, curriculum management), flat flags become
unmanageable and self-documenting help is poor. The architectural direction is now captured in
`docs/architecture.md` and the system-growth rationale in `docs/project_scale.md`.

---

## Current State

```
python generate_lesson.py --theme food
python generate_lesson.py --list-themes
python generate_lesson.py --create-vocab animals
python generate_lesson.py --show-curriculum
python generate_lesson.py --generate-vocab shopping
```

Problems:
- No subcommand grouping — unrelated operations share one flat namespace
- `--nouns` / `--verbs` default (6) silently overrides `--create-vocab` defaults (12/10) — special-cased in code
- Adding `--next-lesson`, `--render`, `--export` would push the flag count past readability
- `argparse` error messages and help text are functional but bare

---

## Options

### Option 1: `argparse` with subparsers (stdlib)

**What:** Python's built-in; add `subparsers = parser.add_subparsers()` and create sub-parsers for each group.

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib |
| **Subcommands** | Yes — `add_subparsers()` + `set_defaults(func=handler)` |
| **Type coercion** | Manual |
| **Help output** | Functional but verbose; no colour |
| **Decorator style** | No — imperative registration |
| **Testing** | Standard `parser.parse_args(['cmd', '--flag'])` |

**Pros:** No new dependency, familiar  
**Cons:** Verbose to set up; help output is mediocre; nesting subcommands is awkward; no automatic rich help pages

---

### Option 2: `click` (INSTALLED — 8.3.1)

**What:** Composable command line interface toolkit. Decorator-based command + group registration.

| Aspect | Detail |
|--------|--------|
| **Install** | Already installed |
| **Subcommands** | `@click.group()` + `@group.command()` — first-class |
| **Type coercion** | Built-in types: `INT`, `FLOAT`, `Path`, `Choice`, `File` |
| **Help output** | Clean, colour-coded, auto-generated; `--help` at every level |
| **Decorator style** | Yes — clean, readable registration |
| **Testing** | `CliRunner` built-in — invoke CLI in tests without subprocess |
| **Error handling** | `UsageError`, `BadParameter`, `Abort` — automatic formatting |
| **Composability** | Commands as objects; re-use across groups |

Example target structure:
```python
@click.group()
def cli(): ...

@cli.group()
def vocab(): ...

@vocab.command("create")
@click.argument("theme")
@click.option("--nouns", default=12)
def vocab_create(theme, nouns): ...

@cli.group()
def lesson(): ...

@lesson.command("next")
@click.option("--theme")
def lesson_next(theme): ...
```

Usage:
```
python generate_lesson.py vocab list
python generate_lesson.py vocab create animals --nouns 15
python generate_lesson.py lesson next --theme food
python generate_lesson.py lesson render 3
python generate_lesson.py lesson export 3 --format anki
python generate_lesson.py curriculum show
```

**Pros:** Already installed; excellent help output; clean decorator registration; `CliRunner` makes testing easy; strong ecosystem  
**Cons:** Learning curve for existing `argparse` pattern; slight refactor needed

---

### Option 3: `typer` (NOT INSTALLED)

**What:** Built on click; uses Python type annotations to define CLI instead of decorators.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install typer` |
| **Subcommands** | `app = typer.Typer()` + `app.command()` |
| **Type coercion** | Automatic from Python type annotations (`int`, `Path`, `Optional[str]`) |
| **Help output** | Rich-integration available (`typer[all]`) |
| **Decorator style** | Annotation-driven |

Example:
```python
import typer
app = typer.Typer()
vocab_app = typer.Typer()
app.add_typer(vocab_app, name="vocab")

@vocab_app.command("create")
def vocab_create(theme: str, nouns: int = 12): ...
```

**Pros:** Cleanest syntax; type annotations double as CLI spec; Rich help pages with `typer[all]`  
**Cons:** Adds new dependency; `click` is already installed and equally capable; typer adds only syntactic sugar — YAGNI

---

### Option 4: `fire` (NOT INSTALLED)

**What:** Google's Python Fire — automatically generates CLI from functions/classes.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install fire` |
| **Subcommands** | Auto-generated from object methods |
| **Type coercion** | Best-effort from annotations |
| **Control** | Low — fire infers structure |

**Pros:** Zero boilerplate  
**Cons:** Too magical; poor control over argument names/types/help text; not appropriate for a user-facing tool

---

## Decision: `click` ✅

**Rationale:**
- Already installed — zero cost, zero new dependency
- First-class subcommand groups match the target structure exactly
- `CliRunner` enables proper CLI testing (replaces manual subprocess calls)
- Help output is clean and grouped — important for a tool that will have 10+ commands
- `argparse` subparsers achieve the same result but are more verbose and produce inferior help pages
- `typer` offers no real advantage over `click` for this project — YAGNI

**Migration plan:**
1. Replace `build_parser()` + `main()` in `generate_lesson.py` with click groups
2. Group structure: `vocab`, `lesson`, `curriculum`
3. Migrate existing `--list-themes`, `--create-vocab`, `--generate-vocab`, `--show-curriculum`
4. Add `lesson next`, `lesson render <id>`, `lesson export <id>` when pipeline is ready
5. Update `test_vocab_generator.py` / `test_generate_lesson` to use `CliRunner`

**Target command surface:**
```
jlesson vocab list
jlesson vocab create <theme> [--nouns N] [--verbs N] [--level beginner|intermediate]
jlesson vocab show <theme>
jlesson lesson next [--theme THEME] [--seed N]
jlesson lesson render <id>
jlesson lesson export <id> --format video|anki|text
jlesson curriculum show [--path FILE]
jlesson curriculum reset
```
