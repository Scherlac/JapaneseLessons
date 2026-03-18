"""
Lesson generation pipeline.

Orchestrates the full lesson workflow through twelve sequential steps:

  step 1   select_vocab       — pick fresh nouns/verbs from the vocab file
  step 2   grammar_select     — LLM: pick 1-2 grammar points for this lesson
  step 3   generate_sentences — LLM: produce practice sentences
  step 4   review_sentences   — LLM: rate naturalness, rewrite awkward sentences
  step 5   noun_practice      — LLM: enrich nouns with examples + memory tips
  step 6   verb_practice      — LLM: enrich verbs with conjugations + memory tips
  step 7   register_lesson    — add+complete the lesson in curriculum.json
  step 8   persist_content    — save LessonContent to output/<id>/content.json
  step 9   compile_assets     — render card images + TTS audio per item (Stage 2)
  step 10  compile_touches    — profile-driven touch sequencing (Stage 3)
  step 11  render_video       — assemble MP4 from touch sequence
  step 12  save_report        — finalize and save Markdown lesson report

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
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .curriculum import (
    add_lesson,
    complete_lesson,
    get_grammar_by_id,
    get_next_grammar,
    get_next_grammar_from,
    load_curriculum,
    save_curriculum,
    suggest_new_vocab,
)
from .language_config import LanguageConfig, get_language_config
from .lesson_report import ReportBuilder, save_report
from .lesson_store import save_lesson_content
from .llm_client import ask_llm_json_free
from .models import (
    CompiledItem,
    GeneralItem,
    GrammarItem,
    LessonContent,
    NounItem,
    Phase,
    Sentence,
    Touch,
    VerbItem,
)
from .profiles import get_profile
from .prompt_template import (
    build_grammar_generate_prompt,
    build_grammar_select_prompt,
    build_noun_practice_prompt,
    build_sentence_review_prompt,
    build_verb_practice_prompt,
    hungarian_build_grammar_generate_prompt,
    hungarian_build_grammar_select_prompt,
    hungarian_build_noun_practice_prompt,
    hungarian_build_sentence_review_prompt,
    hungarian_build_verb_practice_prompt,
)

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
    selected_grammar: list[GrammarItem] = field(default_factory=list)
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
# Internal helpers
# ---------------------------------------------------------------------------

_VOCAB_DIR = Path(__file__).parent.parent / "vocab"


def _load_vocab(theme: str, vocab_dir: Path | None = None) -> dict:
    """Load vocab file; generate via LLM if missing."""
    base_dir = vocab_dir if vocab_dir is not None else _VOCAB_DIR
    path = base_dir / f"{theme}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    print(f"  [vocab] {theme}.json not found — generating via LLM...")
    from .vocab_generator import generate_vocab

    return generate_vocab(theme=theme, num_nouns=12, num_verbs=10, output_dir=base_dir)


def _ask_llm(ctx: LessonContext, prompt: str) -> dict:
    """Route LLM call through cache when use_cache is enabled."""
    if ctx.config.use_cache:
        from .llm_cache import ask_llm_cached

        return ask_llm_cached(prompt)
    return ask_llm_json_free(prompt)


def _resolve_output_dir(config: LessonConfig) -> Path:
    base = Path(config.output_dir) if config.output_dir is not None else Path(__file__).parent.parent / "output"
    if config.language != "eng-jap":
        lang_cfg = get_language_config(config.language)
        return base / lang_cfg.native_language.lower()
    return base


def _build_video_items(noun_items: list[dict], sentences: list[dict]) -> list[dict]:
    """Convert noun_items + sentences into per-card dicts for the video pipeline."""
    items = []
    total = len(noun_items) + len(sentences)

    for i, noun in enumerate(noun_items, 1):
        jp = noun.get("japanese", "")
        romaji = noun.get("romaji", "")
        reveal = f"{jp}  ({romaji})" if romaji else jp
        items.append(
            {
                "phase": "Nouns",
                "step": "INTRODUCE",
                "counter": f"{i}/{total}",
                "prompt": noun.get("english", ""),
                "reveal": reveal,
                "tts_text": jp,
                "tts_voice": "ja-JP-NanamiNeural",
            }
        )

    offset = len(noun_items)
    for i, sent in enumerate(sentences, 1):
        items.append(
            {
                "phase": "Grammar",
                "step": "TRANSLATE",
                "counter": f"{offset + i}/{total}",
                "prompt": sent.get("english", ""),
                "reveal": sent.get("japanese", ""),
                "tts_text": sent.get("japanese", ""),
                "tts_voice": "ja-JP-NanamiNeural",
            }
        )

    return items


def _build_content(ctx: LessonContext) -> LessonContent:
    """Construct a LessonContent model from the current pipeline context."""
    words = []
    words.extend(ctx.noun_items)
    words.extend(ctx.verb_items)
    return LessonContent(
        lesson_id=ctx.lesson_id,
        theme=ctx.config.theme,
        language=ctx.config.language,
        grammar_ids=[g.id for g in ctx.selected_grammar],
        words=words,
        sentences=ctx.sentences,
        created_at=ctx.created_at
        or (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        ),
    )


def _build_items_by_phase(ctx: LessonContext) -> dict[Phase, list]:
    """Convert pipeline context dicts into typed items grouped by phase."""
    return {
        Phase.NOUNS: ctx.noun_items,
        Phase.VERBS: ctx.verb_items,
        Phase.GRAMMAR: ctx.sentences,
    }


# ---------------------------------------------------------------------------
# Concrete pipeline steps
# ---------------------------------------------------------------------------


class SelectVocabStep(PipelineStep):
    """Step 1 — Load vocab file and select fresh nouns/verbs."""

    name = "select_vocab"
    description = "Pick fresh nouns/verbs from the vocab file"

    def execute(self, ctx: LessonContext) -> LessonContext:
        vocab_dir = Path(__file__).parent.parent / ctx.language_config.vocab_dir
        ctx.vocab = _load_vocab(ctx.config.theme, vocab_dir)
        ctx.nouns, ctx.verbs = suggest_new_vocab(
            ctx.vocab["nouns"],
            ctx.vocab["verbs"],
            covered_nouns=ctx.curriculum.get("covered_nouns", []),
            covered_verbs=ctx.curriculum.get("covered_verbs", []),
            num_nouns=ctx.config.num_nouns,
            num_verbs=ctx.config.num_verbs,
            seed=ctx.config.seed,
        )
        self._log(ctx, f"       nouns : {[n['english'] for n in ctx.nouns]}")
        self._log(ctx, f"       verbs : {[v['english'] for v in ctx.verbs]}")
        return ctx


class GrammarSelectStep(PipelineStep):
    """Step 2 — LLM: select 1-2 grammar points for this lesson."""

    name = "grammar_select"
    description = "LLM: pick 1-2 grammar points for this lesson"

    def execute(self, ctx: LessonContext) -> LessonContext:
        lang_cfg = ctx.language_config
        progression = list(lang_cfg.grammar_progression)
        covered = ctx.curriculum.get("covered_grammar_ids", [])
        unlocked = get_next_grammar_from(progression, covered)
        grammar_map = {g.id: g for g in progression}
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        noun_items = [lang_cfg.generator.convert_raw_noun(n) for n in ctx.nouns]
        verb_items = [lang_cfg.generator.convert_raw_verb(v) for v in ctx.verbs]
        prompt = lang_cfg.prompts.build_grammar_select_prompt(
            unlocked,
            noun_items,
            verb_items,
            lesson_number,
            covered_grammar_ids=covered,
        )
        result = _ask_llm(ctx, prompt)
        selected_ids: list[str] = result.get("selected_ids") or [
            g.id for g in unlocked[:2]
        ]
        ctx.selected_grammar = []
        for gid in selected_ids:
            if gid in grammar_map:
                ctx.selected_grammar.append(grammar_map[gid])
            else:
                self._log(
                    ctx, f"       Warning: unknown grammar id {gid!r}, skipping"
                )
        self._log(
            ctx, f"       selected : {[g.id for g in ctx.selected_grammar]}"
        )
        return ctx


class GenerateSentencesStep(PipelineStep):
    """Step 3 — LLM: generate practice sentences."""

    name = "generate_sentences"
    description = "LLM: produce practice sentences"

    def execute(self, ctx: LessonContext) -> LessonContext:
        noun_items = [ctx.language_config.generator.convert_raw_noun(n) for n in ctx.nouns]
        verb_items = [ctx.language_config.generator.convert_raw_verb(v) for v in ctx.verbs]
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        narrative = (ctx.config.narrative or "").strip()
        if not narrative:
            narrative = ctx.language_config.generator.build_default_narrative(
                theme=ctx.config.theme,
                lesson_number=lesson_number,
            )
        prompt = ctx.language_config.prompts.build_grammar_generate_prompt(
            ctx.selected_grammar,
            noun_items,
            verb_items,
            sentences_per_grammar=ctx.config.sentences_per_grammar,
            narrative=narrative,
        )
        result = _ask_llm(ctx, prompt)
        sentences = result.get("sentences", [])
        ctx.sentences = []
        for s_src in sentences:
            ctx.sentences.append(ctx.language_config.generator.convert_sentence(s_src))
        self._log(ctx, f"       {len(ctx.sentences)} sentences")
        if narrative:
            self._log(ctx, f"       narrative : {narrative[:96]}{'...' if len(narrative) > 96 else ''}")
            ctx.report.add(
                "grammar_context",
                "\n".join(
                    [
                        "## Narrative Context",
                        "",
                        narrative,
                        "",
                    ]
                ),
            )
        if ctx.sentences:
            if ctx.language_config.code == "hun-eng":
                src_lbl, tgt_lbl, ph_lbl, has_phonetic = "Magyar", "English", "Pronunciation", True
            else:
                src_lbl, tgt_lbl, ph_lbl, has_phonetic = "English", "Japanese", "Romaji", True
            ctx.report.add(
                "grammar_practice",
                self._grammar_section(ctx.sentences, src_lbl, tgt_lbl, ph_lbl, has_phonetic),
            )
        return ctx

    @staticmethod
    def _grammar_section(sentences: list[Sentence], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool) -> str:
        header = f"| # | Person | {src_lbl} | {tgt_lbl} |"
        sep = "|---|--------|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        lines: list[str] = ["## Phase 3 \u2014 Grammar Practice", ""]
        by_grammar: dict[str, list[Sentence]] = {}
        for s in sentences:
            by_grammar.setdefault(s.grammar_id, []).append(s)
        for gid, sents in by_grammar.items():
            lines.extend([f"### {gid}", "", header, sep])
            for i, s in enumerate(sents, 1):
                row = (
                    f"| {i} | {s.grammar_parameters.get('person', '')} | {s.source.display_text} | {s.target.display_text} |"
                )
                if has_phonetic and s.target.pronunciation:
                    row += f" {s.target.pronunciation} |"
                lines.append(row)
            lines.append("")
        return "\n".join(lines)


class ReviewSentencesStep(PipelineStep):
    """Step 4 — LLM: rate sentences for naturalness, rewrite awkward ones."""

    name = "review_sentences"
    description = "LLM: review sentence naturalness + rewrite"

    NATURALNESS_THRESHOLD = 3

    def execute(self, ctx: LessonContext) -> LessonContext:
        if not ctx.sentences:
            self._log(ctx, "       (no sentences to review)")
            return ctx

        # Ensure all sentences are Sentence objects
        for i, s in enumerate(ctx.sentences):
            if isinstance(s, dict):
                ctx.sentences[i] = ctx.language_config.generator.convert_sentence(s)

        noun_items = [ctx.language_config.generator.convert_raw_noun(n) for n in ctx.nouns]
        verb_items = [ctx.language_config.generator.convert_raw_verb(v) for v in ctx.verbs]

        prompt = ctx.language_config.prompts.build_sentence_review_prompt(
            ctx.sentences,
            noun_items,
            verb_items,
            ctx.selected_grammar,
        )
        result = _ask_llm(ctx, prompt)
        reviews = result.get("reviews", [])
        revised_count = 0
        for review in reviews:
            idx = review.get("index")
            score = review.get("score", 5)
            revised = review.get("revised_sentence")
            if (
                idx is not None
                and score < self.NATURALNESS_THRESHOLD
                and isinstance(revised, dict)
                and 0 <= idx < len(ctx.sentences)
            ):
                original_en = ctx.sentences[idx].source.display_text
                ctx.sentences[idx] = ctx.language_config.generator.convert_sentence(revised)
                revised_count += 1
                self._log(
                    ctx,
                    f"       [{idx}] score {score} — revised: {original_en!r}",
                )

        overall = result.get("overall_naturalness", "?")
        self._log(
            ctx,
            f"       {len(ctx.sentences)} sentences reviewed "
            f"(naturalness: {overall}/5, revised: {revised_count})",
        )

        if revised_count > 0:
            ctx.report.add(
                "review_notes",
                self._review_section(reviews, revised_count),
            )
        return ctx

    @staticmethod
    def _review_section(reviews: list[dict], revised_count: int) -> str:
        lines = [
            "## Sentence Review",
            "",
            f"> {revised_count} sentence(s) revised for naturalness.",
            "",
        ]
        for r in reviews:
            score = r.get("score", "?")
            issue = r.get("issue")
            if issue:
                lines.append(f"- **[{r.get('index', '?')}]** score {score}: {issue}")
        lines.append("")
        return "\n".join(lines)


class NounPracticeStep(PipelineStep):
    """Step 5 — LLM: enrich nouns with example sentences and memory tips."""

    name = "noun_practice"
    description = "LLM: enrich nouns with examples + memory tips"

    def execute(self, ctx: LessonContext) -> LessonContext:
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        noun_items = [ctx.language_config.generator.convert_raw_noun(n) for n in ctx.nouns]
        result = _ask_llm(ctx, ctx.language_config.prompts.build_noun_practice_prompt(noun_items, lesson_number))
        raw_items = result.get("noun_items", [])
        ctx.noun_items = []
        for n_item in raw_items:
            # Find corresponding source item and merge
            v_src = next((n for n in ctx.nouns if n["english"] == n_item["english"]), None)
            if v_src:
                ctx.noun_items.append(ctx.language_config.generator.convert_noun(n_item, v_src))
            else:
                ctx.noun_items.append(ctx.language_config.generator.convert_noun(n_item, {}))
        if not ctx.noun_items:
            # Fallback: convert ctx.nouns to new format
            for n_src in ctx.nouns:
                ctx.noun_items.append(ctx.language_config.generator.convert_raw_noun(n_src))
        for item in ctx.noun_items:
            item.item_type = "noun"
        self._log(ctx, f"       {len(ctx.noun_items)} noun items")
        if ctx.language_config.code == "hun-eng":
            src_lbl, tgt_lbl, ph_lbl, has_phonetic = "Magyar", "English", "Pronunciation", True
        else:
            src_lbl, tgt_lbl, ph_lbl, has_phonetic = "English", "Japanese", "Romaji", True
        ctx.report.add("vocabulary", self._vocab_table(ctx.noun_items, src_lbl, tgt_lbl, ph_lbl, has_phonetic))
        ctx.report.add("noun_practice", self._practice_section(ctx.noun_items, src_lbl, tgt_lbl, ph_lbl))
        return ctx

    @staticmethod
    def _vocab_table(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool) -> str:
        header = f"| # | {src_lbl} | {tgt_lbl} |"
        sep = "|---|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        lines = ["## Vocabulary", "", "### Nouns", "", header, sep]
        for i, n in enumerate(items, 1):
            row = f"| {i} | {n.source.display_text} | {n.target.display_text} |"
            if has_phonetic and n.target.pronunciation:
                row += f" {n.target.pronunciation} |"
            lines.append(row)
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _practice_section(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str) -> str:
        lines: list[str] = ["## Phase 1 \u2014 Noun Practice", ""]
        for i, n in enumerate(items, 1):
            lines.extend([f"### {i}. {n.source.display_text}", ""])
            lines.append(f"- **{tgt_lbl}:** {n.target.display_text}")
            if n.target.pronunciation:
                lines.append(f"- **{ph_lbl}:** {n.target.pronunciation}")
            if n.target.extra.get("example_sentence_target"):
                lines.append(f"- **Example:** {n.target.extra['example_sentence_target']}")
            if n.target.extra.get("example_sentence_source"):
                lines.append(f"  *{n.target.extra['example_sentence_source']}*")
            if n.target.extra.get("memory_tip"):
                lines.append(f"- **Memory tip:** {n.target.extra['memory_tip']}")
            lines.append("")
        return "\n".join(lines)


class VerbPracticeStep(PipelineStep):
    """Step 6 — LLM: enrich verbs with conjugation forms and memory tips."""

    name = "verb_practice"
    description = "LLM: enrich verbs with conjugations + memory tips"

    def execute(self, ctx: LessonContext) -> LessonContext:
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        verb_items = [ctx.language_config.generator.convert_raw_verb(v) for v in ctx.verbs]
        result = _ask_llm(ctx, ctx.language_config.prompts.build_verb_practice_prompt(verb_items, lesson_number))
        verb_items = result.get("verb_items", [])
        ctx.verb_items = []
        for v_item in verb_items:
            # Find corresponding source item and merge
            v_src = next((v for v in ctx.verbs if v["english"] == v_item["english"]), None)
            if v_src:
                ctx.verb_items.append(ctx.language_config.generator.convert_verb(v_item, v_src))
            else:
                ctx.verb_items.append(ctx.language_config.generator.convert_verb(v_item, {}))
        if not ctx.verb_items:
            # Fallback: convert raw verbs to new format
            for v_src in ctx.verbs:
                ctx.verb_items.append(ctx.language_config.generator.convert_raw_verb(v_src))
        for item in ctx.verb_items:
            item.item_type = "verb"
        self._log(ctx, f"       {len(ctx.verb_items)} verb items")
        if ctx.language_config.code == "hun-eng":
            src_lbl, tgt_lbl, ph_lbl, has_phonetic, has_masu = "Magyar", "English", "Pronunciation", True, False
        else:
            src_lbl, tgt_lbl, ph_lbl, has_phonetic, has_masu = "English", "Japanese", "Romaji", True, True
        ctx.report.add("vocabulary", self._vocab_table(ctx.verb_items, src_lbl, tgt_lbl, ph_lbl, has_phonetic, has_masu))
        ctx.report.add("verb_practice", self._practice_section(ctx.verb_items, src_lbl, tgt_lbl, ph_lbl, has_masu))
        return ctx

    @staticmethod
    def _vocab_table(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool, has_masu: bool) -> str:
        masu_lbl = "Polite form"
        header = f"| # | {src_lbl} | {tgt_lbl} |"
        sep = "|---|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        if has_masu:
            header += f" {masu_lbl} |"
            sep += "-------------|"
        lines = ["### Verbs", "", header, sep]
        for i, v in enumerate(items, 1):
            row = f"| {i} | {v.source.display_text} | {v.target.display_text} |"
            if has_phonetic and v.target.pronunciation:
                row += f" {v.target.pronunciation} |"
            if has_masu and v.target.extra.get("masu_form"):
                row += f" {v.target.extra['masu_form']} |"
            lines.append(row)
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _practice_section(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_masu: bool) -> str:
        lines: list[str] = ["## Phase 2 \u2014 Verb Practice", ""]
        for i, v in enumerate(items, 1):
            lines.extend([f"### {i}. {v.source.display_text}", ""])
            lines.append(f"- **{tgt_lbl}:** {v.target.display_text}")
            if v.target.pronunciation:
                lines.append(f"- **{ph_lbl}:** {v.target.pronunciation}")
            if has_masu and v.target.extra.get("masu_form"):
                lines.append(f"- **Polite form:** {v.target.extra['masu_form']}")
            polite = v.target.extra.get("polite_forms", {})
            if polite:
                for form_name, form_val in polite.items():
                    lines.append(f"  - {form_name}: {form_val}")
            if v.target.extra.get("example_sentence_target"):
                lines.append(f"- **Example:** {v.target.extra['example_sentence_target']}")
            if v.target.extra.get("example_sentence_source"):
                lines.append(f"  *{v.target.extra['example_sentence_source']}*")
            if v.target.extra.get("memory_tip"):
                lines.append(f"- **Memory tip:** {v.target.extra['memory_tip']}")
            lines.append("")
        return "\n".join(lines)


class RegisterLessonStep(PipelineStep):
    """Step 7 — Register and complete the lesson in curriculum.json."""

    name = "register_lesson"
    description = "Add + complete the lesson in curriculum.json"

    def execute(self, ctx: LessonContext) -> LessonContext:
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        lesson = add_lesson(
            ctx.curriculum,
            title=f"Lesson {lesson_number}: {ctx.config.theme.title()}",
            theme=ctx.config.theme,
            nouns=ctx.nouns,
            verbs=ctx.verbs,
            grammar_ids=[g.id for g in ctx.selected_grammar],
            items_count=len(ctx.noun_items) + len(ctx.sentences),
        )
        complete_lesson(ctx.curriculum, lesson["id"])
        ctx.lesson_id = lesson["id"]
        save_curriculum(ctx.curriculum, ctx.config.curriculum_path)
        ctx.created_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        grammar_ids = [g.id for g in ctx.selected_grammar]
        ctx.report.add(
            "header",
            "\n".join(
                [
                    f"# Lesson {ctx.lesson_id}: {ctx.config.theme.title()}",
                    "",
                    f"> Generated: {ctx.created_at}",
                    f"> Grammar: {', '.join(grammar_ids) or '(none)'}",
                    "",
                ]
            ),
        )
        self._log(
            ctx, f"       lesson #{ctx.lesson_id} \u2192 {ctx.config.curriculum_path}"
        )
        return ctx


class PersistContentStep(PipelineStep):
    """Step 8 — Save LessonContent to output/<lesson_id>/content.json."""

    name = "persist_content"
    description = "Save LessonContent to output/<id>/content.json"

    def execute(self, ctx: LessonContext) -> LessonContext:
        content = _build_content(ctx)
        output_dir = _resolve_output_dir(ctx.config)
        ctx.content_path = save_lesson_content(content, output_dir)
        ctx.report.add_artifact("Content JSON", ctx.content_path)
        self._log(ctx, f"       {ctx.content_path}")
        return ctx


class CompileAssetsStep(PipelineStep):
    """Step 9 — Render card images + TTS audio per item (Stage 2)."""

    name = "compile_assets"
    description = "Render card images + TTS audio per item"

    def execute(self, ctx: LessonContext) -> LessonContext:
        from .asset_compiler import compile_assets, compile_assets_sync

        items_by_phase = _build_items_by_phase(ctx)
        profile = get_profile(ctx.config.profile)
        step_info = ctx.step_info
        output_dir = _resolve_output_dir(ctx.config)
        lesson_dir = output_dir / f"lesson_{ctx.lesson_id:03d}"

        total_items = sum(len(v) for v in items_by_phase.values())

        if ctx.config.dry_run:
            self._log(ctx, f"       (dry-run) {total_items} items — cards only")
            ctx.compiled_items = compile_assets_sync(
                items_by_phase, profile, step_info,
                lesson_dir,
                lang_cfg=ctx.language_config,
            )
        else:
            self._log(ctx, f"       {total_items} items → cards + TTS")
            ctx.compiled_items = asyncio.run(
                compile_assets(items_by_phase, profile, ctx.step_info, lesson_dir,
                               lang_cfg=ctx.language_config)
            )

        self._log(ctx, f"       {len(ctx.compiled_items)} compiled items")
        return ctx


class CompileTouchesStep(PipelineStep):
    """Step 10 — Profile-driven touch sequencing (Stage 3)."""

    name = "compile_touches"
    description = "Profile-driven touch sequencing"

    def execute(self, ctx: LessonContext) -> LessonContext:
        from .touch_compiler import compile_touches

        profile = get_profile(ctx.config.profile)
        ctx.touches = compile_touches(ctx.compiled_items, profile)
        self._log(
            ctx,
            f"       {len(ctx.touches)} touches "
            f"(profile: {ctx.config.profile})",
        )
        return ctx


class RenderVideoStep(PipelineStep):
    """Step 11 — Assemble MP4 from touch sequence."""

    name = "render_video"
    description = "Assemble MP4 from touch sequence"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if not ctx.config.render_video or ctx.config.dry_run:
            reason = "dry-run" if ctx.config.dry_run else "skipped"
            self._log(ctx, f"       ({reason})")
            return ctx

        from .video.builder import VideoBuilder

        output_dir = _resolve_output_dir(ctx.config)
        video_path = (
            output_dir / f"lesson_{ctx.lesson_id:03d}_{ctx.config.theme}.mp4"
        )

        video_builder = VideoBuilder()
        clips = []
        for touch in ctx.touches:
            card_path = touch.artifacts.get("card")
            if card_path is None or not card_path.exists():
                continue
            audio_paths = touch.artifacts.get("audio") or []
            clip = video_builder.create_multi_audio_clip(
                card_path, audio_paths,
            )
            clips.append(clip)

        self._log(ctx, f"       {len(clips)} clips → {video_path.name}")

        if clips:
            video_builder.build_video(clips, video_path, method="ffmpeg")
            ctx.video_path = video_path
            size_kb = video_path.stat().st_size // 1024
            self._log(ctx, f"       OK  ({size_kb} KB)")
            ctx.report.add_artifact("Video", video_path)

        lesson_dir = output_dir / f"lesson_{ctx.lesson_id:03d}"
        cards_dir = lesson_dir / "cards"
        audio_dir = lesson_dir / "audio"
        if cards_dir.exists():
            ctx.report.add_artifact("Cards", cards_dir)
        if audio_dir.exists():
            ctx.report.add_artifact("Audio", audio_dir)
        return ctx


class SaveReportStep(PipelineStep):
    """Step 12 — Finalize and save Markdown lesson report."""

    name = "save_report"
    description = "Finalize and save Markdown lesson report"

    def execute(self, ctx: LessonContext) -> LessonContext:
        ctx.report.add("summary", self._summary(ctx))
        report = ctx.report.render()
        output_dir = _resolve_output_dir(ctx.config)
        report_path = output_dir / f"lesson_{ctx.lesson_id:03d}" / "report.md"
        ctx.report_path = save_report(report, report_path)
        self._log(ctx, f"       {ctx.report_path}")
        return ctx

    @staticmethod
    def _summary(ctx: LessonContext) -> str:
        from .touch_compiler import count_touches

        n_nouns = len(ctx.noun_items)
        n_verbs = len(ctx.verb_items)
        n_sentences = len(ctx.sentences)
        total = n_nouns + n_verbs + n_sentences
        profile = get_profile(ctx.config.profile)
        counts = count_touches(n_nouns, n_verbs, n_sentences, profile)
        noun_reps = len(profile.cycle_for(Phase.NOUNS))
        verb_reps = len(profile.cycle_for(Phase.VERBS))
        grammar_reps = len(profile.cycle_for(Phase.GRAMMAR))
        lines = [
            "## Summary",
            "",
            f"> Profile: **{ctx.config.profile}**",
            "",
            "| Phase | Items | Repetitions | Touches |",
            "|-------|-------|-------------|---------|",
            f"| Nouns | {n_nouns} | {noun_reps} | {counts['nouns']} |",
            f"| Verbs | {n_verbs} | {verb_reps} | {counts['verbs']} |",
            f"| Grammar | {n_sentences} | {grammar_reps} | {counts['grammar']} |",
            f"| **Total** | **{total}** | | **{counts['total']}** |",
            "",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

PIPELINE: list[PipelineStep] = [
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

    Loads the curriculum from config.curriculum_path, executes all twelve
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
