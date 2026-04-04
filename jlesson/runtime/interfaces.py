"""Runtime services interface used by pipeline step actions.

``RuntimeServices`` is a structural protocol — any object that implements the
required methods satisfies it without explicit inheritance.  Step actions
declare a dependency on ``RuntimeServices`` rather than on the concrete
``PipelineRuntime`` or ``LessonContext``, which keeps individual actions
testable without a live pipeline context.

Concrete implementations
------------------------
``ContextRuntime`` (runtime._base)
    Wraps a live ``LessonContext``; used during normal pipeline execution.

Future implementations
----------------------
Mock / in-memory runtimes for unit testing action logic in isolation.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from jlesson.curriculum import CurriculumData
    from jlesson.retrieval import RetrievalResult


@runtime_checkable
class RuntimeServices(Protocol):
    """Thin facade for all I/O-bound operations available to step actions.

    Responsibilities are grouped into four areas:

    LLM
        Send prompts, receive parsed JSON responses.
    Retrieval / vector store
        Query and update the semantic retrieval index.
    Storage
        Read and write persisted lesson content.
    Cache
        Query and update the LLM response cache.
    """

    # ── LLM ──────────────────────────────────────────────────────────────────

    def call_llm(self, prompt: str) -> dict[str, Any]:
        """Send *prompt* to the LLM; return the parsed JSON response dict."""
        ...

    # ── Retrieval / vector store ──────────────────────────────────────────────

    def query_retrieval(self, theme: str, **kwargs: Any) -> RetrievalResult:
        """Query the retrieval store for previously generated material."""
        ...

    def update_retrieval(self, theme: str, items: list[Any]) -> None:
        """Index *items* into the retrieval store under *theme*."""
        ...


    # ── Lesson content storage ────────────────────────────────────────────────

    def read_content(self, lesson_id: int) -> dict[str, Any]:
        """Load a persisted lesson content JSON by *lesson_id*."""
        ...

    def write_content(self, lesson_id: int, data: dict[str, Any]) -> Path:
        """Persist lesson content *data* for *lesson_id* and return the file path."""
        ...

    # ── Curriculum storage ────────────────────────────────────────────────────

    def read_curriculum(self) -> CurriculumData:
        """Load current curriculum state from disk."""
        ...

    def write_curriculum(self, data: CurriculumData) -> None:
        """Persist updated curriculum state to disk."""
        ...

    # ── LLM response cache ────────────────────────────────────────────────────

    def query_cache(self, key: str) -> dict[str, Any] | None:
        """Return a cached LLM response for *key*, or ``None`` on cache miss."""
        ...

    def update_cache(self, key: str, value: dict[str, Any]) -> None:
        """Write *value* into the LLM response cache under *key*."""
        ...
