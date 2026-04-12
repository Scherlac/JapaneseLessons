from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jlesson.curriculum import load_curriculum, save_curriculum
from jlesson.llm_cache import ask_llm_cached, bind_trace_to_step, build_uncached_llm_trace
from jlesson.llm_client import ask_llm_json_free
from jlesson.retrieval import get_retrieval_service
from jlesson.vocab_generator import generate_vocab, VOCAB_DIR

_DEFAULT_VOCAB_DIR = VOCAB_DIR


def _record_step_llm_trace(ctx: Any, trace) -> None:
    call_index = len(ctx.llm_traces) + 1
    step_info = getattr(ctx, "step_info", None)
    ctx.llm_traces.append(
        bind_trace_to_step(
            trace,
            call_index=call_index,
            step_name=step_info.name if step_info is not None else None,
            step_index=step_info.index if step_info is not None else None,
        )
    )


def _resolve_retrieval_store_path(config: Any) -> Path:
    if config.retrieval_store_path is not None:
        return Path(config.retrieval_store_path)
    return Path(__file__).parent.parent / "output" / "retrieval" / "material_index.json"


class PipelineRuntime:
    """Shared runtime services used by pipeline steps.

    This centralizes recurring operational concerns: LLM routing, vocab file
    loading (with LLM generation fallback), and lightweight JSON persistence.
    """

    @staticmethod
    def ask_llm(ctx, prompt: str, effort: str | None = None) -> dict[str, Any]:
        """Invoke the configured LLM path (cached or direct)."""
        if ctx.config.use_cache:
            return ask_llm_cached(
                prompt,
                effort=effort,
                trace_recorder=lambda trace: _record_step_llm_trace(ctx, trace),
            )
        result = ask_llm_json_free(prompt, effort=effort)
        _record_step_llm_trace(ctx, build_uncached_llm_trace(prompt, result, effort=effort))
        return result

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

    def call_llm(self, prompt: str, effort: str | None = None) -> dict[str, Any]:
        """Route to the cached or direct LLM path based on ``ctx.config.use_cache``."""
        return PipelineRuntime.ask_llm(self._ctx, prompt, effort=effort)

    # ── Retrieval / vector store ──────────────────────────────────────────────

    def query_retrieval(self, theme: str, **kwargs: Any) -> Any:
        service = get_retrieval_service(
            self._ctx.config.retrieval_enabled,
            _resolve_retrieval_store_path(self._ctx.config),
            backend=self._ctx.config.retrieval_backend,
            embedding_model=self._ctx.config.retrieval_embedding_model,
        )
        return service.search(theme, **kwargs)

    def update_retrieval(self, theme: str, items: list[Any]) -> None:
        raise NotImplementedError("update_retrieval not yet migrated to ContextRuntime")

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
