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
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .curriculum import load_curriculum, suggest_new_vocab
from .language_config import LanguageConfig, get_language_config
from .lesson_report import ReportBuilder
from .lesson_store import load_lesson_content
from .models import (
    CompiledItem,
    GeneralItem,
    GrammarItem,
    Phase,
    Sentence,
    Touch,
)
from .pipeline_gadgets import PipelineGadgets
from .profiles import get_profile
from .retrieval import RetrievalResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class LessonConfig:
    """Configuration for a single lesson run."""

    theme: str
    curriculum_path: Path
    output_dir: Path | None = None
    num_nouns: int = 4
    num_verbs: int = 3
    sentences_per_grammar: int = 3
    seed: int | None = None
    use_cache: bool = True
    render_video: bool = True
    dry_run: bool = False
    verbose: bool = True
    profile: str = "passive_video"
    language: str = "eng-jap"
    narrative: str = ""
    retrieval_enabled: bool = True
    retrieval_store_path: Path | None = None
    retrieval_backend: str = "file"
    retrieval_embedding_model: str = "text-embedding-3-small"
    retrieval_min_coverage: float = 0.6
    retrieval_limit: int = 24


# ---------------------------------------------------------------------------
# Step metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StepInfo:
    """Runtime metadata about the current pipeline step."""

    index: int
    total: int
    name: str
    description: str

    @property
    def label(self) -> str:
        return f"[{self.index}/{self.total}]"

    @property
    def progress(self) -> float:
        """Return step completion ratio (0.0–1.0) for progress bars."""
        return self.index / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# Pipeline context
# ---------------------------------------------------------------------------


@dataclass
class LessonContext:
    """Mutable state accumulated across pipeline steps."""

    config: LessonConfig
    report: ReportBuilder = field(default_factory=ReportBuilder)
    step_info: StepInfo | None = None
    curriculum: dict = field(default_factory=dict)
    vocab: dict = field(default_factory=dict)
    nouns: list[dict] = field(default_factory=list)
    verbs: list[dict] = field(default_factory=list)
    selected_grammar: list[GrammarItem | dict] = field(default_factory=list)
    sentences: list[Sentence] = field(default_factory=list)
    noun_items: list[GeneralItem] = field(default_factory=list)
    verb_items: list[GeneralItem] = field(default_factory=list)
    compiled_items: list[CompiledItem] = field(default_factory=list)
    touches: list[Touch] = field(default_factory=list)
    lesson_id: int = 0
    created_at: str = ""
    content_path: Path | None = None
    video_path: Path | None = None
    report_path: Path | None = None
    language_config: LanguageConfig | None = None
    retrieval_result: RetrievalResult | None = None

    def __post_init__(self) -> None:
        if self.language_config is None:
            self.language_config = get_language_config(self.config.language)


# ---------------------------------------------------------------------------
# Abstract step interface
# ---------------------------------------------------------------------------


class PipelineStep(ABC):
    """Abstract base class for pipeline steps.

    Subclasses set *name* and *description* as class attributes and
    implement execute() to transform the LessonContext.  Steps use
    ctx.report to contribute Markdown content to the lesson report.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def execute(self, ctx: LessonContext) -> LessonContext:
        """Run this step, updating *ctx* and returning it."""
        ...

    @staticmethod
    def _log(ctx: LessonContext, msg: str) -> None:
        if ctx.config.verbose:
            print(msg)


# ---------------------------------------------------------------------------
# Shared gadgets
# ---------------------------------------------------------------------------


from .lesson_pipeline_steps import (
    CompileAssetsStep,
    CompileTouchesStep,
    GenerateSentencesStep,
    GrammarSelectStep,
    NounPracticeStep,
    PersistContentStep,
    RegisterLessonStep,
    RenderVideoStep,
    RetrieveLessonMaterialStep,
    ReviewSentencesStep,
    SaveReportStep,
    SelectVocabStep,
    VerbPracticeStep,
)


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
    """Run the full lesson generation pipeline.

    Loads the curriculum from config.curriculum_path, executes all pipeline
    steps in sequence, and returns the completed LessonContext.
    """
    ctx = LessonContext(config=config)
    ctx.language_config = get_language_config(config.language)
    ctx.curriculum = load_curriculum(config.curriculum_path)
    total = len(PIPELINE)

    print(f"\n{'=' * 60}")
    print(f"  LESSON: {config.theme.upper()}")
    print(f"{'=' * 60}")

    t_total = time.time()
    for i, step in enumerate(PIPELINE, 1):
        info = StepInfo(
            index=i, total=total, name=step.name, description=step.description
        )
        ctx.step_info = info
        if config.verbose:
            print(f"\n  {info.label} {step.description}")
        t_step = time.time()
        ctx = step.execute(ctx)
        ctx.report.record_time(step.name, time.time() - t_step)

    elapsed = time.time() - t_total
    print(f"\n  Done \u2014 {elapsed:.0f}s")
    if ctx.video_path and ctx.video_path.exists():
        print(f"  Video   : {ctx.video_path}")
    if ctx.content_path:
        print(f"  Content : {ctx.content_path}")
    if ctx.report_path:
        print(f"  Report  : {ctx.report_path}")

    return ctx


def render_existing_lesson(
    lesson_id: int,
    output_dir: Path | None = None,
    profile: str = "passive_video",
    language: str = "eng-jap",
    verbose: bool = True,
) -> Path:
    """Render MP4 for an already-generated lesson content file.

    This reuses Stage 2 and Stage 3 compilation against persisted content in
    ``output/lesson_<id>/content.json`` (or language-specific output base), then
    renders ``lesson_<id>_<theme>.mp4``.
    """
    config = LessonConfig(
        theme="",
        curriculum_path=Path("curriculum/curriculum.json"),
        output_dir=output_dir,
        profile=profile,
        language=language,
        verbose=verbose,
    )
    resolved_output_dir = PipelineGadgets.resolve_output_dir(config)
    content = load_lesson_content(lesson_id, resolved_output_dir)
    lang_cfg = get_language_config(content.language or language)
    profile_obj = get_profile(profile)

    items_by_phase = {
        Phase.NOUNS: content.noun_items,
        Phase.VERBS: content.verb_items,
        Phase.GRAMMAR: content.sentences,
    }

    lesson_dir = resolved_output_dir / f"lesson_{lesson_id:03d}"
    step_info = StepInfo(
        index=9,
        total=12,
        name="compile_assets",
        description="Render card images + TTS audio per item",
    )

    from .asset_compiler import compile_assets
    from .touch_compiler import compile_touches
    from .video.builder import VideoBuilder

    compiled_items = asyncio.run(
        compile_assets(
            items_by_phase,
            profile_obj,
            step_info,
            lesson_dir,
            lang_cfg=lang_cfg,
        )
    )
    touches = compile_touches(compiled_items, profile_obj)

    video_builder = VideoBuilder()
    clips = []
    for touch in touches:
        card_path = touch.artifacts.get("card")
        if card_path is None or not card_path.exists():
            continue
        audio_paths = touch.artifacts.get("audio") or []
        clip = video_builder.create_multi_audio_clip(card_path, audio_paths)
        clips.append(clip)

    video_path = resolved_output_dir / f"lesson_{lesson_id:03d}_{content.theme}.mp4"
    if not clips:
        raise ValueError(
            f"No renderable clips found for lesson {lesson_id}. "
            "Check compiled assets under the lesson output directory."
        )

    video_builder.build_video(clips, video_path, method="ffmpeg")
    if verbose:
        print(f"  Rendered {len(clips)} clips -> {video_path}")
    return video_path
