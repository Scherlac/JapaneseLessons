"""
Lesson generation pipeline.

Orchestrates the full lesson workflow through fifteen sequential steps:

    step 1   retrieve_material  — optional retrieval with safe fallback
    step 2   narrative_generator     — create block-by-block story progression
    step 3   extract_narrative_vocab — extract block-level vocab targets
    step 4   generate_narrative_vocab — LLM: generate Japanese vocab from narrative terms
    step 5   select_vocab            — pick fresh nouns/verbs from the vocab file
    step 6   grammar_select          — LLM: pick grammar points for this lesson
    step 7   narrative_grammar       — LLM: produce block-aware practice sentences
    step 8   review_sentences        — LLM: rate naturalness, rewrite awkward sentences
    step 9   noun_practice           — LLM: enrich nouns with examples + memory tips
    step 10  verb_practice           — LLM: enrich verbs with conjugations + memory tips
    step 11  register_lesson         — add+complete the lesson in curriculum.json
    step 12  persist_content         — save LessonContent to output/<id>/content.json
    step 13  compile_assets          — render card images + TTS audio per item (Stage 2)
    step 14  compile_touches         — profile-driven touch sequencing (Stage 3)
    step 15  render_video            — assemble MP4 from touch sequence
    step 16  save_report             — finalize and save Markdown lesson report

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
    CompileAssetsStep,
    CompileTouchesStep,
    ExtractNarrativeVocabStep,
    GenerateNarrativeVocabStep,
    GrammarSelectStep,
    LessonConfig,
    LessonContext,
    NarrativeGeneratorStep,
    NounPracticeStep,
    PersistContentStep,
    PipelineStep,
    RegisterLessonStep,
    RenderVideoStep,
    RetrieveLessonMaterialStep,
    ReviewSentencesStep,
    SaveReportStep,
    SelectVocabStep,
    StepInfo,
    VerbPracticeStep,
)
from jlesson.pipeline_steps.generate_sentences import GenerateSentencesStep, NarrativeGrammarStep
from jlesson.runtime import PipelineGadgets, PipelineRuntime


def _build_pipeline() -> list[PipelineStep]:
    return [
        RetrieveLessonMaterialStep(),
        NarrativeGeneratorStep(),
        ExtractNarrativeVocabStep(),
        GenerateNarrativeVocabStep(),
        SelectVocabStep(),
        GrammarSelectStep(),
        NarrativeGrammarStep(),
        ReviewSentencesStep(),
        NounPracticeStep(),
        VerbPracticeStep(),
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


def render_existing_lesson(
    lesson_id: int,
    output_dir: Path | None = None,
    profile: str = "passive_video",
    language: str = "eng-jap",
    verbose: bool = True,
) -> Path:
    """Render MP4 for an already-generated lesson content file."""
    from .pipeline_existing_lesson import render_existing_lesson as _render_existing_lesson_impl

    return _render_existing_lesson_impl(
        lesson_id=lesson_id,
        output_dir=output_dir,
        profile=profile,
        language=language,
        verbose=verbose,
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
    "GenerateSentencesStep",
    "GrammarSelectStep",
    "LessonConfig",
    "LessonContext",
    "NarrativeGeneratorStep",
    "NarrativeGrammarStep",
    "NounPracticeStep",
    "PersistContentStep",
    "PIPELINE",
    "PipelineGadgets",
    "PipelineRuntime",
    "PipelineStep",
    "RegisterLessonStep",
    "RenderVideoStep",
    "RetrieveLessonMaterialStep",
    "ReviewSentencesStep",
    "SaveReportStep",
    "SelectVocabStep",
    "StepInfo",
    "VerbPracticeStep",
    "load_curriculum",
    "render_existing_lesson",
    "run_pipeline",
]
