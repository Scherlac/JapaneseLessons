from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jlesson.models import VocabFile
from .pipeline_llm import ask_llm
from .pipeline_vocab import load_vocab as _load_vocab_file


class PipelineRuntime:
    """Shared runtime services used by pipeline steps.

    This centralizes recurring operational concerns such as LLM calls,
    vocab file loading, and lightweight JSON persistence helpers.
    """

    @staticmethod
    def ask_llm(ctx, prompt: str) -> dict[str, Any]:
        """Invoke the configured LLM path (cached or direct)."""
        return ask_llm(ctx, prompt)

    @staticmethod
    def load_vocab(theme: str, vocab_dir: Path | None = None) -> VocabFile:
        """Load vocab JSON for *theme*, generating via LLM if the file is absent."""
        return _load_vocab_file(theme, vocab_dir)

    @staticmethod
    def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read JSON data from disk with a caller-provided default fallback."""
        file_path = Path(path)
        if not file_path.exists():
            return dict(default or {})
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return dict(default or {})

    @staticmethod
    def write_json(path: Path, payload: dict[str, Any]) -> None:
        """Write a JSON payload to disk, creating parent directories as needed."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
