"""
Lesson generation pipeline.

Orchestrates the full lesson workflow through eight sequential stages:

  stage 1  select_vocab      — pick fresh nouns/verbs from the vocab file
  stage 2  grammar_select    — LLM: pick 1-2 grammar points for this lesson
  stage 3  generate_sentences — LLM: produce practice sentences
  stage 4  noun_practice     — LLM: enrich nouns with examples + memory tips
  stage 5  verb_practice     — LLM: enrich verbs with conjugations + memory tips
  stage 6  register_lesson   — add+complete the lesson in curriculum.json
  stage 7  persist_content   — save LessonContent to output/<id>/content.json
  stage 8  render_video      — TTS audio + card images + assembled MP4

Each stage is a pure function `stage(ctx) -> ctx`, making them individually
testable and easy to extend without touching the others.

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
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .curriculum import (
    add_lesson,
    complete_lesson,
    get_grammar_by_id,
    get_next_grammar,
    load_curriculum,
    save_curriculum,
    suggest_new_vocab,
)
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
    verbose: bool = True


# ---------------------------------------------------------------------------
# Pipeline context
# ---------------------------------------------------------------------------

@dataclass
class LessonContext:
    """Mutable state accumulated across pipeline stages."""

    config: LessonConfig
    curriculum: dict = field(default_factory=dict)
    vocab: dict = field(default_factory=dict)
    nouns: list[dict] = field(default_factory=list)
    verbs: list[dict] = field(default_factory=list)
    selected_grammar: list[dict] = field(default_factory=list)
    sentences: list[dict] = field(default_factory=list)
    noun_items: list[dict] = field(default_factory=list)
    verb_items: list[dict] = field(default_factory=list)
    lesson_id: int = 0
    content_path: Path | None = None
    video_path: Path | None = None


def _log(ctx: LessonContext, msg: str) -> None:
    if ctx.config.verbose:
        print(msg)


def _ask_llm(ctx: LessonContext, prompt: str) -> dict:
    """Route LLM call through cache when use_cache is enabled."""
    if ctx.config.use_cache:
        from .llm_cache import ask_llm_cached
        return ask_llm_cached(prompt)
    return ask_llm_json_free(prompt)


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
        items.append({
            "phase":     "Nouns",
            "step":      "INTRODUCE",
            "counter":   f"{i}/{total}",
            "prompt":    noun.get("english", ""),
            "reveal":    reveal,
            "tts_text":  jp,
            "tts_voice": "ja-JP-NanamiNeural",
        })

    offset = len(noun_items)
    for i, sent in enumerate(sentences, 1):
        items.append({
            "phase":     "Grammar",
            "step":      "TRANSLATE",
            "counter":   f"{offset + i}/{total}",
            "prompt":    sent.get("english", ""),
            "reveal":    sent.get("japanese", ""),
            "tts_text":  sent.get("japanese", ""),
            "tts_voice": "ja-JP-NanamiNeural",
        })

    return items


# ---------------------------------------------------------------------------
# Stage functions
# ---------------------------------------------------------------------------

def stage_select_vocab(ctx: LessonContext) -> LessonContext:
    """Stage 1 — Load vocab file and select fresh nouns/verbs."""
    _log(ctx, "\n  [1/8] Select vocab")
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
    _log(ctx, f"       nouns : {[n['english'] for n in ctx.nouns]}")
    _log(ctx, f"       verbs : {[v['english'] for v in ctx.verbs]}")
    return ctx


def stage_grammar_select(ctx: LessonContext) -> LessonContext:
    """Stage 2 — LLM: select 1-2 grammar points appropriate for this lesson."""
    _log(ctx, "\n  [2/8] Grammar select (LLM)...")
    unlocked = get_next_grammar(ctx.curriculum.get("covered_grammar_ids", []))
    lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
    t0 = time.time()
    result = _ask_llm(ctx, build_grammar_select_prompt(
        unlocked, ctx.nouns, ctx.verbs, lesson_number,
        covered_grammar_ids=ctx.curriculum.get("covered_grammar_ids", []),
    ))
    selected_ids: list[str] = result.get("selected_ids") or [g["id"] for g in unlocked[:2]]
    _log(ctx, f"       selected : {selected_ids}  ({time.time() - t0:.1f}s)")
    ctx.selected_grammar = []
    for gid in selected_ids:
        try:
            ctx.selected_grammar.append(get_grammar_by_id(gid))
        except KeyError:
            _log(ctx, f"       Warning: unknown grammar id {gid!r}, skipping")
    return ctx


def stage_generate_sentences(ctx: LessonContext) -> LessonContext:
    """Stage 3 — LLM: generate practice sentences for the selected grammar."""
    _log(ctx, "\n  [3/8] Generate sentences (LLM)...")
    t0 = time.time()
    result = _ask_llm(ctx, build_grammar_generate_prompt(
        ctx.selected_grammar, ctx.nouns, ctx.verbs,
        sentences_per_grammar=ctx.config.sentences_per_grammar,
    ))
    ctx.sentences = result.get("sentences", [])
    _log(ctx, f"       {len(ctx.sentences)} sentences  ({time.time() - t0:.1f}s)")
    return ctx


def stage_noun_practice(ctx: LessonContext) -> LessonContext:
    """Stage 4 — LLM: enrich nouns with example sentences and memory tips."""
    _log(ctx, "\n  [4/8] Noun practice (LLM)...")
    lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
    t0 = time.time()
    result = _ask_llm(ctx, build_noun_practice_prompt(ctx.nouns, lesson_number))
    ctx.noun_items = result.get("noun_items", [])
    # Fill in required fields the LLM may have omitted
    for n_item, n_src in zip(ctx.noun_items, ctx.nouns):
        n_item.setdefault("english",  n_src["english"])
        n_item.setdefault("japanese", n_src["japanese"])
        n_item.setdefault("kanji",    n_src.get("kanji", n_src["japanese"]))
        n_item.setdefault("romaji",   n_src["romaji"])
    if not ctx.noun_items:
        ctx.noun_items = [dict(n) for n in ctx.nouns]
    _log(ctx, f"       {len(ctx.noun_items)} noun items  ({time.time() - t0:.1f}s)")
    return ctx


def stage_verb_practice(ctx: LessonContext) -> LessonContext:
    """Stage 5 — LLM: enrich verbs with conjugation forms and memory tips."""
    _log(ctx, "\n  [5/8] Verb practice (LLM)...")
    lesson_number = len(ctx.curriculum.get("lessons", [])) + 1
    t0 = time.time()
    result = _ask_llm(ctx, build_verb_practice_prompt(ctx.verbs, lesson_number))
    ctx.verb_items = result.get("verb_items", [])
    # Fill in required fields the LLM may have omitted
    for v_item, v_src in zip(ctx.verb_items, ctx.verbs):
        v_item.setdefault("english",   v_src["english"])
        v_item.setdefault("japanese",  v_src["japanese"])
        v_item.setdefault("kanji",     v_src.get("kanji", v_src["japanese"]))
        v_item.setdefault("romaji",    v_src["romaji"])
        v_item.setdefault("masu_form", v_src["masu_form"])
    if not ctx.verb_items:
        ctx.verb_items = [dict(v) for v in ctx.verbs]
    _log(ctx, f"       {len(ctx.verb_items)} verb items  ({time.time() - t0:.1f}s)")
    return ctx


def stage_register_lesson(ctx: LessonContext) -> LessonContext:
    """Stage 6 — Register and complete the lesson in curriculum.json."""
    _log(ctx, "\n  [6/8] Register lesson")
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
    _log(ctx, f"       lesson #{ctx.lesson_id} → {ctx.config.curriculum_path}")
    return ctx


def stage_persist_content(ctx: LessonContext) -> LessonContext:
    """Stage 7 — Save LessonContent to output/<lesson_id>/content.json."""
    _log(ctx, "\n  [7/8] Persist lesson content")
    content = LessonContent(
        lesson_id=ctx.lesson_id,
        theme=ctx.config.theme,
        grammar_ids=[g["id"] for g in ctx.selected_grammar],
        noun_items=[NounItem.model_validate(n) for n in ctx.noun_items],
        verb_items=[VerbItem.model_validate(v) for v in ctx.verb_items],
        sentences=[Sentence.model_validate(s) for s in ctx.sentences],
        created_at=datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    )
    output_dir = _resolve_output_dir(ctx.config)
    ctx.content_path = save_lesson_content(content, output_dir)
    _log(ctx, f"       {ctx.content_path}")
    return ctx


def stage_render_video(ctx: LessonContext) -> LessonContext:
    """Stage 8 — Render TTS audio + visual card PNGs + assembled MP4."""
    if not ctx.config.render_video:
        _log(ctx, "\n  [8/8] Render video (skipped)")
        return ctx
    _log(ctx, "\n  [8/8] Render video")
    output_dir = _resolve_output_dir(ctx.config)
    lesson_dir = output_dir / f"lesson_{ctx.lesson_id:03d}"
    video_path = output_dir / f"lesson_{ctx.lesson_id:03d}_{ctx.config.theme}.mp4"
    items = _build_video_items(ctx.noun_items, ctx.sentences)
    _log(ctx, f"       {len(items)} cards → {video_path.name}")
    asyncio.run(_render_async(
        items, video_path,
        lesson_dir / "cards",
        lesson_dir / "audio",
    ))
    ctx.video_path = video_path
    size_kb = video_path.stat().st_size // 1024
    _log(ctx, f"       OK  ({size_kb} KB)")
    return ctx


async def _render_async(
    items: list[dict],
    video_path: Path,
    cards_dir: Path,
    audio_dir: Path,
) -> None:
    """Async implementation of the TTS + card + video assembly step."""
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
        if "Aria"  in tts_voice:
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
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
        audio_paths.append(audio_path)
        await asyncio.sleep(1.0)

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

    # Assemble MP4
    clips = [
        video_builder.create_clip(cards_dir / f"{i + 1:03d}.png", audio_paths[i])
        for i in range(total)
    ]
    video_builder.build_video(clips, video_path, method="ffmpeg")


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

PIPELINE: list[Callable[[LessonContext], LessonContext]] = [
    stage_select_vocab,
    stage_grammar_select,
    stage_generate_sentences,
    stage_noun_practice,
    stage_verb_practice,
    stage_register_lesson,
    stage_persist_content,
    stage_render_video,
]


def run_pipeline(config: LessonConfig) -> LessonContext:
    """Run the full lesson generation pipeline.

    Loads the curriculum from config.curriculum_path, executes all eight
    stages in sequence, and returns the completed LessonContext.
    """
    ctx = LessonContext(config=config)
    ctx.curriculum = load_curriculum(config.curriculum_path)

    print(f"\n{'=' * 60}")
    print(f"  LESSON: {config.theme.upper()}")
    print(f"{'=' * 60}")

    t_total = time.time()
    for stage in PIPELINE:
        ctx = stage(ctx)

    elapsed = time.time() - t_total
    print(f"\n  Done — {elapsed:.0f}s")
    if ctx.video_path and ctx.video_path.exists():
        print(f"  Video   : {ctx.video_path}")
    if ctx.content_path:
        print(f"  Content : {ctx.content_path}")

    return ctx
