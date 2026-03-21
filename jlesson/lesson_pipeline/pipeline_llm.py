from __future__ import annotations

from jlesson.llm_client import ask_llm_json_free


def ask_llm(ctx, prompt: str) -> dict:
    """Route LLM calls through cache when enabled."""
    if ctx.config.use_cache:
        from jlesson.llm_cache import ask_llm_cached

        return ask_llm_cached(prompt)
    return ask_llm_json_free(prompt)