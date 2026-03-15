"""
File-based LLM response cache for development use.

Maps sha256(prompt) → JSON response stored in output/.cache/<hash>.json.
Re-running the pipeline with the same prompts skips all LLM calls, reducing
a ~60s lesson pipeline run to under 1s during iterative development.

Usage:
    from jlesson.llm_cache import ask_llm_cached

    result = ask_llm_cached("Your prompt text...")

Cache controls:
    - Default cache dir: output/.cache/ (relative to project root)
    - Override via LLM_CACHE_DIR env var
    - Clear with: from jlesson.llm_cache import clear_cache; clear_cache()
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .llm_client import ask_llm_json_free

_DEFAULT_CACHE_DIR = Path(__file__).parent.parent / "output" / ".cache"


def _resolve_cache_dir(cache_dir: Path | None) -> Path:
    if cache_dir is not None:
        return Path(cache_dir)
    env = os.getenv("LLM_CACHE_DIR")
    if env:
        return Path(env)
    return _DEFAULT_CACHE_DIR


def _cache_path(prompt: str, cache_dir: Path) -> Path:
    key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.json"


def ask_llm_cached(
    prompt: str,
    *,
    cache_dir: Path | None = None,
) -> dict:
    """Return a cached LLM response if one exists; otherwise call the LLM and cache the result.

    Args:
        prompt:    The exact prompt string sent to the LLM.
        cache_dir: Override the cache directory (default: output/.cache/).

    Returns:
        Parsed JSON dict from the LLM (or cache).
    """
    resolved = _resolve_cache_dir(cache_dir)
    path = _cache_path(prompt, resolved)

    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    result = ask_llm_json_free(prompt)
    resolved.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def clear_cache(cache_dir: Path | None = None) -> int:
    """Delete all cached response files.

    Returns:
        Number of files deleted.
    """
    resolved = _resolve_cache_dir(cache_dir)
    if not resolved.exists():
        return 0
    deleted = 0
    for f in resolved.glob("*.json"):
        f.unlink()
        deleted += 1
    return deleted


def cache_size(cache_dir: Path | None = None) -> int:
    """Return the number of cached entries."""
    resolved = _resolve_cache_dir(cache_dir)
    if not resolved.exists():
        return 0
    return sum(1 for _ in resolved.glob("*.json"))
