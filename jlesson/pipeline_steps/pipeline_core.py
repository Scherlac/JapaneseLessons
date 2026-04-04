from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar

from jlesson.language_config import LanguageConfig, get_language_config
from jlesson.lesson_report import ReportBuilder
from jlesson.models import GeneralItem, GeneralItem, GrammarItem, Sentence, Touch, Phase,CanonicalItem
from jlesson.curriculum import CurriculumData
from jlesson.runtime.interfaces import RuntimeServices
from jlesson.curriculum import create_curriculum
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from jlesson.pipeline_steps.review_sentences.action import SentenceReviewResult


_UNSET = object()


@dataclass
class LessonConfig:
    """Configuration for a single lesson run."""

    theme: str
    curriculum_path: Path
    output_dir: Path | None = None
    num_nouns: int = 4
    num_verbs: int = 3
    sentences_per_grammar: int = 3
    grammar_points_per_lesson: int = 2
    grammar_points_per_block: int = 1
    lesson_number: int = 1
    lesson_blocks: int = 1
    seed: int | None = None
    use_cache: bool = True
    render_video: bool = True
    dry_run: bool = False
    verbose: bool = True
    profile: str = "passive_video"
    language: str = "eng-jap"
    narrative: list[str] = dataclass_field(default_factory=list)
    retrieval_enabled: bool = True
    retrieval_store_path: Path | None = None
    retrieval_backend: str = "file"
    retrieval_embedding_model: str = "text-embedding-3-small"
    retrieval_min_coverage: float = 0.6
    retrieval_limit: int = 24
    regenerate_lesson_id: int | None = None
    # Step name to resume from (loads checkpoint; skips content generation)
    from_step: str | None = None


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

@dataclass
class LessonContext:
    """Mutable state accumulated across pipeline steps."""

    config: LessonConfig
    language_config: LanguageConfig | None = None
    report: ReportBuilder = dataclass_field(default_factory=ReportBuilder)
    step_info: StepInfo | None = None
    curriculum: CurriculumData = dataclass_field(default_factory=CurriculumData)

    narrative_frame: NarrativeFrame | None = None
    canonical_plan: CanonicalLessonPlan | None = None
    lesson_plan: LessonPlan | None = None

    touch_sequence: TouchSequence | None = None

    rendered_video: RenderedVideoArtifact | None = None
    saved_report: ReportArtifact | None = None

class PipelineStep(ABC):
    """Abstract base class for pipeline steps."""

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
# Typed chunk types
# ---------------------------------------------------------------------------

@dataclass
class BlockChunk:
    """Input snapshot for a single lesson block.

    This is the standard chunk type for steps that iterate **per block** —
    e.g. sentence generation, narrative generation, coherence review.

    Fields map directly to the per-block slices assembled from ``LessonContext``
    by the enclosing ``ActionStep.build_input`` implementation.
    """

    block_index: int
    narrative: str
    nouns: list[GeneralItem]
    verbs: list[GeneralItem]
    grammar: list[GrammarItem]


_T = TypeVar("_T")


@dataclass
class ItemBatch(Generic[_T]):
    """A fixed-size batch of homogeneous items for enrichment steps.

    This is the standard chunk type for steps that iterate **per batch** —
    e.g. noun/verb enrichment, sentence review.

    ``block_index`` is ``-1`` when items span multiple blocks (e.g. review
    steps that process all sentences regardless of their block origin).
    """

    batch_index: int
    block_index: int
    items: list[_T]


# ---------------------------------------------------------------------------
# Narrative inter-step typed artifacts
# ---------------------------------------------------------------------------

@dataclass
class NarrativeConfig:
    """Input chunk for ``NarrativeGeneratorStep``.

    Carries everything needed for one narrative generation call.
    ``lesson_number`` is resolved from curriculum state inside
    ``build_input`` so the action remains free of ``LessonContext``.
    """

    theme: str
    lesson_number: int
    lesson_blocks: int
    seed_blocks: list[str]


@dataclass
class NarrativeFrame(NarrativeConfig):
    """Typed output of ``NarrativeGeneratorStep``.

    Also serves as the input chunk for ``ExtractNarrativeVocabStep``,
    making the inter-step dependency explicit and typed: the same artifact
    that ``NarrativeGeneratorStep`` emits is the chunk type the next step
    directly consumes.

    Context field: ``LessonContext.narrative_blocks``
    """

    blocks: list[str]



# ---------------------------------------------------------------------------
# Lesson plan typed artifacts
# ---------------------------------------------------------------------------


class CanonicalLessonBlock(BaseModel):
    """Fully-resolved lesson plan expressed in canonical (English) terms only.

    Assembled by ``CanonicalPlannerStep.merge_output`` after the two-pass
    planning LLM calls complete.  Persisting this artifact to disk is the
    Phase-1 / Phase-2 boundary: the same plan can later be loaded to drive
    a different language pair without repeating planning-phase LLM calls.

    Context field: ``LessonContext.canonical_plan``
    """

    theme: str
    lesson_number: int
    block_index: int = Field(default=0, description="The 0-based index of this block within the lesson.")
    narrative_content: str = Field(default="", 
        description="The narrative content for this block, e.g. 'The cat climbs the tree.'")
    alternative_content: str = Field(default="", 
        description = ( 
        """An alternative version of the narrative content, e.g. 'The cat is black and likes milk.' 
        This can be used to provide variety in practice sentences or to offer a fallback if the main narrative
        content is too complex for certain grammar points or to avoid spoilers for later narrative blocks.""" ))
    sentiment: str = Field(default="", 
        description= (
        """Optional sentiment or tone label for the block, e.g. 'mishievous', 'heartwarming', 'tense', etc."""))
    grammar_ids: list[str]
    content_sequences: dict[Phase, list[CanonicalItem]]

@dataclass
class CanonicalLessonPlan:
    """Full lesson plan expressed in canonical (English) terms only.

    Assembled by ``CanonicalPlannerStep.merge_output`` after the two-pass
    planning LLM calls complete.  Persisting this artifact to disk is the
    Phase-1 / Phase-2 boundary: the same plan can later be loaded to drive
    a different language pair without repeating planning-phase LLM calls.

    Context field: ``LessonContext.canonical_plan``
    """

    theme: str
    lesson_number: int
    blocks: list[CanonicalLessonBlock]


class LessonBlock(BaseModel):
    """Resolved lesson block with all content and metadata for generation and rendering.

    This is the natural successor artifact to ``CanonicalLessonBlock`` after
    language-specific content is filled in during Phase 2.  It keeps the
    content-resolution boundary explicit and gives later successor-oriented
    refactors a concrete artifact to work with instead of relying only on
    ``LessonContext.canonical_plan``.
    """

    block_index: int = Field(default=0, description="The 0-based index of this block within the lesson.")
    
    content_sequences: dict[Phase, list[GeneralItem]] = Field(default_factory=dict, 
        description=(
        """The core content items for this block, organized by lesson phase (nouns, verbs
        grammar points, etc.).  Each item is expressed in the target language and enriched with
        all metadata needed for sentence generation and rendering (e.g. embeddings, glosses, etc.)."""))


@ dataclass
class LessonPlan:
    """Full lesson plan with all content and metadata for generation and rendering.

    This is the natural successor artifact to ``CanonicalLessonPlan`` after
    language-specific content is filled in during Phase 2.  It keeps the
    content-resolution boundary explicit and gives later successor-oriented
    refactors a concrete artifact to work with instead of relying only on
    ``LessonContext.lesson_plan``.
    """

    blocks: list[LessonBlock]


# ---------------------------------------------------------------------------
# Render inter-step typed artifacts
# ---------------------------------------------------------------------------

@dataclass
class GeneralItemSequence:
    """Typed render-ready output of ``CompileAssetsStep``.

    Also serves as the input chunk for ``CompileTouchesStep``, making the
    render-side successor dependency explicit even before ``compile_assets`` is
    migrated to ``ActionStep`` form.

    Context field: ``LessonContext.compiled_items``
    """

    items: list[GeneralItem]


@dataclass
class TouchSequence:
    """Typed output of ``CompileTouchesStep``.

    This is the natural successor artifact for later ``RenderVideoStep``
    migration, where the video render step can consume the same typed artifact
    rather than reading raw touch lists directly from ``LessonContext``.

    Context field: ``LessonContext.touches``
    """

    items: list[Touch]


@dataclass
class RenderedVideoArtifact:
    """Typed output of ``RenderVideoStep``.

    This is the render-side sink artifact produced from ``TouchSequence``.
    A later ``SaveReportStep`` migration can use this typed result instead of
    relying only on ``LessonContext.video_path``.

    Context field: ``LessonContext.video_path``
    """

    video_path: Path | None
    clip_count: int
    cards_dir: Path | None = None
    audio_dir: Path | None = None


@dataclass
class ReportArtifact:
    """Typed output of ``SaveReportStep``.

    This is the final sink artifact for the pipeline's report output. It lets
    successor-oriented decomposition continue even for terminal steps.

    Context field: ``LessonContext.report_path``
    """

    report_path: Path | None


@dataclass
class LessonRegistrationArtifact:
    """Typed output of ``RegisterLessonStep``.

    This is the storage-side handoff artifact produced before lesson-content
    persistence. A later ``PersistContentStep`` migration can consume this
    artifact instead of relying only on ``lesson_id`` and ``created_at`` on the
    shared context.

    Context fields: ``LessonContext.lesson_id``, ``LessonContext.created_at``
    """

    lesson_id: int
    created_at: str
    curriculum: CurriculumData
    header_markdown: str


@dataclass
class PersistedContentArtifact:
    """Typed output of ``PersistContentStep``.

    This is the storage-side persistence result produced after lesson
    registration. It keeps the content-write boundary explicit and gives later
    successor-oriented refactors a concrete artifact instead of relying only on
    ``LessonContext.content_path``.

    Context field: ``LessonContext.content_path``
    """

    lesson_id: int
    created_at: str
    content_path: Path | None


# ---------------------------------------------------------------------------
# Per-invocation action configuration
# ---------------------------------------------------------------------------

@dataclass
class ActionConfig:
    """Immutable per-invocation scope passed to every ``StepAction``.

    Carries the three configuration dimensions visible to a single action call:

    lesson
        Full lesson-level settings (num_nouns, sentences_per_grammar, etc.).
    block_index
        Which block this invocation handles (0-based).
    language
        Language-pair specific prompts, generators, and labels.
    runtime
        I/O facade for LLM calls, retrieval, storage, and cache.
    """
    curriculum: CurriculumData
    lesson: LessonConfig
    block_index: int
    language: LanguageConfig
    runtime: RuntimeServices


# ---------------------------------------------------------------------------
# Step action and action step abstractions
# ---------------------------------------------------------------------------

_I = TypeVar("_I")
_O = TypeVar("_O")


class StepAction(ABC, Generic[_I, _O]):
    """Single, stateless transformation: ``(ActionConfig, chunk: I) → O``.

    A ``StepAction`` encapsulates one logical transformation for one chunk of
    work — one block, one batch, one item.  It has no knowledge of
    ``LessonContext`` and no iteration logic.  All I/O is done through
    ``config.runtime`` (a ``RuntimeServices`` instance).

    This makes actions independently testable: supply a mock ``RuntimeServices``
    and a typed chunk, and inspect the output without a live pipeline context.
    """

    @abstractmethod
    def run(self, config: ActionConfig, chunk: _I) -> _O:
        """Execute the action for one *chunk*; return the output."""
        ...


class ActionStep(PipelineStep, Generic[_I, _O]):
    """``PipelineStep`` that drives a ``StepAction`` over typed input chunks.

    Subclasses implement four declarative methods; ``execute`` handles the rest:

    ``action``
        The ``StepAction`` to invoke for each chunk.
    ``should_skip(ctx)``
        Return ``True`` when this step's output is already present in *ctx*
        (idempotency guard, e.g. when retrieval pre-populated the field).
    ``build_input(ctx)``
        Decompose *ctx* into the ordered list of typed input chunks.
    ``merge_output(ctx, outputs)``
        Write the collected action outputs back to *ctx* and return it.

    The iteration contract
    ----------------------
    ``execute`` calls ``build_input``, then for each chunk it constructs an
    ``ActionConfig`` (binding the current ``LessonContext`` into a
    ``ContextRuntime``) and invokes ``action.run(config, chunk)``.  After all
    chunks are processed, ``merge_output`` is called once with the full list
    of outputs.

    ``block_index`` is read from ``chunk.block_index`` when the attribute
    exists (``BlockChunk``, ``ItemBatch``); it falls back to the loop index
    for custom chunk types that omit the attribute.
    """

    @property
    @abstractmethod
    def action(self) -> StepAction[_I, _O]:
        """The ``StepAction`` to invoke for each chunk."""
        ...

    @abstractmethod
    def should_skip(self, ctx: LessonContext) -> bool:
        """Return ``True`` when this step's output is already populated."""
        ...

    @abstractmethod
    def build_input(self, ctx: LessonContext) -> _I:
        """Decompose *ctx* into the ordered list of input chunks."""
        ...

    @abstractmethod
    def merge_output(self, ctx: LessonContext, outputs: _O) -> LessonContext:
        """Apply the collected *outputs* back to *ctx* and return it."""
        ...

    @abstractmethod
    def build_input_list(self, ctx: LessonContext) -> list[_I]:
        """Decompose *ctx* into the ordered list of input chunks."""
        return []

    @abstractmethod
    def merge_output_list(self, ctx: LessonContext, outputs: list[_O]) -> LessonContext:
        """Apply the collected *outputs* back to *ctx* and return it."""
        ...

    def process_list(self, ctx: LessonContext, chunks: list[_I]) -> list[_O]:

        from jlesson.runtime._base import ContextRuntime  # local import avoids circularity
        rt = ContextRuntime(ctx)

        self._last_chunks = deepcopy(chunks)
        outputs: list[_O] = []
        for loop_index, chunk in enumerate(chunks):
            block_index = getattr(chunk, "block_index", loop_index)
            cfg = ActionConfig(
                curriculum=ctx.curriculum,
                lesson=ctx.config,
                block_index=block_index,
                language=ctx.language_config,
                runtime=rt,
            )
            outputs.append(self.action.run(cfg, chunk))

        self._last_outputs = deepcopy(outputs)
        return self.merge_output_list(ctx, outputs)
    
    def process_single(self, ctx: LessonContext) -> LessonContext:

        from jlesson.runtime._base import ContextRuntime  # local import avoids circularity
        rt = ContextRuntime(ctx)
        
        inputs = self.build_input(ctx)
        cfg = ActionConfig(
            curriculum=ctx.curriculum,
            lesson=ctx.config,
            block_index=0,
            language=ctx.language_config,
            runtime=rt,
        )
        output = self.action.run(cfg, inputs)

        self._last_chunks = [inputs]
        self._last_outputs = [output]

        return self.merge_output(ctx, output)



    def execute(self, ctx: LessonContext) -> LessonContext:
        if self.should_skip(ctx):
            self._last_chunks: list = []
            self._last_outputs: list = []
            return ctx

        chunks = self.build_input_list(ctx)

        if len(chunks) > 0:
            return self.process_list(ctx, chunks)
        else:
            return self.process_single(ctx)

