from __future__ import annotations

from typing import Any

from .pipeline_llm import ask_llm


class PipelineGadgets:
    """Compatibility shim — legacy patch point for ask_llm in older tests."""

    @staticmethod
    def ask_llm(ctx, prompt: str) -> dict[str, Any]:
        return ask_llm(ctx, prompt)
