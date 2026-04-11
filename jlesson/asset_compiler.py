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


def _asset_stem(item: GeneralItem, lang_cfg: LanguageConfig | None) -> str:
    """Return a stable filename stem for *item* based on canonical id."""
    canonical_id = (item.canonical.id if item.canonical else "") or ""
    if canonical_id:
        return canonical_id
    # Fallback: derive from display text if id not yet populated
    text = (item.canonical.text if item.canonical else "") or ""
    return text.lower().replace(" ", "_")[:40] or "item"


def _lang_codes(lang_cfg: LanguageConfig | None) -> tuple[str, str]:
    """Return (source_code, target_code) from *lang_cfg*, defaulting to 'src'/'tar'."""
    if lang_cfg is None:
        return "src", "tar"
    return lang_cfg.source.code, lang_cfg.target.code


def build_asset_suffix_map(language_code: str) -> dict[str, str]:
    """Return the canonical asset-key → filename-suffix mapping for *language_code*.

    The suffix is the part after ``{item_id}_``, e.g. ``audio_fr_f.mp3``.
    Language codes are derived from the first two characters of each part:
    ``eng-fre`` → src=``en``, tar=``fr``.

    This is the single source of truth for the asset filename convention used
    by :mod:`asset_compiler`, :class:`~jlesson.rcm.RCMStore`, and the import /
    bundle tools.
    """
    parts = language_code.split("-")
    src = parts[0][:2] if parts else "en"
    tar = parts[1][:2] if len(parts) > 1 else "fr"
    return {
        "audio_src":   f"audio_{src}.mp3",
        "audio_tar_f": f"audio_{tar}_f.mp3",
        "audio_tar_m": f"audio_{tar}_m.mp3",
        "card_src":    f"card_{src}.png",
        "card_tar":    f"card_{tar}.png",
        "card_src_tar":f"card_{src}_{tar}.png",
    }


def _render_item_cards(
    item: GeneralItem,
    required: set[str],
    cards_dir: Path,
    renderer: CardRenderer,
    lang_cfg: LanguageConfig | None = None,
) -> None:
    """Render the card images needed for *item* and update item's assets.

    Filenames use the canonical item id + language codes so that each item
    across all blocks gets a unique, stable path, e.g.:
      nouns_house_08c6b0_card_en_ja.png
    """
    stem = _asset_stem(item, lang_cfg)
    src_code, tar_code = _lang_codes(lang_cfg)

    _CARD_FILENAME: dict[str, str] = {
        "card_src": f"{stem}_card_{src_code}.png",
        "card_tar": f"{stem}_card_{tar_code}.png",
        "card_src_tar": f"{stem}_card_{src_code}_{tar_code}.png",
    }

    for asset_key in required:
        if asset_key not in _CARD_FILENAME:
            continue
        path = cards_dir / _CARD_FILENAME[asset_key]
        if path.exists():
            if asset_key == "card_src":
                item.source.assets[asset_key] = path
            else:
                item.target.assets[asset_key] = path
            continue
        card = renderer.render_card(
            item=item,
            touch=None,
            lang_cfg=lang_cfg,
        )
        renderer.save_card(card, path)
        if asset_key == "card_src":
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
    create_engine_fn,
    lang_cfg: LanguageConfig | None = None,
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

    stem = _asset_stem(item, lang_cfg)
    src_code, tar_code = _lang_codes(lang_cfg)
    _AUDIO_FILENAME: dict[str, str] = {
        "audio_src": f"{stem}_audio_{src_code}.mp3",
        "audio_tar_f": f"{stem}_audio_{tar_code}_f.mp3",
        "audio_tar_m": f"{stem}_audio_{tar_code}_m.mp3",
    }

    for asset_key, (voice_key, text) in voice_map.items():
        if asset_key not in required or not text or not voice_key:
            continue
        path = audio_dir / _AUDIO_FILENAME.get(asset_key, f"{stem}_{asset_key}.mp3")
        if path.exists():
            if asset_key == "audio_src":
                item.source.assets[asset_key] = path
            else:
                item.target.assets[asset_key] = path
            continue
        engine = create_engine_fn(lang_cfg.voices.get(voice_key, voice_key), rate="-20%")
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
) -> dict[Phase, list[GeneralItem]]:
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

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.ADJECTIVES, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile.required_assets(phase)

        for item in items:
            _render_item_cards(
                item, required, cards_dir, renderer, lang_cfg=lang_cfg,
            )
            compiled_item = item.model_copy()
            compiled_item.phase = phase

    return items_by_phase


async def compile_assets(
    items_by_phase: dict[Phase, list[GeneralItem]],
    profile: Profile,
    output_dir: Path | None = None,
    renderer=None,
    create_engine_fn=None,
    lang_cfg: LanguageConfig | None = None,
) -> dict[Phase, list[GeneralItem]]:
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

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.ADJECTIVES, Phase.GRAMMAR):
        items = items_by_phase.get(phase, [])
        required = profile.required_assets(phase)

        for item in items:
            _render_item_cards(
                item, required, cards_dir, renderer, lang_cfg=lang_cfg,
            )

            await _render_item_audio(
                item, required, audio_dir, create_engine_fn,
                lang_cfg=lang_cfg,
            )

            compiled_item = item.model_copy()
            compiled_item.phase = phase

    return items_by_phase
