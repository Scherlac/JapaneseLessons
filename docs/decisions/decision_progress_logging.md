# Decision: Progress Display + Logging

**Status:** Decided — `rich` for progress and console output; stdlib `logging` for structured logs  
**Date:** 2026-03-15  
**Context:** The pipeline makes 4-6 LLM calls (~60s total) plus TTS generation (rate-limited,
~30s for 10 items) plus video render (~10s). Currently all feedback is `print()` statements.
A developer or end-user running `lesson next` has no visibility into which stage is running,
how long it has been, or whether the process is stuck.

---

## Current State

```python
print(f"\n{'='*60}")
print(f"  Lesson 1: Food Theme")
print(f"{'='*60}")
print("  [grammar_select] Calling LLM...")
# ... 60 seconds later ...
print("  ✅ grammar select done")
```

Problems:
- No timing information per stage
- No visual differentiation between stages, warnings, errors
- No progress bar for iterative operations (TTS batch generation)
- No log level control — debug print and user-facing print are indistinguishable
- Pipeline failure looks identical to silence

---

## Options

### Option 1: stdlib `logging` + `print()`

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Grammar select: calling LLM...")
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib |
| **Log levels** | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| **Formatting** | Custom formatters; no colour by default |
| **Progress bars** | None |
| **Structured logs** | With `logging.handlers` or JSON formatter |

**Pros:** Zero dependency; standard Python  
**Cons:** Plain text; no progress bars; no colour; poor UX for an interactive CLI tool

---

### Option 2: `rich` (INSTALLED — 14.2.0)

`rich` is already installed and provides:
- `rich.Console` — coloured, styled output with markup `[green]text[/green]`
- `rich.progress.Progress` — live multi-bar progress tracker
- `rich.Panel` — bordered boxes for section headers
- `rich.Table` — terminal tables (useful for summary output)
- `rich.Spinner` — animated spinner for indeterminate waits (LLM calls)
- `rich.Traceback` — pretty exception formatting

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    TimeElapsedColumn(),
    console=console,
) as progress:
    task = progress.add_task("Grammar select (LLM)...", total=None)
    result = ask_llm_json_free(grammar_select_prompt)
    progress.update(task, description="[green]Grammar select ✓", completed=1, total=1)
```

| Aspect | Detail |
|--------|--------|
| **Install** | Already installed |
| **Progress bars** | Yes — multi-bar, live-updating, with elapsed time |
| **Spinners** | Yes — for indeterminate LLM calls |
| **Colour/style** | Full — markup `[bold green]`, `[yellow]`, etc. |
| **Tables** | Yes — lesson summary, curriculum display |
| **Panels** | Yes — section headers for pipeline stages |
| **Log integration** | `RichHandler` for stdlib `logging` — coloured log output |

**Pros:** Already installed; dramatically improves pipeline UX; `TimeElapsedColumn` shows wall time per stage; `RichHandler` replaces bare print  
**Cons:** Adds rich as a project-level import (not just a dev dependency) — accepted given it's already installed

---

### Option 3: `loguru` (NOT INSTALLED)

**What:** Alternative logging library with coloured output and simpler API than stdlib `logging`.

```python
from loguru import logger
logger.info("Grammar select: calling LLM...")
logger.success("Grammar select: done in {:.1f}s", elapsed)
```

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install loguru` |
| **Colour** | Yes — built-in coloured output |
| **Progress bars** | No — logging library only |
| **Integration** | Not `rich` — separate ecosystem |

**Pros:** Elegant API; coloured structured logs  
**Cons:** New dependency; no progress bars; `rich` is already installed and covers the same use cases plus progress bars

---

### Option 4: `tqdm` (CHECK INSTALLED)

**What:** Minimal progress bar library.

```python
from tqdm import tqdm
for item in tqdm(audio_items, desc="Generating TTS audio"):
    await tts_engine.generate_audio(item.text, item.path)
```

`tqdm` may already be present (many ML/data environments include it), but it is a narrower
tool — only progress bars, no styling, no spinners, no tables. `rich` is a strict superset.

---

## Decision: `rich` (primary console output) + stdlib `logging` via `RichHandler` ✅

**Rationale:**
- `rich` is already installed — zero cost
- The pipeline has exactly the UX problem rich solves: long-running LLM + TTS stages with no feedback
- `TimeElapsedColumn` on each pipeline stage gives direct visibility into LLM latency
- `RichHandler` replaces all existing bare `print()` statements with level-controlled, coloured output
- `loguru` adds nothing that `rich` + stdlib `logging` doesn't provide — YAGNI, and requires install
- Existing `llm_client.py` already uses stdlib `logging` — `RichHandler` integrates without rewrites

**Implementation plan:**

1. Add to `lesson_pipeline.py`:
   ```python
   from rich.console import Console
   from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn
   console = Console()
   ```

2. Wrap each LLM call in a `Progress` spinner with `TimeElapsedColumn`

3. Use `Progress` with percentage for TTS batch generation (known count):
   ```python
   with Progress() as p:
       task = p.add_task("TTS audio", total=len(items))
       for item in items:
           await tts.generate_audio(...)
           p.advance(task)
   ```

4. Use `rich.Panel` for lesson start/end banners

5. Replace `logging.basicConfig()` in `llm_client.py` with `RichHandler`:
   ```python
   from rich.logging import RichHandler
   logging.basicConfig(handlers=[RichHandler()], level=logging.INFO)
   ```

6. Keep `console = Console()` as module-level singleton in `lesson_pipeline.py` — 
   **do not** add rich imports to domain modules (`curriculum.py`, `prompt_template.py`)

**Rule:** rich output is presentation layer only — it belongs in the CLI and pipeline orchestrator,
not in domain or data modules.
