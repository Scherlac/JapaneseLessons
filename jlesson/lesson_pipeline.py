"""
Lesson generation pipeline.

Orchestrates the full lesson workflow through nine sequential steps:

  step 1  select_vocab       — pick fresh nouns/verbs from the vocab file
  step 2  grammar_select     — LLM: pick 1-2 grammar points for this lesson
  step 3  generate_sentences — LLM: produce practice sentences
  step 4  noun_practice      — LLM: enrich nouns with examples + memory tips
  step 5  verb_practice      — LLM: enrich verbs with conjugations + memory tips
  step 6  register_lesson    — add+complete the lesson in curriculum.json
  step 7  persist_content    — save LessonContent to output/<id>/content.json
  step 8  render_video       — TTS audio + card images + assembled MP4
  step 9  save_report        — finalize and save Markdown lesson report

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
    load_curriculum,
    save_curriculum,
    suggest_new_vocab,
)
from .lesson_report import ReportBuilder, save_report
from .lesson_store import save_lesson_content
from .llm_client import ask_llm_json_free
from .models import LessonContent, NounItem, Sentence, VerbItem
from .prompt_template import (
    build_grammar_generate_prompt,
    build_grammar_select_prompt,
    build_noun_practice_prompt,
    build_verb_practice_prompt,
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
    selected_grammar: list[dict] = field(default_factory=list)
    sentences: list[dict] = field(default_factory=list)
    noun_items: list[dict] = field(default_factory=list)
    verb_items: list[dict] = field(default_factory=list)
    lesson_id: int = 0
    created_at: str = ""
    content_path: Path | None = None
    video_path: Path | None = None
    report_path: Path | None = None


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


def _load_vocab(theme: str) -> dict:
    """Load vocab file; generate via LLM if missing."""
    path = _VOCAB_DIR / f"{theme}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    print(f"  [vocab] {theme}.json not found — generating via LLM...")
    from .vocab_generator import generate_vocab

    return generate_vocab(theme=theme, num_nouns=12, num_verbs=10, output_dir=_VOCAB_DIR)


def _ask_llm(ctx: LessonContext, prompt: str) -> dict:
    """Route LLM call through cache when use_cache is enabled."""
    if ctx.config.use_cache:
        from .llm_cache import ask_llm_cached

        return ask_llm_cached(prompt)
    return ask_llm_json_free(prompt)


def _resolve_output_dir(config: LessonConfig) -> Path:
    if config.output_dir is not None:
        return Path(config.output_dir)
    return Path(__file__).parent.parent / "output"


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
    return LessonContent(
        lesson_id=ctx.lesson_id,
        theme=ctx.config.theme,
        grammar_ids=[g["id"] for g in ctx.selected_grammar],
        noun_items=[NounItem.model_validate(n) for n in ctx.noun_items],
        verb_items=[VerbItem.model_validate(v) for v in ctx.verb_items],
        sentences=[Sentence.model_validate(s) for s in ctx.sentences],
        created_at=ctx.created_at
        or (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        ),
    )


async def _render_async(
    items: list[dict],
    video_path: Path,
    cards_dir: Path,
    audio_dir: Path,
    report: ReportBuilder | None = None,
) -> None:
    """Async TTS + card + video assembly."""
    from .video.builder import VideoBuilder
    from .video.cards import CardRenderer
    from .video.tts_engine import create_engine

    cards_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    card_renderer = CardRenderer()
    video_builder = VideoBuilder()
    total = len(items)

    # TTS audio — rate-limited to avoid overwhelming Edge TTS
    audio_paths: list[Path] = []
    for i, item in enumerate(items):
        voice_key = "japanese_female"
        tts_voice = item.get("tts_voice", "")
        if "Aria" in tts_voice:
            voice_key = "english_female"
        if "Keita" in tts_voice:
            voice_key = "japanese_male"
        engine = create_engine(voice_key, rate="-20%")
        audio_path = audio_dir / f"audio_{i + 1:03d}.mp3"
        for attempt in range(3):
            try:
                await engine.generate_audio(item["tts_text"], audio_path)
                break
            except Exception as exc:
                if attempt < 2:
                    print(f"    TTS retry {attempt + 1}: {exc}")
                    await asyncio.sleep(2**attempt)
                else:
                    raise
        audio_paths.append(audio_path)
        await asyncio.sleep(1.0)

    if report:
        report.add(
            "render_details",
            "\n".join(
                ["## Render Details", "", f"- **TTS audio:** {len(audio_paths)} files"]
            ),
        )

    # Card images
    for i, item in enumerate(items):
        progress = (i + 1) / total
        if item["step"] == "INTRODUCE":
            card = card_renderer.render_introduce_card(
                english=item["prompt"],
                japanese=item["reveal"],
                kana="",
                romaji="",
                step_label=item["counter"],
                progress=progress,
            )
        else:
            card = card_renderer.render_translate_card(
                english=item["prompt"],
                japanese=item["reveal"],
                romaji="",
                context=item["phase"].lower(),
                step_label=item["counter"],
                progress=progress,
            )
        card_renderer.save_card(card, cards_dir / f"{i + 1:03d}.png")

    if report:
        report.add("render_details", f"- **Card images:** {total}")

    # Assemble MP4
    clips = [
        video_builder.create_clip(cards_dir / f"{i + 1:03d}.png", audio_paths[i])
        for i in range(total)
    ]
    video_builder.build_video(clips, video_path, method="ffmpeg")

    if report:
        report.add("render_details", f"- **Video:** {video_path.name}")
        report.add("render_details", "")


# ---------------------------------------------------------------------------
# Concrete pipeline steps
# ---------------------------------------------------------------------------


class SelectVocabStep(PipelineStep):
    """Step 1 — Load vocab file and select fresh nouns/verbs."""

    name = "select_vocab"
    description = "Pick fresh nouns/verbs from the vocab file"

    def execute(self, ctx: LessonContext) -> LessonContext:
        ctx.vocab = _load_vocab(ctx.config.theme)
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
        unlocked = get_next_grammar(ctx.curriculum.get("covered_grammar_ids", []))
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        result = _ask_llm(
            ctx,
            build_grammar_select_prompt(
                unlocked,
                ctx.nouns,
                ctx.verbs,
                lesson_number,
                covered_grammar_ids=ctx.curriculum.get("covered_grammar_ids", []),
            ),
        )
        selected_ids: list[str] = result.get("selected_ids") or [
            g["id"] for g in unlocked[:2]
        ]
        ctx.selected_grammar = []
        for gid in selected_ids:
            try:
                ctx.selected_grammar.append(get_grammar_by_id(gid))
            except KeyError:
                self._log(
                    ctx, f"       Warning: unknown grammar id {gid!r}, skipping"
                )
        self._log(
            ctx, f"       selected : {[g['id'] for g in ctx.selected_grammar]}"
        )
        return ctx


class GenerateSentencesStep(PipelineStep):
    """Step 3 — LLM: generate practice sentences."""

    name = "generate_sentences"
    description = "LLM: produce practice sentences"

    def execute(self, ctx: LessonContext) -> LessonContext:
        result = _ask_llm(
            ctx,
            build_grammar_generate_prompt(
                ctx.selected_grammar,
                ctx.nouns,
                ctx.verbs,
                sentences_per_grammar=ctx.config.sentences_per_grammar,
            ),
        )
        ctx.sentences = result.get("sentences", [])
        self._log(ctx, f"       {len(ctx.sentences)} sentences")
        if ctx.sentences:
            ctx.report.add(
                "grammar_practice", self._grammar_section(ctx.sentences)
            )
        return ctx

    @staticmethod
    def _grammar_section(sentences: list[dict]) -> str:
        lines: list[str] = ["## Phase 3 \u2014 Grammar Practice", ""]
        by_grammar: dict[str, list[dict]] = {}
        for s in sentences:
            by_grammar.setdefault(s.get("grammar_id", ""), []).append(s)
        for gid, sents in by_grammar.items():
            lines.extend(
                [
                    f"### {gid}",
                    "",
                    "| # | Person | English | Japanese | Romaji |",
                    "|---|--------|---------|----------|--------|",
                ]
            )
            for i, s in enumerate(sents, 1):
                lines.append(
                    f"| {i} | {s.get('person', '')} | {s.get('english', '')} "
                    f"| {s.get('japanese', '')} | {s.get('romaji', '')} |"
                )
            lines.append("")
        return "\n".join(lines)


class NounPracticeStep(PipelineStep):
    """Step 4 — LLM: enrich nouns with example sentences and memory tips."""

    name = "noun_practice"
    description = "LLM: enrich nouns with examples + memory tips"

    def execute(self, ctx: LessonContext) -> LessonContext:
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        result = _ask_llm(ctx, build_noun_practice_prompt(ctx.nouns, lesson_number))
        ctx.noun_items = result.get("noun_items", [])
        for n_item, n_src in zip(ctx.noun_items, ctx.nouns):
            n_item.setdefault("english", n_src["english"])
            n_item.setdefault("japanese", n_src["japanese"])
            n_item.setdefault("kanji", n_src.get("kanji", n_src["japanese"]))
            n_item.setdefault("romaji", n_src["romaji"])
        if not ctx.noun_items:
            ctx.noun_items = [dict(n) for n in ctx.nouns]
        self._log(ctx, f"       {len(ctx.noun_items)} noun items")
        ctx.report.add("vocabulary", self._vocab_table(ctx.noun_items))
        ctx.report.add("noun_practice", self._practice_section(ctx.noun_items))
        return ctx

    @staticmethod
    def _vocab_table(items: list[dict]) -> str:
        lines = [
            "## Vocabulary",
            "",
            "### Nouns",
            "",
            "| # | English | Japanese | Romaji |",
            "|---|---------|----------|--------|",
        ]
        for i, n in enumerate(items, 1):
            lines.append(
                f"| {i} | {n.get('english', '')} | {n.get('japanese', '')} "
                f"| {n.get('romaji', '')} |"
            )
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _practice_section(items: list[dict]) -> str:
        lines: list[str] = ["## Phase 1 \u2014 Noun Practice", ""]
        for i, n in enumerate(items, 1):
            lines.extend([f"### {i}. {n.get('english', '')}", ""])
            lines.append(f"- **Japanese:** {n.get('japanese', '')}")
            lines.append(f"- **Romaji:** {n.get('romaji', '')}")
            if n.get("example_sentence_jp"):
                lines.append(f"- **Example:** {n['example_sentence_jp']}")
            if n.get("example_sentence_en"):
                lines.append(f"  *{n['example_sentence_en']}*")
            if n.get("memory_tip"):
                lines.append(f"- **Memory tip:** {n['memory_tip']}")
            lines.append("")
        return "\n".join(lines)


class VerbPracticeStep(PipelineStep):
    """Step 5 — LLM: enrich verbs with conjugation forms and memory tips."""

    name = "verb_practice"
    description = "LLM: enrich verbs with conjugations + memory tips"

    def execute(self, ctx: LessonContext) -> LessonContext:
        lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
        result = _ask_llm(ctx, build_verb_practice_prompt(ctx.verbs, lesson_number))
        ctx.verb_items = result.get("verb_items", [])
        for v_item, v_src in zip(ctx.verb_items, ctx.verbs):
            v_item.setdefault("english", v_src["english"])
            v_item.setdefault("japanese", v_src["japanese"])
            v_item.setdefault("kanji", v_src.get("kanji", v_src["japanese"]))
            v_item.setdefault("romaji", v_src["romaji"])
            v_item.setdefault("masu_form", v_src["masu_form"])
        if not ctx.verb_items:
            ctx.verb_items = [dict(v) for v in ctx.verbs]
        self._log(ctx, f"       {len(ctx.verb_items)} verb items")
        ctx.report.add("vocabulary", self._vocab_table(ctx.verb_items))
        ctx.report.add("verb_practice", self._practice_section(ctx.verb_items))
        return ctx

    @staticmethod
    def _vocab_table(items: list[dict]) -> str:
        lines = [
            "### Verbs",
            "",
            "| # | English | Japanese | Romaji | Polite form |",
            "|---|---------|----------|--------|-------------|",
        ]
        for i, v in enumerate(items, 1):
            lines.append(
                f"| {i} | {v.get('english', '')} | {v.get('japanese', '')} "
                f"| {v.get('romaji', '')} | {v.get('masu_form', '')} |"
            )
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _practice_section(items: list[dict]) -> str:
        lines: list[str] = ["## Phase 2 \u2014 Verb Practice", ""]
        for i, v in enumerate(items, 1):
            lines.extend([f"### {i}. {v.get('english', '')}", ""])
            lines.append(f"- **Japanese:** {v.get('japanese', '')}")
            lines.append(f"- **Romaji:** {v.get('romaji', '')}")
            lines.append(f"- **Polite form:** {v.get('masu_form', '')}")
            polite = v.get("polite_forms", {})
            if polite:
                for form_name, form_val in polite.items():
                    lines.append(f"  - {form_name}: {form_val}")
            if v.get("example_sentence_jp"):
                lines.append(f"- **Example:** {v['example_sentence_jp']}")
            if v.get("example_sentence_en"):
                lines.append(f"  *{v['example_sentence_en']}*")
            if v.get("memory_tip"):
                lines.append(f"- **Memory tip:** {v['memory_tip']}")
            lines.append("")
        return "\n".join(lines)


class RegisterLessonStep(PipelineStep):
    """Step 6 — Register and complete the lesson in curriculum.json."""

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
            grammar_ids=[g["id"] for g in ctx.selected_grammar],
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
        grammar_ids = [g["id"] for g in ctx.selected_grammar]
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
    """Step 7 — Save LessonContent to output/<lesson_id>/content.json."""

    name = "persist_content"
    description = "Save LessonContent to output/<id>/content.json"

    def execute(self, ctx: LessonContext) -> LessonContext:
        content = _build_content(ctx)
        output_dir = _resolve_output_dir(ctx.config)
        ctx.content_path = save_lesson_content(content, output_dir)
        ctx.report.add_artifact("Content JSON", ctx.content_path)
        self._log(ctx, f"       {ctx.content_path}")
        return ctx


class RenderVideoStep(PipelineStep):
    """Step 8 — Render TTS audio + visual card PNGs + assembled MP4."""

    name = "render_video"
    description = "TTS audio + card images + assembled MP4"

    def execute(self, ctx: LessonContext) -> LessonContext:
        if not ctx.config.render_video or ctx.config.dry_run:
            reason = "dry-run" if ctx.config.dry_run else "skipped"
            self._log(ctx, f"       ({reason})")
            return ctx

        output_dir = _resolve_output_dir(ctx.config)
        lesson_dir = output_dir / f"lesson_{ctx.lesson_id:03d}"
        video_path = (
            output_dir / f"lesson_{ctx.lesson_id:03d}_{ctx.config.theme}.mp4"
        )
        items = _build_video_items(ctx.noun_items, ctx.sentences)
        self._log(ctx, f"       {len(items)} cards \u2192 {video_path.name}")

        asyncio.run(
            _render_async(
                items,
                video_path,
                lesson_dir / "cards",
                lesson_dir / "audio",
                report=ctx.report,
            )
        )
        ctx.video_path = video_path
        size_kb = video_path.stat().st_size // 1024
        self._log(ctx, f"       OK  ({size_kb} KB)")

        ctx.report.add_artifact("Video", video_path)
        cards_dir = lesson_dir / "cards"
        audio_dir = lesson_dir / "audio"
        if cards_dir.exists():
            ctx.report.add_artifact("Cards", cards_dir)
        if audio_dir.exists():
            ctx.report.add_artifact("Audio", audio_dir)
        return ctx


class SaveReportStep(PipelineStep):
    """Step 9 — Finalize and save Markdown lesson report."""

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
        n_nouns = len(ctx.noun_items)
        n_verbs = len(ctx.verb_items)
        n_sentences = len(ctx.sentences)
        total = n_nouns + n_verbs + n_sentences
        total_touches = n_nouns * 5 + n_verbs * 5 + n_sentences * 3
        lines = [
            "## Summary",
            "",
            "| Phase | Items | Repetitions | Touches |",
            "|-------|-------|-------------|---------|",
            f"| Nouns | {n_nouns} | 5 | {n_nouns * 5} |",
            f"| Verbs | {n_verbs} | 5 | {n_verbs * 5} |",
            f"| Grammar | {n_sentences} | 3 | {n_sentences * 3} |",
            f"| **Total** | **{total}** | | **{total_touches}** |",
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
    NounPracticeStep(),
    VerbPracticeStep(),
    RegisterLessonStep(),
    PersistContentStep(),
    RenderVideoStep(),
    SaveReportStep(),
]


def run_pipeline(config: LessonConfig) -> LessonContext:
    """Run the full lesson generation pipeline.

    Loads the curriculum from config.curriculum_path, executes all nine
    steps in sequence, and returns the completed LessonContext.
    """
    ctx = LessonContext(config=config)
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
