from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar

from jlesson.language_config import LanguageConfig, get_language_config
from jlesson.lesson_report import ReportBuilder
from jlesson.models import CompiledItem, GeneralItem, GrammarItem, NarrativeVocabBlock, Sentence, Touch, VocabFile
from jlesson.retrieval import RetrievalResult
from jlesson.runtime.interfaces import RuntimeServices
from jlesson.curriculum import CurriculumData, create_curriculum


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
    lesson_blocks: int = 1
    seed: int | None = None
    use_cache: bool = True
    render_video: bool = True
    dry_run: bool = False
    verbose: bool = True
    profile: str = "passive_video"
    language: str = "eng-jap"
    narrative: list[str] = field(default_factory=list)
    retrieval_enabled: bool = True
    retrieval_store_path: Path | None = None
    retrieval_backend: str = "file"
    retrieval_embedding_model: str = "text-embedding-3-small"
    retrieval_min_coverage: float = 0.6
    retrieval_limit: int = 24


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
    report: ReportBuilder = field(default_factory=ReportBuilder)
    step_info: StepInfo | None = None
    curriculum: CurriculumData = field(default_factory=create_curriculum)
    vocab: VocabFile | None = None
    nouns: list[GeneralItem] = field(default_factory=list)
    verbs: list[GeneralItem] = field(default_factory=list)
    narrative_blocks: list[str] = field(default_factory=list)
    narrative_vocab_terms: list[NarrativeVocabBlock] = field(default_factory=list)
    selected_grammar: list[GrammarItem] = field(default_factory=list)
    selected_grammar_blocks: list[list[GrammarItem]] = field(default_factory=list)
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
    by the enclosing ``ActionStep.build_chunks`` implementation.
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
class NarrativeGenChunk:
    """Input chunk for ``NarrativeGeneratorStep``.

    Carries everything needed for one narrative generation call.
    ``lesson_number`` is resolved from curriculum state inside
    ``build_chunks`` so the action remains free of ``LessonContext``.
    """

    theme: str
    lesson_number: int
    lesson_blocks: int
    seed_blocks: list[str]


@dataclass
class NarrativeFrame:
    """Typed output of ``NarrativeGeneratorStep``.

    Also serves as the input chunk for ``ExtractNarrativeVocabStep``,
    making the inter-step dependency explicit and typed: the same artifact
    that ``NarrativeGeneratorStep`` emits is the chunk type the next step
    directly consumes.

    Context field: ``LessonContext.narrative_blocks``
    """

    blocks: list[str]


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
    ``build_chunks(ctx)``
        Decompose *ctx* into the ordered list of typed input chunks.
    ``merge_outputs(ctx, outputs)``
        Write the collected action outputs back to *ctx* and return it.

    The iteration contract
    ----------------------
    ``execute`` calls ``build_chunks``, then for each chunk it constructs an
    ``ActionConfig`` (binding the current ``LessonContext`` into a
    ``ContextRuntime``) and invokes ``action.run(config, chunk)``.  After all
    chunks are processed, ``merge_outputs`` is called once with the full list
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
    def build_chunks(self, ctx: LessonContext) -> list[_I]:
        """Decompose *ctx* into the ordered list of input chunks."""
        ...

    @abstractmethod
    def merge_outputs(self, ctx: LessonContext, outputs: list[_O]) -> LessonContext:
        """Apply the collected *outputs* back to *ctx* and return it."""
        ...

    def execute(self, ctx: LessonContext) -> LessonContext:
        if self.should_skip(ctx):
            return ctx

        from jlesson.runtime._base import ContextRuntime  # local import avoids circularity

        rt = ContextRuntime(ctx)
        chunks = self.build_chunks(ctx)
        outputs: list[_O] = []
        for loop_index, chunk in enumerate(chunks):
            block_index = getattr(chunk, "block_index", loop_index)
            cfg = ActionConfig(
                lesson=ctx.config,
                block_index=block_index,
                language=ctx.language_config,
                runtime=rt,
            )
            outputs.append(self.action.run(cfg, chunk))

        return self.merge_outputs(ctx, outputs)
