"""
Asset compiler — Stage 2 of the compilation pipeline.

Takes a list of lesson items (GeneralItem, GeneralItem, Sentence) grouped by phase,
determines which assets are needed based on the selected profile, and renders
card images + TTS audio for each item.

Produces a list of GeneralItem objects with populated asset paths.

Usage:
    from jlesson.asset_compiler import compile_assets
    compiled = await compile_assets(items_by_phase, profile, output_dir=output_dir)
"""

from __future__ import annotations

import asyncio
import anyio
from pathlib import Path

from jlesson.language_config import LanguageConfig
from jlesson.video.cards import CardRenderer

from .models import (
    GeneralItem,
    GeneralItem,
    Phase,
)
from .profiles import Profile


# ---------------------------------------------------------------------------
# Card rendering
# ---------------------------------------------------------------------------


def _render_item_cards(
    item: GeneralItem,
    required: set[str],
    cards_dir: Path,
    item_index: int,
    renderer : CardRenderer,
    lang_cfg: LanguageConfig | None =None,
) -> None:
    """Render the card images needed for *item* and update item's assets.

    When *lang_cfg* is provided its :class:`~jlesson.language_config.FieldMap`
    is used for language-agnostic text extraction and the correct card renderer
    method is selected for the language.  Falls back to the Japanese-specific
    renderer methods when *lang_cfg* is ``None``.
    """

    for asset_key in required:
        if not asset_key.startswith("card_"):
            continue
        suffix = asset_key.split('_', 1)[1]  # src, tar, src_tar
        path = cards_dir / f"{item_index:03d}_{suffix}.png"
        card = renderer.render_card(
            item=item,
            touch=None,  # Touch-specific details are not needed for static card rendering
            lang_cfg=lang_cfg,
        )
        renderer.save_card(card, path)
        if "src" in asset_key and asset_key != "card_src_tar":
            item.source.assets[asset_key] = path
        else:
            item.target.assets[asset_key] = path


# ---------------------------------------------------------------------------
# TTS rendering
# ---------------------------------------------------------------------------


async def _render_item_audio(
    item: GeneralItem,
    required: set[str],
    audio_dir: Path,
    item_index: int,
    create_engine_fn,
    lang_cfg: LanguageConfig | None =None,
) -> None:
    """Generate TTS audio files needed for *item* and update item's assets.

    When *lang_cfg* is provided, audio_tar_f / audio_tar_m asset keys are routed
    to the correct target-language voices for the language pair.  For eng-jap
    this means Japanese voices; for hun-eng this means English voices.
    """

    # Map asset keys to (voice_key, text) tuples.  We compute it here instead
    # of relying on a global variable to keep the function self-contained.
    if lang_cfg is None:
        from .language_config import get_language_config
        
        lang_cfg = get_language_config("eng-jap")

    source_text = item.source.tts_text or item.source.display_text
    target_text = item.target.tts_text or item.target.display_text

    voice_map = {
        "audio_src": (lang_cfg.source_voice, source_text),
        "audio_tar_f": (lang_cfg.target_voice_female, target_text),
        "audio_tar_m": (lang_cfg.target_voice_male, target_text),
    }

    for asset_key, (voice_key, text) in voice_map.items():
        if asset_key not in required or not text or not voice_key:
            continue
        engine = create_engine_fn(lang_cfg.voices.get(voice_key, voice_key), rate="-20%")
        path = audio_dir / f"{item_index:03d}_{asset_key}.mp3"
        for attempt in range(3):
            try:
                await engine.generate_audio(text, path)
                break
            except Exception as exc:
                if attempt < 2:
                    await anyio.sleep(2**attempt)
                else:
                    raise RuntimeError(
                        f"TTS failed for asset '{asset_key}' after 3 attempts.\n"
                        f"  voice_key : {voice_key!r}\n"
                        f"  resolved  : {getattr(engine, 'voice', '?')!r}\n"
                        f"  text      : {text!r}\n"
                        f"  cause     : {exc}"
                    ) from exc
        if asset_key == "audio_src":
            item.source.assets[asset_key] = path
        else:
            item.target.assets[asset_key] = path
        await anyio.sleep(0.5)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile_assets_sync(
    items_by_phase: dict[Phase, list[GeneralItem]],
    profile: Profile,
    step_info=None,
    output_dir: Path | None = None,
    renderer=None,
    lang_cfg=None,
) -> list[GeneralItem]:
    """Compile card assets only (synchronous). TTS audio paths are left as None.

    Useful for dry-run or report-only modes. For full compilation with TTS,
    use ``compile_assets()``.

    ``step_info`` is retained for call-site compatibility but ignored because
    asset compilation renders reusable static cards, not touch-progress cards.

    *lang_cfg* is an optional :class:`~jlesson.language_config.LanguageConfig`
    that enables language-aware card dispatch.  When ``None``, falls back to
    the legacy Japanese-specific renderers.
    """
    if output_dir is None:
        raise ValueError("output_dir is required")

    if renderer is None:
        from .video.cards import CardRenderer
        renderer = CardRenderer()

    cards_dir = output_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    compiled: list[GeneralItem] = []
    item_index = 0

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile.required_assets(phase)

        for item in items:
            item_index += 1
            _render_item_cards(
                item, required, cards_dir, item_index, renderer, lang_cfg=lang_cfg,
            )
            compiled_item = item.model_copy()
            compiled_item.phase = phase
            compiled.append(compiled_item)

    return compiled


async def compile_assets(
    items_by_phase: dict[Phase, list[GeneralItem]],
    profile: Profile,
    step_info=None,
    output_dir: Path | None = None,
    renderer=None,
    create_engine_fn=None,
    lang_cfg: LanguageConfig | None =None,
) -> list[GeneralItem]:
    """Full asset compilation: card images + TTS audio.

    Parameters
    ----------
    items_by_phase : dict mapping Phase → list of items
    profile : Profile rulebook determining which assets to render
    step_info : retained for call-site compatibility; ignored for static cards
    output_dir : base directory for cards/ and audio/ subdirectories
    renderer : optional CardRenderer instance (created if None)
    create_engine_fn : optional factory ``(voice_key, rate) → TTSEngine``
    lang_cfg : optional LanguageConfig for language-aware rendering dispatch
    """
    if output_dir is None:
        raise ValueError("output_dir is required")

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

    compiled: list[GeneralItem] = []
    item_index = 0

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile.required_assets(phase)

        for item in items:
            item_index += 1

            _render_item_cards(
                item, required, cards_dir, item_index, renderer, lang_cfg=lang_cfg,
            )

            await _render_item_audio(
                item, required, audio_dir, item_index, create_engine_fn,
                lang_cfg=lang_cfg,
            )

            compiled_item = item.model_copy()
            compiled_item.phase = phase
            compiled.append(compiled_item)

    return compiled
