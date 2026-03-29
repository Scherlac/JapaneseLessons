from __future__ import annotations

from .pipeline_llm import ask_llm


class PipelineGadgets:
    """Compatibility shim — legacy patch point for ask_llm in older tests."""

    ask_llm = staticmethod(ask_llm)
