from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jlesson.curriculum import load_curriculum, save_curriculum
from jlesson.lesson_pipeline.pipeline_paths import resolve_lesson_dir
from jlesson.lesson_store import load_lesson_content, save_lesson_content
from jlesson.llm_cache import ask_llm_cached
from jlesson.llm_client import ask_llm_json_free
from jlesson.models import LessonContent, VocabFile
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


class ContextRuntime:
    """``RuntimeServices`` implementation backed by a live ``LessonContext``.

    Wraps an existing ``LessonContext`` so ``ActionStep`` subclasses can pass a
    ``RuntimeServices``-typed object to their ``StepAction`` without the action
    needing to know about the full pipeline context.

    ``call_llm``, curriculum storage, and lesson-content storage are wired.
    Retrieval and cache methods still raise ``NotImplementedError`` until the
    corresponding migrations land.
    """

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx

    # ── LLM ──────────────────────────────────────────────────────────────────

    def call_llm(self, prompt: str) -> dict[str, Any]:
        """Route to the cached or direct LLM path based on ``ctx.config.use_cache``."""
        return PipelineRuntime.ask_llm(self._ctx, prompt)

    # ── Retrieval / vector store ──────────────────────────────────────────────

    def query_retrieval(self, theme: str, **kwargs: Any) -> Any:
        raise NotImplementedError("query_retrieval not yet migrated to ContextRuntime")

    def update_retrieval(self, theme: str, items: list[Any]) -> None:
        raise NotImplementedError("update_retrieval not yet migrated to ContextRuntime")

    # ── Lesson content storage ────────────────────────────────────────────────

    def read_content(self, lesson_id: int) -> dict[str, Any]:
        lesson_dir = resolve_lesson_dir(self._ctx.config, lesson_id)
        content = load_lesson_content(lesson_id, lesson_dir)
        return content.model_dump(mode="json", exclude_none=True)

    def write_content(self, lesson_id: int, data: dict[str, Any]) -> Path:
        lesson_dir = resolve_lesson_dir(self._ctx.config, lesson_id)
        content = LessonContent.model_validate(data)
        return save_lesson_content(content, lesson_dir)

    # ── Curriculum storage ────────────────────────────────────────────────────

    def read_curriculum(self) -> Any:
        return load_curriculum(self._ctx.config.curriculum_path)

    def write_curriculum(self, data: Any) -> None:
        save_curriculum(data, self._ctx.config.curriculum_path)

    # ── LLM response cache ────────────────────────────────────────────────────

    def query_cache(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError("query_cache not yet migrated to ContextRuntime")

    def update_cache(self, key: str, value: dict[str, Any]) -> None:
        raise NotImplementedError("update_cache not yet migrated to ContextRuntime")
