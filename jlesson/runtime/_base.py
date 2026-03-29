from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jlesson.llm_cache import ask_llm_cached
from jlesson.llm_client import ask_llm_json_free
from jlesson.models import VocabFile
from jlesson.vocab_generator import generate_vocab, VOCAB_DIR

_DEFAULT_VOCAB_DIR = VOCAB_DIR


class PipelineRuntime:
    """Shared runtime services used by pipeline steps.

    This centralizes recurring operational concerns: LLM routing, vocab file
    loading (with LLM generation fallback), and lightweight JSON persistence.
    """

    @staticmethod
    def ask_llm(ctx, prompt: str) -> dict[str, Any]:
        """Invoke the configured LLM path (cached or direct)."""
        if ctx.config.use_cache:
            return ask_llm_cached(prompt)
        return ask_llm_json_free(prompt)

    @staticmethod
    def load_vocab(theme: str, vocab_dir: Path | None = None) -> VocabFile:
        """Load vocab JSON for *theme*, generating via LLM if the file is absent.

        File I/O is handled here (runtime concern).  When the file is missing,
        generation is delegated to ``vocab_generator.generate_vocab`` (domain
        concern) which validates, normalizes, and saves the result.
        """
        base_dir = Path(vocab_dir) if vocab_dir is not None else _DEFAULT_VOCAB_DIR
        path = base_dir / f"{theme}.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
        else:
            print(f"  [vocab] {theme}.json not found — generating via LLM...")
            raw = generate_vocab(
                theme=theme,
                num_nouns=12,
                num_verbs=10,
                output_dir=base_dir,
            )
        return VocabFile.model_validate(raw)

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
