from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar

from jlesson.language_config import LanguageConfig, get_language_config
from jlesson.lesson_report import ReportBuilder
from jlesson.models import CompiledItem, GeneralItem, GrammarItem, NarrativeVocabBlock, Sentence, Touch, VocabFile
from jlesson.models import CanonicalItem
from jlesson.curriculum import CurriculumData
from jlesson.runtime.interfaces import RuntimeServices
from jlesson.curriculum import create_curriculum

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
    report: ReportBuilder = field(default_factory=ReportBuilder)
    step_info: StepInfo | None = None
    curriculum: CurriculumData = field(default_factory=CurriculumData)

    # Step 1: narrative_generator -> extract_narrative_vocab
    narrative_frame: NarrativeFrame | None = None
    # Step 2: extract_narrative_vocab -> canonical_vocab_select
    narrative_vocab_plan: NarrativeVocabPlan | None = None
    # Step 3: canonical_vocab_select -> select_vocab / lesson_planner / grammar_select
    canonical_vocab: CanonicalVocabSelection | None = None
    # Step 4: select_vocab -> narrative_grammar / review_sentences / vocab_enhancement / register_lesson
    selected_vocab: SelectedVocabSet | None = None
    # Step 5: lesson_planner / grammar_select -> narrative_grammar / register_lesson / persist_content
    grammar_selection: GrammarSelectionArtifact | None = None
    # Step 6: narrative_grammar -> review_sentences
    generated_sentence_blocks: list[list[Sentence]] = field(default_factory=list)
    # Step 7: review_sentences -> register_lesson / persist_content / compile_assets
    review_results: list[SentenceReviewResult] = field(default_factory=list)
    # Step 8: vocab_enhancement -> register_lesson / persist_content / compile_assets / save_report
    vocab_enhancement: VocabEnhancementArtifact | None = None
    # Step 9: register_lesson -> persist_content
    lesson_registration: LessonRegistrationArtifact | None = None
    # Step 10: persist_content -> checkpoint/reporting
    persisted_content: PersistedContentArtifact | None = None
    # Step 11: compile_assets -> compile_touches
    compiled_sequence: CompiledItemSequence | None = None
    # Step 12: compile_touches -> render_video / save_report
    touch_sequence: TouchSequence | None = None
    # Step 13: render_video -> save_report
    rendered_video: RenderedVideoArtifact | None = None
    # Step 14: save_report -> terminal sink
    saved_report: ReportArtifact | None = None

    lesson_id: int = 0
    artifact_lesson_id: int = 0
    created_at: str = ""
    content_path: Path | None = None
    video_path: Path | None = None
    report_path: Path | None = None
    language_config: LanguageConfig | None = None
    pipeline_started_at: str = ""
    completed_steps: list[str] = field(default_factory=list)
    step_timings: dict[str, float] = field(default_factory=dict)
    # Per-step detail records accumulated during run
    step_details: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.language_config is None:
            self.language_config = get_language_config(self.config.language)

    # def _update_selected_vocab(
    #     self,
    #     *,
    #     vocab=_UNSET,
    #     nouns=_UNSET,
    #     verbs=_UNSET,
    # ) -> None:
    #     current = self.selected_vocab or SelectedVocabSet(vocab=None, nouns=[], verbs=[])
    #     updated = SelectedVocabSet(
    #         vocab=current.vocab if vocab is _UNSET else vocab,
    #         nouns=list(current.nouns) if nouns is _UNSET else list(nouns),
    #         verbs=list(current.verbs) if verbs is _UNSET else list(verbs),
    #     )
    #     self.selected_vocab = updated if (updated.vocab is not None or updated.nouns or updated.verbs) else None
    #     if self.vocab_enhancement is not None:
    #         self.vocab_enhancement = VocabEnhancementArtifact(
    #             vocab=updated.vocab,
    #             nouns=list(updated.nouns),
    #             verbs=list(updated.verbs),
    #             noun_items=list(self.vocab_enhancement.noun_items),
    #             verb_items=list(self.vocab_enhancement.verb_items),
    #         )

    # def _update_grammar_selection(
    #     self,
    #     *,
    #     selected_grammar=_UNSET,
    #     selected_grammar_blocks=_UNSET,
    #     lesson_outline=_UNSET,
    #     canonical_plan=_UNSET,
    # ) -> None:
    #     current = self.grammar_selection or GrammarSelectionArtifact(
    #         selected_grammar=[],
    #         selected_grammar_blocks=[],
    #         lesson_outline=None,
    #         canonical_plan=None,
    #     )
    #     updated = GrammarSelectionArtifact(
    #         selected_grammar=(
    #             list(current.selected_grammar)
    #             if selected_grammar is _UNSET
    #             else list(selected_grammar)
    #         ),
    #         selected_grammar_blocks=(
    #             [list(block) for block in current.selected_grammar_blocks]
    #             if selected_grammar_blocks is _UNSET
    #             else [list(block) for block in selected_grammar_blocks]
    #         ),
    #         lesson_outline=current.lesson_outline if lesson_outline is _UNSET else lesson_outline,
    #         canonical_plan=current.canonical_plan if canonical_plan is _UNSET else canonical_plan,
    #     )
    #     self.grammar_selection = updated

    # def _update_vocab_enhancement(
    #     self,
    #     *,
    #     noun_items=_UNSET,
    #     verb_items=_UNSET,
    # ) -> None:
    #     base_vocab = self.selected_vocab or SelectedVocabSet(vocab=None, nouns=[], verbs=[])
    #     current = self.vocab_enhancement or VocabEnhancementArtifact(
    #         vocab=base_vocab.vocab,
    #         nouns=list(base_vocab.nouns),
    #         verbs=list(base_vocab.verbs),
    #         noun_items=[],
    #         verb_items=[],
    #     )
    #     updated = VocabEnhancementArtifact(
    #         vocab=current.vocab,
    #         nouns=list(current.nouns),
    #         verbs=list(current.verbs),
    #         noun_items=list(current.noun_items) if noun_items is _UNSET else list(noun_items),
    #         verb_items=list(current.verb_items) if verb_items is _UNSET else list(verb_items),
    #     )
    #     self.vocab_enhancement = updated if (
    #         updated.vocab is not None or updated.nouns or updated.verbs or updated.noun_items or updated.verb_items
    #     ) else None
    #     self.selected_vocab = SelectedVocabSet(
    #         vocab=updated.vocab,
    #         nouns=list(updated.nouns),
    #         verbs=list(updated.verbs),
    #     ) if (updated.vocab is not None or updated.nouns or updated.verbs) else None

    # @property
    # def narrative_blocks(self) -> list[str]:
    #     return list(self.narrative_frame.blocks) if self.narrative_frame is not None else []

    # @narrative_blocks.setter
    # def narrative_blocks(self, blocks: list[str]) -> None:
    #     self.narrative_frame = NarrativeFrame(blocks=list(blocks)) if blocks else None

    # @property
    # def narrative_vocab_terms(self) -> list[NarrativeVocabBlock]:
    #     return list(self.narrative_vocab_plan.blocks) if self.narrative_vocab_plan is not None else []

    # @narrative_vocab_terms.setter
    # def narrative_vocab_terms(self, blocks: list[NarrativeVocabBlock]) -> None:
    #     self.narrative_vocab_plan = NarrativeVocabPlan(blocks=list(blocks)) if blocks else None

    # @property
    # def vocab(self) -> VocabFile | None:
    #     if self.vocab_enhancement is not None:
    #         return self.vocab_enhancement.vocab
    #     if self.selected_vocab is not None:
    #         return self.selected_vocab.vocab
    #     return None

    # @vocab.setter
    # def vocab(self, value: VocabFile | None) -> None:
    #     self._update_selected_vocab(vocab=value)

    # @property
    # def nouns(self) -> list[GeneralItem]:
    #     if self.vocab_enhancement is not None:
    #         return list(self.vocab_enhancement.nouns)
    #     if self.selected_vocab is not None:
    #         return list(self.selected_vocab.nouns)
    #     return []

    # @nouns.setter
    # def nouns(self, items: list[GeneralItem]) -> None:
    #     self._update_selected_vocab(nouns=items)

    # @property
    # def verbs(self) -> list[GeneralItem]:
    #     if self.vocab_enhancement is not None:
    #         return list(self.vocab_enhancement.verbs)
    #     if self.selected_vocab is not None:
    #         return list(self.selected_vocab.verbs)
    #     return []

    # @verbs.setter
    # def verbs(self, items: list[GeneralItem]) -> None:
    #     self._update_selected_vocab(verbs=items)

    # @property
    # def selected_grammar(self) -> list[GrammarItem]:
    #     return list(self.grammar_selection.selected_grammar) if self.grammar_selection is not None else []

    # @selected_grammar.setter
    # def selected_grammar(self, items: list[GrammarItem]) -> None:
    #     self._update_grammar_selection(selected_grammar=items)

    # @property
    # def selected_grammar_blocks(self) -> list[list[GrammarItem]]:
    #     return [list(block) for block in self.grammar_selection.selected_grammar_blocks] if self.grammar_selection is not None else []

    # @selected_grammar_blocks.setter
    # def selected_grammar_blocks(self, blocks: list[list[GrammarItem]]) -> None:
    #     self._update_grammar_selection(selected_grammar_blocks=blocks)

    # @property
    # def lesson_outline(self) -> LessonOutline | None:
    #     return self.grammar_selection.lesson_outline if self.grammar_selection is not None else None

    # @lesson_outline.setter
    # def lesson_outline(self, outline: LessonOutline | None) -> None:
    #     self._update_grammar_selection(lesson_outline=outline)

    # @property
    # def canonical_plan(self) -> CanonicalLessonPlan | None:
    #     return self.grammar_selection.canonical_plan if self.grammar_selection is not None else None

    # @canonical_plan.setter
    # def canonical_plan(self, plan: CanonicalLessonPlan | None) -> None:
    #     self._update_grammar_selection(canonical_plan=plan)

    # @property
    # def sentences(self) -> list[Sentence]:
    #     if self.review_results:
    #         return [sentence for result in self.review_results for sentence in result.sentences]
    #     return [sentence for block in self.generated_sentence_blocks for sentence in block]

    # @sentences.setter
    # def sentences(self, items: list[Sentence]) -> None:
    #     self.review_results = []
    #     self.generated_sentence_blocks = [list(items)] if items else []

    # @property
    # def noun_items(self) -> list[GeneralItem]:
    #     return list(self.vocab_enhancement.noun_items) if self.vocab_enhancement is not None else []

    # @noun_items.setter
    # def noun_items(self, items: list[GeneralItem]) -> None:
    #     self._update_vocab_enhancement(noun_items=items)

    # @property
    # def verb_items(self) -> list[GeneralItem]:
    #     return list(self.vocab_enhancement.verb_items) if self.vocab_enhancement is not None else []

    # @verb_items.setter
    # def verb_items(self, items: list[GeneralItem]) -> None:
    #     self._update_vocab_enhancement(verb_items=items)

    # @property
    # def compiled_items(self) -> list[CompiledItem]:
    #     return list(self.compiled_sequence.items) if self.compiled_sequence is not None else []

    # @compiled_items.setter
    # def compiled_items(self, items: list[CompiledItem]) -> None:
    #     self.compiled_sequence = CompiledItemSequence(items=list(items)) if items else None

    # @property
    # def touches(self) -> list[Touch]:
    #     return list(self.touch_sequence.items) if self.touch_sequence is not None else []

    # @touches.setter
    # def touches(self, items: list[Touch]) -> None:
    #     self.touch_sequence = TouchSequence(items=list(items)) if items else None

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


@dataclass
class NarrativeVocabPlan:
    """Typed output of ``ExtractNarrativeVocabStep``.

    Consumed by ``CanonicalVocabSelectStep`` to pick canonical English vocab
    terms for the planning phase.

    Context field: ``LessonContext.narrative_vocab_terms``
    """

    blocks: list[NarrativeVocabBlock]


# ---------------------------------------------------------------------------
# Lesson outline typed artifacts
# ---------------------------------------------------------------------------

@dataclass
class BlockOutline:
    """Planned content for a single lesson block."""

    block_index: int
    grammar_ids: list[str]
    noun_suggestions: list[str]
    verb_suggestions: list[str]
    sentence_count: int
    narrative_summary: str


@dataclass
class LessonOutline:
    """Full lesson plan produced by the two-pass lesson planner.

    Context field: ``LessonContext.lesson_outline``
    """

    blocks: list[BlockOutline]
    grammar_ids: list[str]
    rationale: str = ""


@dataclass
class SelectedVocabSet:
    """Typed output of ``SelectVocabStep``.

    This is the stable vocab-selection artifact handed to later lesson-content
    generation steps. ``GrammarSelectStep`` uses this as its visible
    predecessor artifact by extending it in its request chunk.

    Context fields: ``LessonContext.vocab``, ``LessonContext.nouns``,
    ``LessonContext.verbs``
    """

    vocab: VocabFile | None
    nouns: list[GeneralItem]
    verbs: list[GeneralItem]


@dataclass
class CanonicalVocabSelection:
    """Canonical (language-neutral) vocabulary selection for the planning phase.

    All fields use English canonical terms only — no source or target language
    forms.  This artifact is produced by ``CanonicalVocabSelectStep`` and
    consumed by ``LessonPlannerStep`` and ``GrammarSelectStep`` so that the
    entire planning phase stays free of language-specific content.

    ``nouns_per_block`` and ``verbs_per_block`` record which canonical terms
    are assigned to each lesson block.  ``SelectVocabStep`` uses these lists
    during Phase 2 to look up the matching ``VocabItem`` rows in the
    generated ``VocabFile`` and build ``GeneralItem`` objects.

    Context field: ``LessonContext.canonical_vocab``
    """

    nouns: list[CanonicalItem] = field(default_factory=list)
    verbs: list[CanonicalItem] = field(default_factory=list)
    nouns_per_block: list[list[str]] = field(default_factory=list)  # canonical texts per block (index matches block_index)
    verbs_per_block: list[list[str]] = field(default_factory=list)


@dataclass
class CanonicalLessonPlan:
    """Fully-resolved lesson plan expressed in canonical (English) terms only.

    Assembled by ``LessonPlannerStep.merge_outputs`` after the two-pass
    planning LLM calls complete.  Persisting this artifact to disk is the
    Phase-1 / Phase-2 boundary: the same plan can later be loaded to drive
    a different language pair without repeating planning-phase LLM calls.

    Context field: ``LessonContext.canonical_plan``
    """

    theme: str
    lesson_number: int
    narrative_blocks: list[str]
    canonical_vocab: CanonicalVocabSelection
    grammar_ids: list[str]
    grammar_blocks: list[list[str]]
    lesson_outline: "LessonOutline | None" = None


@dataclass
class GrammarSelectionArtifact:
    """Unified grammar-planning artifact for lesson_planner and grammar_select.

    Keeps the grammar-selection handoff explicit on ``LessonContext`` even
    though the codebase currently has both the modern ``LessonPlannerStep`` and
    the compatibility ``GrammarSelectStep``.
    """

    selected_grammar: list[GrammarItem]
    selected_grammar_blocks: list[list[GrammarItem]]
    lesson_outline: LessonOutline | None = None
    canonical_plan: CanonicalLessonPlan | None = None


@dataclass
class VocabEnhancementArtifact(SelectedVocabSet):
    """Typed output of ``VocabEnhancementStep``.

    This keeps the selected-vocab predecessor artifact visible while adding the
    richer noun/verb practice payload needed by later storage and persistence
    steps.

    Context fields: ``LessonContext.noun_items``, ``LessonContext.verb_items``
    """

    noun_items: list[GeneralItem]
    verb_items: list[GeneralItem]


# ---------------------------------------------------------------------------
# Render inter-step typed artifacts
# ---------------------------------------------------------------------------

@dataclass
class CompiledItemSequence:
    """Typed render-ready output of ``CompileAssetsStep``.

    Also serves as the input chunk for ``CompileTouchesStep``, making the
    render-side successor dependency explicit even before ``compile_assets`` is
    migrated to ``ActionStep`` form.

    Context field: ``LessonContext.compiled_items``
    """

    items: list[CompiledItem]


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
            self._last_chunks: list = []
            self._last_outputs: list = []
            return ctx

        from jlesson.runtime._base import ContextRuntime  # local import avoids circularity

        rt = ContextRuntime(ctx)
        chunks = self.build_chunks(ctx)
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
        return self.merge_outputs(ctx, outputs)
