"""Unit tests for jlesson.asset_compiler — Stage 2 asset compilation."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from jlesson.asset_compiler import (
    _render_item_cards,
    compile_assets,
    compile_assets_sync,
)
from jlesson.language_config import get_language_config
from jlesson.lesson_pipeline import StepInfo
from jlesson.models import GeneralItem, PartialItem, Phase, Sentence
from jlesson.profiles import ACTIVE_FLASH_CARDS, PASSIVE_VIDEO

ENG_JAP = get_language_config("eng-jap")
HUN_ENG = get_language_config("hun-eng")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _noun() -> GeneralItem:
    return GeneralItem(
        source=PartialItem(display_text="water"),
        target=PartialItem(display_text="みず", pronunciation="mizu", extra={"kanji": "水"}),
    )


def _verb() -> GeneralItem:
    return GeneralItem(
        source=PartialItem(display_text="to eat"),
        target=PartialItem(display_text="たべる", pronunciation="taberu", extra={"kanji": "食べる", "masu_form": "食べます"}),
    )


def _sentence() -> Sentence:
    return Sentence(
        source=PartialItem(display_text="I eat bread."),
        target=PartialItem(display_text="パンを食べます。", pronunciation="pan o tabemasu."),
        grammar_id="G1",
        grammar_parameters={},
    )


def _mock_renderer():
    """Create a mock CardRenderer that returns Image-like objects."""
    r = MagicMock()
    r.render_card.return_value = MagicMock()
    r.save_card = MagicMock()
    return r


def _hun_noun() -> GeneralItem:
    """GeneralItem carrying Hungarian extra fields."""
    return GeneralItem.model_validate({
        "source": {"display_text": "cat"},
        "target": {"display_text": "macska", "pronunciation": "/ˈmɒtʃkɒ/"},
    })


def _mock_engine_factory():
    """Create a mock TTS engine factory."""
    engine = AsyncMock()
    engine.generate_audio = AsyncMock()
    return MagicMock(return_value=engine)


def _mock_step_info():
    """Return None — step_info is accepted but ignored by asset compilation functions."""
    return None



# ---------------------------------------------------------------------------
# _render_item_cards
# ---------------------------------------------------------------------------


class TestRenderItemCards:
    def test_renders_src_card_when_required(self, tmp_path):
        renderer = _mock_renderer()
        item = _noun()
        _render_item_cards(item, {"card_src"}, tmp_path, 1, renderer)
        renderer.render_card.assert_called_once()
        assert "card_src" in item.source.assets

    def test_renders_tar_card_when_required(self, tmp_path):
        renderer = _mock_renderer()
        item = _noun()
        _render_item_cards(item, {"card_tar"}, tmp_path, 1, renderer)
        renderer.render_card.assert_called_once()
        assert "card_tar" in item.target.assets

    def test_renders_src_tar_card_when_required(self, tmp_path):
        renderer = _mock_renderer()
        item = _noun()
        _render_item_cards(item, {"card_src_tar"}, tmp_path, 1, renderer)
        renderer.render_card.assert_called_once()
        assert "card_src_tar" in item.target.assets

    def test_skips_unrequired_cards(self, tmp_path):
        renderer = _mock_renderer()
        item = _noun()
        _render_item_cards(item, {"card_src"}, tmp_path, 1, renderer)
        # Only one call for card_src
        assert renderer.render_card.call_count == 1
        assert "card_tar" not in item.target.assets

    def test_file_naming_convention(self, tmp_path):
        renderer = _mock_renderer()
        item = _noun()
        _render_item_cards(
            item, {"card_src", "card_tar", "card_src_tar"}, tmp_path, 5, renderer,
        )
        assert renderer.render_card.call_count == 3
        assert item.source.assets["card_src"].name == "005_src.png"
        assert item.target.assets["card_tar"].name == "005_tar.png"
        assert item.target.assets["card_src_tar"].name == "005_src_tar.png"


# ---------------------------------------------------------------------------
# _render_item_cards — Hungarian dispatch (via lang_cfg)
# ---------------------------------------------------------------------------


class TestRenderItemCardsHungarian:
    def test_card_src_renders(self, tmp_path):
        """card_src in hun-eng mode should render."""
        renderer = _mock_renderer()
        item = _hun_noun()
        _render_item_cards(item, {"card_src"}, tmp_path, 1, renderer, lang_cfg=HUN_ENG)
        renderer.render_card.assert_called_once()
        assert "card_src" in item.source.assets

    def test_card_tar_renders(self, tmp_path):
        """card_tar in hun-eng mode should render."""
        renderer = _mock_renderer()
        item = _hun_noun()
        _render_item_cards(item, {"card_tar"}, tmp_path, 1, renderer, lang_cfg=HUN_ENG)
        renderer.render_card.assert_called_once()
        assert "card_tar" in item.target.assets

    def test_card_src_tar_renders(self, tmp_path):
        """card_src_tar in hun-eng mode should render."""
        renderer = _mock_renderer()
        item = _hun_noun()
        _render_item_cards(item, {"card_src_tar"}, tmp_path, 1, renderer, lang_cfg=HUN_ENG)
        renderer.render_card.assert_called_once()
        assert "card_src_tar" in item.target.assets

    def test_japanese_renderers_not_called_for_hungarian(self, tmp_path):
        renderer = _mock_renderer()
        item = _hun_noun()
        _render_item_cards(
            item,
            {"card_src", "card_tar", "card_src_tar"},
            tmp_path, 1, renderer, lang_cfg=HUN_ENG,
        )
        # Only render_card is called, no specific ones
        assert renderer.render_card.call_count == 3

    def test_eng_jap_still_uses_japanese_renderers_when_lang_cfg_provided(self, tmp_path):
        renderer = _mock_renderer()
        item = _noun()
        _render_item_cards(item, {"card_src", "card_tar", "card_src_tar"}, tmp_path, 1, renderer, lang_cfg=ENG_JAP)
        assert renderer.render_card.call_count == 3
        renderer.render_hun_card.assert_not_called()


# ---------------------------------------------------------------------------
# compile_assets_sync (cards only, no TTS)
# ---------------------------------------------------------------------------


class TestCompileAssetsSync:
    def test_active_nouns_produce_src_and_tar_cards(self, tmp_path):
        renderer = _mock_renderer()
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()
        compiled = compile_assets_sync(items, ACTIVE_FLASH_CARDS, step_info, tmp_path, renderer)

        assert len(compiled) == 1
        assert compiled[0].source.assets["card_src"] is not None
        assert compiled[0].target.assets["card_tar"] is not None

    def test_passive_nouns_produce_src_tar_and_tar_cards(self, tmp_path):
        renderer = _mock_renderer()
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()
        compiled = compile_assets_sync(items, PASSIVE_VIDEO, step_info, tmp_path, renderer)

        assert len(compiled) == 1
        assert compiled[0].target.assets["card_src_tar"] is not None
        assert compiled[0].target.assets["card_tar"] is not None

    def test_phase_ordering_nouns_verbs_grammar(self, tmp_path):
        renderer = _mock_renderer()
        items = {
            Phase.GRAMMAR: [_sentence()],
            Phase.NOUNS: [_noun()],
            Phase.VERBS: [_verb()],
        }
        step_info = _mock_step_info()
        compiled = compile_assets_sync(items, ACTIVE_FLASH_CARDS, step_info, tmp_path, renderer)

        assert len(compiled) == 3
        # Phases are processed in order: nouns, verbs, grammar

    def test_empty_input(self, tmp_path):
        renderer = _mock_renderer()
        step_info = _mock_step_info()
        compiled = compile_assets_sync({}, ACTIVE_FLASH_CARDS, step_info, tmp_path, renderer)
        assert compiled == []

    def test_items_are_preserved(self, tmp_path):
        renderer = _mock_renderer()
        noun = _noun()
        items = {Phase.NOUNS: [noun]}
        step_info = _mock_step_info()
        compiled = compile_assets_sync(items, ACTIVE_FLASH_CARDS, step_info, tmp_path, renderer)
        assert compiled[0].source.display_text == "water"

    def test_audio_assets_are_none_in_sync(self, tmp_path):
        renderer = _mock_renderer()
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()
        compiled = compile_assets_sync(items, PASSIVE_VIDEO, step_info, tmp_path, renderer)
        assert compiled[0].source.assets.get("audio_src") is None
        assert compiled[0].target.assets.get("audio_tar_f") is None
        assert compiled[0].target.assets.get("audio_tar_m") is None

    def test_creates_cards_directory(self, tmp_path):
        renderer = _mock_renderer()
        out = tmp_path / "lesson_001"
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()
        compile_assets_sync(items, ACTIVE_FLASH_CARDS, step_info, out, renderer)
        assert (out / "cards").is_dir()


# ---------------------------------------------------------------------------
# compile_assets (async, with TTS)
# ---------------------------------------------------------------------------


class TestCompileAssetsAsync:
    @pytest.mark.anyio
    async def test_passive_noun_generates_three_audio_files(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()

        compiled = await compile_assets(
            items, PASSIVE_VIDEO, step_info, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 1
        # Passive nouns need: audio_src, audio_tar_f, audio_tar_m
        assert compiled[0].source.assets["audio_src"] is not None
        assert compiled[0].target.assets["audio_tar_f"] is not None
        assert compiled[0].target.assets["audio_tar_m"] is not None

    @pytest.mark.anyio
    async def test_active_noun_generates_one_audio_file(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()

        compiled = await compile_assets(
            items, ACTIVE_FLASH_CARDS, step_info, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 1
        # Active nouns need only: audio_tar_f
        assert compiled[0].target.assets["audio_tar_f"] is not None
        assert compiled[0].source.assets.get("audio_src") is None
        assert compiled[0].target.assets.get("audio_tar_m") is None

    @pytest.mark.anyio
    async def test_engine_called_with_correct_voices(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()

        await compile_assets(
            items, PASSIVE_VIDEO, step_info, tmp_path, renderer, engine_fn, lang_cfg=ENG_JAP
        )

        voice_keys = [c.args[0] for c in engine_fn.call_args_list]
        # The voices should be selected from the language config's voice map.
        assert "en-US-AriaNeural" in voice_keys
        assert "ja-JP-NanamiNeural" in voice_keys
        assert "ja-JP-KeitaNeural" in voice_keys

    @pytest.mark.anyio
    async def test_hungarian_uses_correct_voices(self, tmp_path):
        """hun-eng: source=hungarian_female, target=english_female/male."""
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {Phase.NOUNS: [_hun_noun()]}
        step_info = _mock_step_info()

        await compile_assets(
            items, PASSIVE_VIDEO, step_info, tmp_path, renderer, engine_fn, lang_cfg=HUN_ENG,
        )

        voice_keys = [c.args[0] for c in engine_fn.call_args_list]
        assert "hu-HU-NoemiNeural" in voice_keys
        assert "en-GB-SoniaNeural" in voice_keys
        assert "en-GB-RyanNeural" in voice_keys
        assert "ja-JP-NanamiNeural" not in voice_keys
        assert "ja-JP-KeitaNeural" not in voice_keys

    @pytest.mark.anyio
    async def test_multiple_items_indexed_correctly(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        n1 = GeneralItem(
            source=PartialItem(display_text="cat"),
            target=PartialItem(display_text="ねこ", pronunciation="neko")
        )
        n2 = GeneralItem(
            source=PartialItem(display_text="dog"),
            target=PartialItem(display_text="いぬ", pronunciation="inu")
        )
        items = {Phase.NOUNS: [n1, n2]}
        step_info = _mock_step_info()

        compiled = await compile_assets(
            items, ACTIVE_FLASH_CARDS, step_info, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 2
        assert compiled[0].source.display_text == "cat"
        assert compiled[1].source.display_text == "dog"
        # Check file naming: item indices 1 and 2
        assert "001" in compiled[0].source.assets["card_src"].name
        assert "002" in compiled[1].source.assets["card_src"].name

    @pytest.mark.anyio
    async def test_creates_audio_directory(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        out = tmp_path / "lesson_001"
        items = {Phase.NOUNS: [_noun()]}
        step_info = _mock_step_info()

        await compile_assets(items, ACTIVE_FLASH_CARDS, step_info, out, renderer, engine_fn)
        assert (out / "audio").is_dir()

    @pytest.mark.anyio
    async def test_full_pipeline_noun_verb_grammar(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {
            Phase.NOUNS: [_noun()],
            Phase.VERBS: [_verb()],
            Phase.GRAMMAR: [_sentence()],
        }
        step_info = _mock_step_info()

        compiled = await compile_assets(
            items, ACTIVE_FLASH_CARDS, step_info, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 3
