"""Lesson generation pipeline.

Orchestrates the currently active lesson workflow through nine sequential steps:

    step 1  narrative_generator  — create block-by-block story progression
    step 2  lesson_planner       — LLM: two-pass lesson outline (grammar + pacing)
    step 3  review_sentences     — LLM: rate naturalness, rewrite awkward sentences
    step 4  register_lesson      — add+complete the lesson in curriculum.json
    step 5  persist_content      — save LessonContent to output/<id>/content.json
    step 6  compile_assets       — render card images + TTS audio per item (Stage 2)
    step 7  compile_touches      — profile-driven touch sequencing (Stage 3)
    step 8  render_video         — assemble MP4 from touch sequence
    step 9  save_report          — finalize and save Markdown lesson report
"""

from __future__ import annotations

from jlesson.curriculum import load_curriculum
from jlesson.pipeline_steps import (
    CanonicalPlannerStep,
    CompileAssetsStep,
    CompileTouchesStep,
    LessonConfig,
    LessonContext,
    NarrativeGeneratorStep,
    PersistContentStep,
    PipelineStep,
    RegisterLessonStep,
    RenderVideoStep,
    ReviewSentencesStep,
    SaveReportStep,
    StepInfo,
)
from jlesson.runtime import PipelineRuntime


def _build_pipeline() -> list[PipelineStep]:
    return [
        NarrativeGeneratorStep(),
        CanonicalPlannerStep(),
        ReviewSentencesStep(),
        RegisterLessonStep(),
        PersistContentStep(),
        CompileAssetsStep(),
        CompileTouchesStep(),
        RenderVideoStep(),
        SaveReportStep(),
    ]
        

def run_pipeline(config: LessonConfig) -> LessonContext:
    """Run the full lesson generation pipeline."""
    from .pipeline_orchestrator import run_pipeline as _run_pipeline_impl

    return _run_pipeline_impl(
        config,
        pipeline=_build_pipeline(),
        load_curriculum_fn=load_curriculum,
    )


def restore_context_from_checkpoint(
    config: LessonConfig,
    *,
    wire_assets: bool = True,
) -> "LessonContext":
    """Load a saved lesson checkpoint and return a renderable LessonContext."""
    from .pipeline_orchestrator import restore_context_from_checkpoint as _restore_impl

    return _restore_impl(
        config,
        load_curriculum_fn=load_curriculum,
        wire_assets=wire_assets,
    )


def __getattr__(name: str):
    if name == "PIPELINE":
        return _build_pipeline()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
	"CanonicalPlannerStep",
    "CompileAssetsStep",
    "CompileTouchesStep",
    "LessonConfig",
    "LessonContext",
    "NarrativeGeneratorStep",
    "PersistContentStep",
    "PIPELINE",
    "PipelineRuntime",
    "PipelineStep",
    "RegisterLessonStep",
    "RenderVideoStep",
    "ReviewSentencesStep",
    "SaveReportStep",
    "StepInfo",
    "load_curriculum",
    "restore_context_from_checkpoint",
    "run_pipeline",
]
