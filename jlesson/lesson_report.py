"""
Markdown lesson report builder.

Provides ReportBuilder — an accumulator that pipeline steps use to
contribute report sections during execution.  The final step calls
render() to produce the complete Markdown string.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jlesson.llm_cache import LlmCacheTrace


@dataclass
class StepBudget:
    """Aggregated per-step execution and LLM usage metrics."""

    duration_s: float = 0.0
    llm_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ReportBuilder:
    """Accumulates Markdown report content across pipeline steps.

    Steps call add() to append markdown blocks to named sections.
    render() outputs all sections in a fixed display order, followed
    by auto-generated artifacts and timetable sections.
    """

    SECTION_ORDER = (
        "header",
        "retrieval",
        "narrative",
        "vocabulary",
        "noun_practice",
        "verb_practice",
        "grammar_practice",
        "review_notes",
        "render_details",
        "summary",
    )

    def __init__(self) -> None:
        self._sections: dict[str, list[str]] = {}
        self._step_times: dict[str, float] = {}
        self._step_budgets: dict[str, StepBudget] = {}
        self._artifacts: dict[str, Path] = {}

    def add(self, section: str, markdown: str) -> None:
        """Append a markdown block to *section*."""
        self._sections.setdefault(section, []).append(markdown)

    def record_time(self, step_name: str, elapsed: float) -> None:
        """Record a pipeline step's execution time."""
        self._step_times[step_name] = elapsed
        self._step_budgets.setdefault(step_name, StepBudget()).duration_s = elapsed

    def record_llm_usage(self, step_name: str, traces: list[LlmCacheTrace]) -> None:
        """Aggregate step-level LLM usage and cache metrics."""
        budget = self._step_budgets.setdefault(step_name, StepBudget())
        budget.llm_calls = len(traces)
        budget.cache_hits = sum(1 for trace in traces if trace.cache_hit)
        budget.cache_misses = sum(1 for trace in traces if not trace.cache_hit)
        budget.prompt_tokens = sum(trace.prompt_tokens for trace in traces)
        budget.completion_tokens = sum(trace.completion_tokens for trace in traces)
        budget.total_tokens = sum(trace.total_tokens for trace in traces)

    def add_artifact(self, name: str, path: Path) -> None:
        """Register a generated file or directory."""
        self._artifacts[name] = path

    def render(self) -> str:
        """Combine all sections into a Markdown report string."""
        parts: list[str] = []
        for section in self.SECTION_ORDER:
            for block in self._sections.get(section, []):
                parts.append(block)
        if self._artifacts:
            parts.append(self._render_artifacts())
        if self._step_times:
            parts.append(self._render_timetable())
        if self._step_budgets:
            parts.append(self._render_step_budget())
        text = "\n".join(parts)
        return text.rstrip("\n") + "\n"

    def _render_artifacts(self) -> str:
        lines = ["## Artifacts", ""]
        for name, path in self._artifacts.items():
            lines.append(f"- **{name}:** `{path}`")
        lines.append("")
        return "\n".join(lines)

    def _render_timetable(self) -> str:
        lines = [
            "## Pipeline Timetable",
            "",
            "| Stage | Duration |",
            "|-------|----------|",
        ]
        total = 0.0
        for name, elapsed in self._step_times.items():
            total += elapsed
            lines.append(f"| {name} | {elapsed:.1f}s |")
        lines.append(f"| **Total** | **{total:.1f}s** |")
        lines.append("")
        return "\n".join(lines)

    def _render_step_budget(self) -> str:
        lines = [
            "## Step Budget",
            "",
            "| Stage | Duration | LLM Calls | Cache Hits | Cache Misses | Prompt Tokens | Completion Tokens | Total Tokens |",
            "|-------|----------|-----------|------------|--------------|---------------|-------------------|--------------|",
        ]
        total = StepBudget()
        for name, budget in self._step_budgets.items():
            total.duration_s += budget.duration_s
            total.llm_calls += budget.llm_calls
            total.cache_hits += budget.cache_hits
            total.cache_misses += budget.cache_misses
            total.prompt_tokens += budget.prompt_tokens
            total.completion_tokens += budget.completion_tokens
            total.total_tokens += budget.total_tokens
            lines.append(
                f"| {name} | {budget.duration_s:.1f}s | {budget.llm_calls} | {budget.cache_hits} | {budget.cache_misses} | {budget.prompt_tokens} | {budget.completion_tokens} | {budget.total_tokens} |"
            )
        lines.append(
            f"| **Total** | **{total.duration_s:.1f}s** | **{total.llm_calls}** | **{total.cache_hits}** | **{total.cache_misses}** | **{total.prompt_tokens}** | **{total.completion_tokens}** | **{total.total_tokens}** |"
        )
        lines.append("")
        return "\n".join(lines)


def save_report(report: str, path: Path) -> Path:
    """Write the markdown report to a file. Returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path
