"""
Lesson generation pipeline.

Orchestrates the full lesson workflow through fifteen sequential steps:

    step 1   retrieve_material  — optional retrieval with safe fallback
    step 2   narrative_generator     — create block-by-block story progression
    step 3   extract_narrative_vocab — extract block-level vocab targets
    step 4   select_vocab            — pick fresh nouns/verbs from the vocab file
    step 5   grammar_select          — LLM: pick grammar points for this lesson
    step 6   narrative_grammar       — LLM: produce block-aware practice sentences
    step 7   review_sentences        — LLM: rate naturalness, rewrite awkward sentences
    step 8   noun_practice           — LLM: enrich nouns with examples + memory tips
    step 9   verb_practice           — LLM: enrich verbs with conjugations + memory tips
    step 10  register_lesson         — add+complete the lesson in curriculum.json
    step 11  persist_content         — save LessonContent to output/<id>/content.json
    step 12  compile_assets          — render card images + TTS audio per item (Stage 2)
    step 13  compile_touches         — profile-driven touch sequencing (Stage 3)
    step 14  render_video            — assemble MP4 from touch sequence
    step 15  save_report             — finalize and save Markdown lesson report

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
from importlib import import_module
from typing import Any

from .pipeline_core import LessonConfig, LessonContext, PipelineStep, StepInfo

_EXPORTS: dict[str, tuple[str, str]] = {
    "CompileAssetsStep": (".compile_assets", "CompileAssetsStep"),
    "CompileTouchesStep": (".compile_touches", "CompileTouchesStep"),
    "ExtractNarrativeVocabStep": (".extract_narrative_vocab", "ExtractNarrativeVocabStep"),
    "GenerateSentencesStep": (".generate_sentences", "GenerateSentencesStep"),
    "GrammarSelectStep": (".grammar_select", "GrammarSelectStep"),
    "NarrativeGeneratorStep": (".narrative_generator", "NarrativeGeneratorStep"),
    "NarrativeGrammarStep": (".generate_sentences", "NarrativeGrammarStep"),
    "NounPracticeStep": (".noun_practice", "NounPracticeStep"),
    "PersistContentStep": (".persist_content", "PersistContentStep"),
    "PipelineGadgets": (".pipeline_gadgets", "PipelineGadgets"),
    "RegisterLessonStep": (".register_lesson", "RegisterLessonStep"),
    "RenderVideoStep": (".render_video", "RenderVideoStep"),
    "RetrieveLessonMaterialStep": (".retrieve_material", "RetrieveLessonMaterialStep"),
    "ReviewSentencesStep": (".review_sentences", "ReviewSentencesStep"),
    "SaveReportStep": (".save_report", "SaveReportStep"),
    "SelectVocabStep": (".select_vocab", "SelectVocabStep"),
    "VerbPracticeStep": (".verb_practice", "VerbPracticeStep"),
}


def _build_pipeline() -> list[PipelineStep]:
    return [
        __getattr__("RetrieveLessonMaterialStep")(),
        __getattr__("NarrativeGeneratorStep")(),
        __getattr__("ExtractNarrativeVocabStep")(),
        __getattr__("SelectVocabStep")(),
        __getattr__("GrammarSelectStep")(),
        __getattr__("NarrativeGrammarStep")(),
        __getattr__("ReviewSentencesStep")(),
        __getattr__("NounPracticeStep")(),
        __getattr__("VerbPracticeStep")(),
        __getattr__("RegisterLessonStep")(),
        __getattr__("PersistContentStep")(),
        __getattr__("CompileAssetsStep")(),
        __getattr__("CompileTouchesStep")(),
        __getattr__("RenderVideoStep")(),
        __getattr__("SaveReportStep")(),
    ]


def run_pipeline(config: LessonConfig) -> LessonContext:
    """Run the full lesson generation pipeline."""
    from jlesson.curriculum import load_curriculum
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


def __getattr__(name: str) -> Any:
    if name == "PIPELINE":
        return _build_pipeline()
    if name in {"load_curriculum", "suggest_new_vocab"}:
        curriculum = import_module("jlesson.curriculum")
        return getattr(curriculum, name)
    if name in _EXPORTS:
        module_name, attr_name = _EXPORTS[name]
        module = import_module(module_name, __name__)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "CompileAssetsStep",
    "CompileTouchesStep",
    "ExtractNarrativeVocabStep",
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
