"""
Lesson generation pipeline.

Orchestrates the full lesson workflow through thirteen sequential steps:

    step 1   retrieve_material  — optional retrieval with safe fallback
    step 2   select_vocab       — pick fresh nouns/verbs from the vocab file
    step 3   grammar_select     — LLM: pick 1-2 grammar points for this lesson
    step 4   generate_sentences — LLM: produce practice sentences
    step 5   review_sentences   — LLM: rate naturalness, rewrite awkward sentences
    step 6   noun_practice      — LLM: enrich nouns with examples + memory tips
    step 7   verb_practice      — LLM: enrich verbs with conjugations + memory tips
    step 8   register_lesson    — add+complete the lesson in curriculum.json
    step 9   persist_content    — save LessonContent to output/<id>/content.json
    step 10  compile_assets     — render card images + TTS audio per item (Stage 2)
    step 11  compile_touches    — profile-driven touch sequencing (Stage 3)
    step 12  render_video       — assemble MP4 from touch sequence
    step 13  save_report        — finalize and save Markdown lesson report

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

import asyncio
from pathlib import Path

from jlesson.curriculum import load_curriculum, suggest_new_vocab
from .pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo
from .pipeline_gadgets import PipelineGadgets
from .pipeline_orchestrator import (
    render_existing_lesson as _render_existing_lesson_impl,
    run_pipeline as _run_pipeline_impl,
)
from .compile_assets import CompileAssetsStep
from .compile_touches import CompileTouchesStep
from .generate_sentences import GenerateSentencesStep
from .grammar_select import GrammarSelectStep
from .noun_practice import NounPracticeStep
from .persist_content import PersistContentStep
from .register_lesson import RegisterLessonStep
from .render_video import RenderVideoStep
from .retrieve_material import RetrieveLessonMaterialStep
from .review_sentences import ReviewSentencesStep
from .save_report import SaveReportStep
from .select_vocab import SelectVocabStep
from .verb_practice import VerbPracticeStep


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

PIPELINE: list[PipelineStep] = [
    RetrieveLessonMaterialStep(),
    SelectVocabStep(),
    GrammarSelectStep(),
    GenerateSentencesStep(),
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
    return _run_pipeline_impl(
        config,
        pipeline=PIPELINE,
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
    return _render_existing_lesson_impl(
        lesson_id=lesson_id,
        output_dir=output_dir,
        profile=profile,
        language=language,
        verbose=verbose,
    )


__all__ = [
    "CompileAssetsStep",
    "CompileTouchesStep",
    "GenerateSentencesStep",
    "GrammarSelectStep",
    "LessonConfig",
    "LessonContext",
    "NounPracticeStep",
    "PersistContentStep",
    "PIPELINE",
    "PipelineGadgets",
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
    "suggest_new_vocab",
]
