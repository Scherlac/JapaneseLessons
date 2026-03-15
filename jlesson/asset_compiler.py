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
# Text extraction helpers
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
) -> dict[str, Path]:
    """Render the card images needed for *item* and return asset-key → path."""
    paths: dict[str, Path] = {}
    en = _english_text(item)
    jp = _japanese_text(item)
    kana = _kana_text(item)
    romaji = _romaji_text(item)

    if "card_en" in required:
        path = cards_dir / f"{item_index:03d}_en.png"
        card = renderer.render_en_card(english=en)
        renderer.save_card(card, path)
        paths["card_en"] = path

    if "card_jp" in required:
        path = cards_dir / f"{item_index:03d}_jp.png"
        card = renderer.render_jp_card(japanese=jp, kana=kana, romaji=romaji)
        renderer.save_card(card, path)
        paths["card_jp"] = path

    if "card_en_jp" in required:
        path = cards_dir / f"{item_index:03d}_en_jp.png"
        card = renderer.render_bilingual_card(
            english=en, japanese=jp, kana=kana, romaji=romaji,
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
) -> dict[str, Path]:
    """Generate TTS audio files needed for *item* and return asset-key → path."""
    paths: dict[str, Path] = {}
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
) -> list[CompiledItem]:
    """Compile card assets only (synchronous). TTS audio paths are left as None.

    Useful for dry-run or report-only modes. For full compilation with TTS,
    use ``compile_assets()``.
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
                item, required, cards_dir, item_index, renderer,
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
) -> list[CompiledItem]:
    """Full asset compilation: card images + TTS audio.

    Parameters
    ----------
    items_by_phase : dict mapping Phase → list of items
    profile : Profile rulebook determining which assets to render
    output_dir : base directory for cards/ and audio/ subdirectories
    renderer : optional CardRenderer instance (created if None)
    create_engine_fn : optional factory ``(voice_key, rate) → TTSEngine``
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
                item, required, cards_dir, item_index, renderer,
            )

            audio_paths = await _render_item_audio(
                item, required, audio_dir, item_index, create_engine_fn,
            )

            all_paths = {**card_paths, **audio_paths}
            assets = ItemAssets(**all_paths)
            compiled.append(CompiledItem(item=item, phase=phase, assets=assets))

    return compiled
