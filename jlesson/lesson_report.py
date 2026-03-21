"""
Markdown lesson report builder.

Provides ReportBuilder — an accumulator that pipeline steps use to
contribute report sections during execution.  The final step calls
render() to produce the complete Markdown string.
"""

from __future__ import annotations

from pathlib import Path


class ReportBuilder:
    """Accumulates Markdown report content across pipeline steps.

    Steps call add() to append markdown blocks to named sections.
    render() outputs all sections in a fixed display order, followed
    by auto-generated artifacts and timetable sections.
    """

    SECTION_ORDER = (
        "header",
        "retrieval",
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
        self._artifacts: dict[str, Path] = {}

    def add(self, section: str, markdown: str) -> None:
        """Append a markdown block to *section*."""
        self._sections.setdefault(section, []).append(markdown)

    def record_time(self, step_name: str, elapsed: float) -> None:
        """Record a pipeline step's execution time."""
        self._step_times[step_name] = elapsed

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


def save_report(report: str, path: Path) -> Path:
    """Write the markdown report to a file. Returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path
