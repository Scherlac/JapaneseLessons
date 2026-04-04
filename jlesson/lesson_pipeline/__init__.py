"""
Lesson generation pipeline.

Orchestrates the full lesson workflow through fourteen sequential steps:

    step 1   narrative_generator     — create block-by-block story progression
    step 2   extract_narrative_vocab — extract block-level vocab targets
    step 3   canonical_vocab_select  — choose canonical planning vocab
    step 4   select_vocab            — pick fresh nouns/verbs from the vocab file
    step 5   lesson_planner          — LLM: two-pass lesson outline (grammar + pacing)
    step 6   narrative_grammar       — LLM: produce block-aware practice sentences
    step 7   review_sentences        — LLM: rate naturalness, rewrite awkward sentences
    step 8   vocab_enhancement       — LLM: enrich nouns and verbs together
    step 9   register_lesson         — add+complete the lesson in curriculum.json
    step 10  persist_content         — save LessonContent to output/<id>/content.json
    step 11  compile_assets          — render card images + TTS audio per item (Stage 2)
    step 12  compile_touches         — profile-driven touch sequencing (Stage 3)
    step 13  render_video            — assemble MP4 from touch sequence
    step 14  save_report             — finalize and save Markdown lesson report

Each step is a PipelineStep subclass with an execute(ctx) method,
making them individually testable and easy to extend.

Usage:
    from jlesson.lesson_pipeline import LessonConfig, run_pipeline
    config = LessonConfig(
        theme="food",
        curriculum_path=Path("curriculum/curriculum.json"),
    )
    ctx = run_pipeline(config)
    print(f"Video: {ctx.video_path}")
    print(f"Content: {ctx.content_path}")
"""

from __future__ import annotations

from pathlib import Path

from jlesson.curriculum import load_curriculum
from jlesson.pipeline_steps import (
    CanonicalVocabSelectStep,
    CompileAssetsStep,
    CompileTouchesStep,
    ExtractNarrativeVocabStep,
    GrammarSelectStep,  # kept for backward-compatible re-export
    LessonConfig,
    LessonContext,
    CanonicalPlannerStep,
    NarrativeGeneratorStep,
    NounPracticeStep,
    PersistContentStep,
    PipelineStep,
    RegisterLessonStep,
    RenderVideoStep,
    ReviewSentencesStep,
    SaveReportStep,
    SelectVocabStep,
    StepInfo,
    VocabEnhancementStep,
    VerbPracticeStep,
)
from jlesson.pipeline_steps.generate_sentences import NarrativeGrammarStep
from jlesson.runtime import PipelineRuntime


def _build_pipeline() -> list[PipelineStep]:
    return [
        NarrativeGeneratorStep(),
        ExtractNarrativeVocabStep(),
        CanonicalVocabSelectStep(),
        SelectVocabStep(),
        CanonicalPlannerStep(),  # two-pass lesson outline (replaces GrammarSelectStep)
        # GrammarSelectStep(),
        NarrativeGrammarStep(),
        ReviewSentencesStep(),
        VocabEnhancementStep(),
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
    "CompileAssetsStep",
    "CompileTouchesStep",
    "ExtractNarrativeVocabStep",
    "GenerateNarrativeVocabStep",
    "NarrativeGrammarStep",
    "GrammarSelectStep",
    "LessonConfig",
    "LessonContext",
    "NarrativeGeneratorStep",
    "NarrativeGrammarStep",
    "NounPracticeStep",
    "PersistContentStep",
    "PIPELINE",
    "PipelineRuntime",
    "PipelineStep",
    "RegisterLessonStep",
    "RenderVideoStep",
    "ReviewSentencesStep",
    "SaveReportStep",
    "SelectVocabStep",
    "StepInfo",
    "VocabEnhancementStep",
    "VerbPracticeStep",
    "load_curriculum",
    "restore_context_from_checkpoint",
    "run_pipeline",
]
