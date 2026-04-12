"""
File-based LLM response cache for development use.

Maps sha256(prompt) → JSON response stored in output/.cache/<hash>.json.
Re-running the pipeline with the same prompts skips all LLM calls, reducing
a ~60s lesson pipeline run to under 1s during iterative development.

Usage:
    from jlesson.llm_cache import ask_llm_cached

    result = ask_llm_cached("Your prompt text...")

Cache controls:
    - Default cache dir: ~/.jlesson/cache/ (user home directory)
    - Override via LLM_CACHE_DIR env var
    - Clear with: from jlesson.llm_cache import clear_cache; clear_cache()
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from .llm_client import ask_llm_json_free

_DEFAULT_CACHE_DIR = Path.home() / ".jlesson" / "cache"


@dataclass(frozen=True)
class LlmCacheTrace:
    """Typed trace record for one LLM call tied to cache state."""

    prompt_hash: str
    response_hash: str
    cache_key: str | None
    cache_hit: bool
    prompt_file: str | None
    response_file: str | None
    effort: str | None = None
    call_index: int = 0
    step_name: str | None = None
    step_index: int | None = None


@dataclass(frozen=True)
class StepLlmCacheLog:
    """Serialized step-level wrapper for LLM trace records."""

    step: str
    calls: list[LlmCacheTrace]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(canonical)


def _resolve_cache_dir(cache_dir: Path | None) -> Path:
    if cache_dir is not None:
        return Path(cache_dir)
    env = os.getenv("LLM_CACHE_DIR")
    if env:
        return Path(env)
    return _DEFAULT_CACHE_DIR


def _cache_path(prompt: str, cache_dir: Path) -> Path:
    key = _sha256_text(prompt)
    return cache_dir / f"{key}.json"


def build_uncached_llm_trace(
    prompt: str,
    response: dict[str, Any],
    *,
    effort: str | None = None,
) -> LlmCacheTrace:
    return LlmCacheTrace(
        prompt_hash=_sha256_text(prompt),
        response_hash=_sha256_json(response),
        cache_key=None,
        cache_hit=False,
        prompt_file=None,
        response_file=None,
        effort=effort,
    )


def bind_trace_to_step(
    trace: LlmCacheTrace,
    *,
    call_index: int,
    step_name: str | None,
    step_index: int | None,
) -> LlmCacheTrace:
    return replace(
        trace,
        call_index=call_index,
        step_name=step_name,
        step_index=step_index,
    )


def build_llm_cache_trace(
    prompt: str,
    response: dict[str, Any],
    *,
    cache_path: Path,
    cache_hit: bool,
    effort: str | None = None,
) -> LlmCacheTrace:
    return LlmCacheTrace(
        prompt_hash=_sha256_text(prompt),
        response_hash=_sha256_json(response),
        cache_key=cache_path.stem,
        cache_hit=cache_hit,
        prompt_file=str(cache_path.with_suffix(".prompt.txt")),
        response_file=str(cache_path),
        effort=effort,
    )


def ask_llm_cached(
    prompt: str,
    *,
    cache_dir: Path | None = None,
    effort: str | None = None,
    trace_recorder: Callable[[LlmCacheTrace], None] | None = None,
) -> dict:
    """Return a cached LLM response if one exists; otherwise call the LLM and cache the result.

    Args:
        prompt:    The exact prompt string sent to the LLM.
        cache_dir: Override the cache directory (default: ~/.jlesson/cache/).

    Returns:
        Parsed JSON dict from the LLM (or cache).
    """
    resolved = _resolve_cache_dir(cache_dir)
    path = _cache_path(prompt, resolved)
    path_prompt = path.with_suffix(".prompt.txt")

    if path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
        if trace_recorder is not None:
            trace_recorder(
                build_llm_cache_trace(
                    prompt,
                    result,
                    cache_path=path,
                    cache_hit=True,
                    effort=effort,
                )
            )
        return result

    result = ask_llm_json_free(prompt, effort=effort)
    resolved.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    path_prompt.write_text(prompt, encoding="utf-8")
    if trace_recorder is not None:
        trace_recorder(
            build_llm_cache_trace(
                prompt,
                result,
                cache_path=path,
                cache_hit=False,
                effort=effort,
            )
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
