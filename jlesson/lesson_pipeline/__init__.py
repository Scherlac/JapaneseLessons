"""Lesson generation pipeline.

Orchestrates the currently active lesson workflow through ten sequential steps:

    step 1   narrative_generator  — create block-by-block story progression
    step 2   canonical_planner    — LLM: two-pass lesson outline (grammar + pacing)
    step 3   lesson_planner       — LLM: resolve canonical items into target language
    step 4   review_sentences     — LLM: rate naturalness, rewrite awkward sentences
    step 5   register_lesson      — add+complete the lesson in curriculum.json
    step 6   compile_assets       — render card images + TTS audio per item (Stage 2)
    step 7   compile_touches      — profile-driven touch sequencing (Stage 3)
    step 8   render_video         — assemble MP4 from touch sequence
    step 9   save_report          — finalize and save Markdown lesson report
"""

from __future__ import annotations

from jlesson.curriculum import load_curriculum
from jlesson.pipeline_steps import (
    CanonicalPlannerStep,
    CompileAssetsStep,
    CompileTouchesStep,
    LessonConfig,
    LessonContext,
    LessonPlannerStep,
    NarrativeGeneratorStep,
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
        LessonPlannerStep(),
        ReviewSentencesStep(),
        RegisterLessonStep(),
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
    "LessonPlannerStep",
    "NarrativeGeneratorStep",
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
