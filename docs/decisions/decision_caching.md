# Decision: LLM Response Caching

**Status:** Decided — file-based prompt cache (custom, no dependency)  
**Date:** 2026-03-15  
**Context:** Each lesson pipeline run makes 4-6 LLM calls (grammar select ~12s, sentence
generate ~21s, noun practice ~11s, verb practice ~est. 12s, content validate ~2s = ~60s total
LLM time). During development, re-running the pipeline repeatedly for testing wastes time and
produces redundant LLM calls for identical prompts. A prompt→response cache would make
pipeline iteration fast without any code changes to callers.

---

## What to Cache

| Call | Prompt size | Response size | Deterministic? |
|------|-------------|---------------|---------------|
| Grammar select | ~400 tokens | ~50 tokens | No — LLM may vary |
| Sentence generate | ~600 tokens | ~800 tokens | No |
| Noun practice | ~300 tokens | ~600 tokens | No |
| Verb practice | ~300 tokens | ~600 tokens | No |
| Content validate | ~1000 tokens | ~200 tokens | No |
| Vocab generate | ~300 tokens | ~2000 tokens | No |

The LLM responses are not strictly deterministic (temperature > 0), but for the same prompt
the responses are semantically stable. Caching makes development iteration fast; production
runs can bypass the cache.

---

## Cache Key Strategy

`sha256(prompt_text)` → 64-char hex string → used as filename.

This is safe because:
- The prompt contains the full context (vocab list, grammar specs, lesson number)
- If any input changes, the sha256 changes → cache miss → fresh LLM call
- Temperature and model are not context-dependent for development use

Optional: include model name in the key — `sha256(model + "|" + prompt)` — ensures cache
is invalidated when switching models.

---

## Options

### Option 1: Custom file-based JSON cache

**What:** A utility function wrapping `ask_llm_json_free()`. On call:
1. Compute `sha256(prompt)`
2. Check `output/.cache/<hash>.json` — return parsed JSON if it exists
3. Otherwise call the LLM, write response to cache file, return response

```python
import hashlib, json
from pathlib import Path

CACHE_DIR = Path("output/.cache")

def _cache_path(prompt: str) -> Path:
    key = hashlib.sha256(prompt.encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"

def ask_llm_cached(prompt: str) -> dict:
    path = _cache_path(prompt)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    result = ask_llm_json_free(prompt)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib `hashlib`, `json`, `pathlib` |
| **Persistence** | Between runs (disk) |
| **TTL** | None — manual cache bust by deleting `output/.cache/` |
| **Inspectability** | Each cache entry is a readable `.json` file |
| **Thread safety** | Not guaranteed — acceptable for single-process CLI |
| **Enable/disable** | `--no-cache` flag or `CACHE_LLM=false` env var |
| **Cache size** | ~10-50KB per entry × ~100 dev iterations = ~5MB max |

**Pros:** Zero dependency; fully inspectable; easy to bust; consistent with JSON-everywhere pattern  
**Cons:** No TTL; no size limits; no thread safety (not needed)

---

### Option 2: `shelve` (stdlib)

**What:** `shelve.open("output/.llm_cache")` — key-value store, persistent between runs.

```python
import shelve
with shelve.open("output/.llm_cache") as cache:
    if prompt in cache:
        return cache[prompt]
    result = ask_llm_json_free(prompt)
    cache[prompt] = result
    return result
```

| Aspect | Detail |
|--------|--------|
| **Install** | None — stdlib |
| **Inspectability** | Binary — cannot read directly |
| **Key** | Raw prompt string (large keys) |

**Pros:** Simpler code than Option 1  
**Cons:** Not inspectable; platform-dependent backend; prompt strings as keys → large dbm keys; JSON files are strictly better for traceability

---

### Option 3: `diskcache` (NOT INSTALLED)

**What:** Production-grade disk cache with TTL, size limits, thread/process safety.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install diskcache` (~200KB) |
| **TTL** | Yes — `cache.set(key, val, expire=3600)` |
| **Size limits** | Yes — eviction policies |
| **Thread safety** | Yes |
| **Inspectability** | SQLite-backed — readable with sqlite3 CLI |

```python
import diskcache
cache = diskcache.Cache("output/.cache")
result = cache.get(prompt) or ask_and_cache(prompt)
```

**Pros:** Production-grade; TTL; size management; thread-safe  
**Cons:** New dependency; features (TTL, eviction, thread-safety) are irrelevant for a single-process dev tool; adds complexity we don't need (YAGNI)

---

### Option 4: `joblib.Memory` (NOT INSTALLED)

**What:** `joblib` memoization decorator — wraps functions, caches call results by arguments.

```python
from joblib import Memory
memory = Memory("output/.cache", verbose=0)

@memory.cache
def ask_llm_cached(prompt): ...
```

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install joblib` (already present in many conda envs — check) |
| **Cache key** | Hash of function arguments (automatic) |
| **Inspectability** | Pickle files — not human-readable |

**Pros:** Decorator-based; no key management  
**Cons:** Pickle-based → not inspectable; joblib designed for numpy/array caching; overkill; requires install

---

### Option 5: `functools.lru_cache` (stdlib)

**What:** In-memory memoization. Cleared on process exit.

**Verdict:** Not useful — we need persistence between pipeline runs (each run is a new process).

---

## Decision: Custom file-based JSON cache (Option 1) ✅

**Rationale:**
- Zero dependency — consistent with stdlib-first principle
- JSON files align with the project's existing storage pattern (all data is human-readable JSON)
- Every cached response is inspectable — valuable for debugging LLM quality issues during development
- Cache bust is trivially `rm -rf output/.cache/` or `del output\.cache`
- The problems that `diskcache` solves (TTL, eviction, thread safety) do not exist in this use case
- `shelve` and `joblib` produce opaque binary files — unacceptable for a debugging-heavy dev tool

**Implementation (to add to `llm_client.py` or a new `llm_cache.py`):**
- `ask_llm_cached(prompt, cache_dir, bypass=False) -> dict`
- Cache key: `sha256(model + "|" + prompt)` — model-specific
- Cache location: `output/.cache/` (gitignored)
- Enable/disable: `LLM_CACHE=true/false` env var (default `false` — opt-in for dev)
- Cache is **development-only** — production runs should use `--no-cache` or `LLM_CACHE=false`

**gitignore entry:** `output/.cache/` should be added to `.gitignore`
