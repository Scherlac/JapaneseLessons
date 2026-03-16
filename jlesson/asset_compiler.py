"""
Asset compiler — Stage 2 of the compilation pipeline.

Takes a list of lesson items (NounItem, VerbItem, Sentence) grouped by phase,
determines which assets are needed based on the selected profile, and renders
card images + TTS audio for each item.

Produces a list of CompiledItem objects with populated asset paths.

Usage:
    from jlesson.asset_compiler import compile_assets
    compiled = await compile_assets(items_by_phase, profile, output_dir)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .models import (
    CompiledItem,
    ItemAssets,
    LessonItem,
    NounItem,
    Phase,
    Sentence,
    VerbItem,
)
from .profiles import Profile


# ---------------------------------------------------------------------------
# Text extraction helpers (legacy — used when no lang_cfg is provided)
# ---------------------------------------------------------------------------


def _english_text(item: LessonItem) -> str:
    return item.english


def _japanese_text(item: LessonItem) -> str:
    return item.japanese


def _kana_text(item: LessonItem) -> str:
    if isinstance(item, (NounItem, VerbItem)):
        return item.japanese
    return ""


def _romaji_text(item: LessonItem) -> str:
    return item.romaji


# ---------------------------------------------------------------------------
# Card rendering
# ---------------------------------------------------------------------------


def _render_item_cards(
    item: LessonItem,
    required: set[str],
    cards_dir: Path,
    item_index: int,
    renderer,
    lang_cfg=None,
) -> dict[str, Path]:
    """Render the card images needed for *item* and return asset-key → path.

    When *lang_cfg* is provided its :class:`~jlesson.language_config.FieldMap`
    is used for language-agnostic text extraction and the correct card renderer
    method is selected for the language.  Falls back to the Japanese-specific
    renderer methods when *lang_cfg* is ``None``.
    """
    paths: dict[str, Path] = {}

    if lang_cfg is not None:
        v = lang_cfg.field_map.view(item)
        source = v["source"]
        target = v["target"]
        phonetic = v["target_phonetic"]
        is_japanese = lang_cfg.code == "eng-jap"
        kana = target if is_japanese and isinstance(item, (NounItem, VerbItem)) else ""
    else:
        source = _english_text(item)
        target = _japanese_text(item)
        kana = _kana_text(item)
        phonetic = _romaji_text(item)
        is_japanese = True

    if is_japanese:
        if "card_en" in required:
            path = cards_dir / f"{item_index:03d}_en.png"
            card = renderer.render_en_card(english=source)
            renderer.save_card(card, path)
            paths["card_en"] = path

        if "card_jp" in required:
            path = cards_dir / f"{item_index:03d}_jp.png"
            card = renderer.render_jp_card(japanese=target, kana=kana, romaji=phonetic)
            renderer.save_card(card, path)
            paths["card_jp"] = path

        if "card_en_jp" in required:
            path = cards_dir / f"{item_index:03d}_en_jp.png"
            card = renderer.render_bilingual_card(
                english=source, japanese=target, kana=kana, romaji=phonetic,
            )
            renderer.save_card(card, path)
            paths["card_en_jp"] = path
    else:
        # Non-Japanese language pair (e.g. hun-eng):
        #   card_en   → source-language prompt  (e.g. Hungarian word)
        #   card_jp   → target-language reveal  (e.g. English word)
        #   card_en_jp → bilingual card (target prominent, source below)
        if "card_en" in required:
            path = cards_dir / f"{item_index:03d}_en.png"
            card = renderer.render_hun_card(hungarian=source, pronunciation=phonetic)
            renderer.save_card(card, path)
            paths["card_en"] = path

        if "card_jp" in required:
            path = cards_dir / f"{item_index:03d}_jp.png"
            card = renderer.render_en_card(english=target)
            renderer.save_card(card, path)
            paths["card_jp"] = path

        if "card_en_jp" in required:
            path = cards_dir / f"{item_index:03d}_en_jp.png"
            card = renderer.render_hun_bilingual_card(
                english=target, hungarian=source, pronunciation=phonetic,
            )
            renderer.save_card(card, path)
            paths["card_en_jp"] = path

    return paths


# ---------------------------------------------------------------------------
# TTS rendering
# ---------------------------------------------------------------------------


async def _render_item_audio(
    item: LessonItem,
    required: set[str],
    audio_dir: Path,
    item_index: int,
    create_engine_fn,
    lang_cfg=None,
) -> dict[str, Path]:
    """Generate TTS audio files needed for *item* and return asset-key → path.

    When *lang_cfg* is provided, audio_jp_f / audio_jp_m asset keys are routed
    to the correct target-language voices for the language pair.  For eng-jap
    this means Japanese voices; for hun-eng this means English voices.
    """
    paths: dict[str, Path] = {}

    if lang_cfg is not None:
        v = lang_cfg.field_map.view(item)
        source_text = v["source"]
        target_text = v["target"]
        voices = lang_cfg.voices
        # Map asset keys to (voice_key, text).  audio_en = source; jp_f/jp_m = target.
        female_voice = next(
            (k for k in voices if k.endswith("_female") and "english" not in k.split("_female")[0][-3:]),
            "english_female",
        ) if lang_cfg.code != "eng-jap" else "japanese_female"
        male_voice = next(
            (k for k in voices if k.endswith("_male") and "english" not in k.split("_male")[0][-3:]),
            "english_male",
        ) if lang_cfg.code != "eng-jap" else "japanese_male"
        voice_map = {
            "audio_en": ("english_female", source_text),
            "audio_jp_f": (female_voice, target_text),
            "audio_jp_m": (male_voice, target_text),
        }
    else:
        en = _english_text(item)
        jp = _japanese_text(item)
        voice_map = {
            "audio_en": ("english_female", en),
            "audio_jp_f": ("japanese_female", jp),
            "audio_jp_m": ("japanese_male", jp),
        }

    for asset_key, (voice_key, text) in voice_map.items():
        if asset_key not in required or not text:
            continue
        engine = create_engine_fn(voice_key, rate="-20%")
        path = audio_dir / f"{item_index:03d}_{asset_key}.mp3"
        for attempt in range(3):
            try:
                await engine.generate_audio(text, path)
                break
            except Exception as exc:
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                else:
                    raise
        paths[asset_key] = path
        await asyncio.sleep(0.5)

    return paths


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile_assets_sync(
    items_by_phase: dict[Phase, list[LessonItem]],
    profile: Profile,
    output_dir: Path,
    renderer=None,
    lang_cfg=None,
) -> list[CompiledItem]:
    """Compile card assets only (synchronous). TTS audio paths are left as None.

    Useful for dry-run or report-only modes. For full compilation with TTS,
    use ``compile_assets()``.

    *lang_cfg* is an optional :class:`~jlesson.language_config.LanguageConfig`
    that enables language-aware card dispatch.  When ``None``, falls back to
    the legacy Japanese-specific renderers.
    """
    if renderer is None:
        from .video.cards import CardRenderer
        renderer = CardRenderer()

    cards_dir = output_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    compiled: list[CompiledItem] = []
    item_index = 0

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile.required_assets(phase)

        for item in items:
            item_index += 1
            card_paths = _render_item_cards(
                item, required, cards_dir, item_index, renderer, lang_cfg=lang_cfg,
            )
            assets = ItemAssets(**card_paths)
            compiled.append(CompiledItem(item=item, phase=phase, assets=assets))

    return compiled


async def compile_assets(
    items_by_phase: dict[Phase, list[LessonItem]],
    profile: Profile,
    output_dir: Path,
    renderer=None,
    create_engine_fn=None,
    lang_cfg=None,
) -> list[CompiledItem]:
    """Full asset compilation: card images + TTS audio.

    Parameters
    ----------
    items_by_phase : dict mapping Phase → list of items
    profile : Profile rulebook determining which assets to render
    output_dir : base directory for cards/ and audio/ subdirectories
    renderer : optional CardRenderer instance (created if None)
    create_engine_fn : optional factory ``(voice_key, rate) → TTSEngine``
    lang_cfg : optional LanguageConfig for language-aware rendering dispatch
    """
    if renderer is None:
        from .video.cards import CardRenderer
        renderer = CardRenderer()

    if create_engine_fn is None:
        from .video.tts_engine import create_engine
        create_engine_fn = create_engine

    cards_dir = output_dir / "cards"
    audio_dir = output_dir / "audio"
    cards_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    compiled: list[CompiledItem] = []
    item_index = 0

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile.required_assets(phase)

        for item in items:
            item_index += 1

            card_paths = _render_item_cards(
                item, required, cards_dir, item_index, renderer, lang_cfg=lang_cfg,
            )

            audio_paths = await _render_item_audio(
                item, required, audio_dir, item_index, create_engine_fn,
                lang_cfg=lang_cfg,
            )

            all_paths = {**card_paths, **audio_paths}
            assets = ItemAssets(**all_paths)
            compiled.append(CompiledItem(item=item, phase=phase, assets=assets))

    return compiled
