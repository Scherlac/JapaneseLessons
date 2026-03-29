from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from jlesson.language_config import LanguageConfig, get_language_config
from jlesson.lesson_report import ReportBuilder
from jlesson.models import CompiledItem, GeneralItem, GrammarItem, Sentence, Touch
from jlesson.retrieval import RetrievalResult
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
    vocab: dict = field(default_factory=dict)
    nouns: list[GeneralItem] = field(default_factory=list)
    verbs: list[GeneralItem] = field(default_factory=list)
    narrative_blocks: list[str] = field(default_factory=list)
    narrative_vocab_terms: list[dict[str, list[str]]] = field(default_factory=list)
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