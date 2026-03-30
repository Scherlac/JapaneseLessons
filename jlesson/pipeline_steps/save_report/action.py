from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jlesson.lesson_report import ReportBuilder, save_report

from ..pipeline_core import ActionConfig, RenderedVideoArtifact, ReportArtifact, StepAction


@dataclass(kw_only=True)
class SaveReportRequest(RenderedVideoArtifact):
    """Composite sink request preserving the rendered-video artifact boundary."""

    report: ReportBuilder
    report_path: Path
    summary_markdown: str


class SaveReportAction(StepAction[SaveReportRequest, ReportArtifact]):
    """Finalize report sections and persist the markdown report."""

    def run(self, config: ActionConfig, chunk: SaveReportRequest) -> ReportArtifact:
        chunk.report.add("summary", chunk.summary_markdown)
        report = chunk.report.render()
        saved_path = save_report(report, chunk.report_path)
        return ReportArtifact(report_path=saved_path)