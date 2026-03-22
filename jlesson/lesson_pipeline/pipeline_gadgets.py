from __future__ import annotations

from .pipeline_llm import ask_llm
from .pipeline_vocab import load_vocab


class PipelineGadgets:
    """Compatibility shim for tests and legacy patch points."""

    ask_llm = staticmethod(ask_llm)
    load_vocab = staticmethod(load_vocab)
