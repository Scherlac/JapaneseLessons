from __future__ import annotations

from typing import Any

from jlesson.llm_cache import ask_llm_cached
from jlesson.llm_client import ask_llm_json_free


def ask_llm(ctx, prompt: str) -> dict[str, Any]:
    """Route an LLM call through the cache or directly, based on config."""
    if ctx.config.use_cache:
        return ask_llm_cached(prompt)
    return ask_llm_json_free(prompt)
