"""Unit tests for jlesson.asset_compiler — Stage 2 asset compilation."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from jlesson.asset_compiler import (
    _english_text,
    _japanese_text,
    _kana_text,
    _render_item_cards,
    _romaji_text,
    compile_assets,
    compile_assets_sync,
)
from jlesson.models import (
    CompiledItem,
    ItemAssets,
    NounItem,
    Phase,
    Sentence,
    VerbItem,
)
from jlesson.profiles import ACTIVE_FLASH_CARDS, PASSIVE_VIDEO


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _noun() -> NounItem:
    return NounItem(english="water", japanese="みず", kanji="水", romaji="mizu")


def _verb() -> VerbItem:
    return VerbItem(
        english="to eat", japanese="たべる", kanji="食べる",
        romaji="taberu", masu_form="食べます",
    )


def _sentence() -> Sentence:
    return Sentence(
        english="I eat bread.", japanese="パンを食べます。",
        romaji="pan wo tabemasu", grammar_id="G1", person="I",
    )


def _mock_renderer():
    """Create a mock CardRenderer that returns Image-like objects."""
    r = MagicMock()
    r.render_en_card.return_value = MagicMock()
    r.render_jp_card.return_value = MagicMock()
    r.render_bilingual_card.return_value = MagicMock()
    return r


def _mock_engine_factory():
    """Create a mock TTS engine factory."""
    engine = AsyncMock()
    engine.generate_audio = AsyncMock()
    return MagicMock(return_value=engine)


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------


class TestTextExtraction:
    def test_english_text_noun(self):
        assert _english_text(_noun()) == "water"

    def test_japanese_text_noun(self):
        assert _japanese_text(_noun()) == "みず"

    def test_kana_text_noun(self):
        assert _kana_text(_noun()) == "みず"

    def test_kana_text_sentence_is_empty(self):
        assert _kana_text(_sentence()) == ""

    def test_romaji_text_verb(self):
        assert _romaji_text(_verb()) == "taberu"


# ---------------------------------------------------------------------------
# _render_item_cards
# ---------------------------------------------------------------------------


class TestRenderItemCards:
    def test_renders_en_card_when_required(self, tmp_path):
        renderer = _mock_renderer()
        paths = _render_item_cards(_noun(), {"card_en"}, tmp_path, 1, renderer)
        renderer.render_en_card.assert_called_once()
        assert "card_en" in paths

    def test_renders_jp_card_when_required(self, tmp_path):
        renderer = _mock_renderer()
        paths = _render_item_cards(_noun(), {"card_jp"}, tmp_path, 1, renderer)
        renderer.render_jp_card.assert_called_once()
        assert "card_jp" in paths

    def test_renders_bilingual_card_when_required(self, tmp_path):
        renderer = _mock_renderer()
        paths = _render_item_cards(_noun(), {"card_en_jp"}, tmp_path, 1, renderer)
        renderer.render_bilingual_card.assert_called_once()
        assert "card_en_jp" in paths

    def test_skips_unrequired_cards(self, tmp_path):
        renderer = _mock_renderer()
        paths = _render_item_cards(_noun(), {"card_en"}, tmp_path, 1, renderer)
        renderer.render_jp_card.assert_not_called()
        renderer.render_bilingual_card.assert_not_called()
        assert "card_jp" not in paths

    def test_file_naming_convention(self, tmp_path):
        renderer = _mock_renderer()
        paths = _render_item_cards(
            _noun(), {"card_en", "card_jp", "card_en_jp"}, tmp_path, 5, renderer,
        )
        assert paths["card_en"].name == "005_en.png"
        assert paths["card_jp"].name == "005_jp.png"
        assert paths["card_en_jp"].name == "005_en_jp.png"


# ---------------------------------------------------------------------------
# compile_assets_sync (cards only, no TTS)
# ---------------------------------------------------------------------------


class TestCompileAssetsSync:
    def test_active_nouns_produce_en_and_jp_cards(self, tmp_path):
        renderer = _mock_renderer()
        items = {Phase.NOUNS: [_noun()]}
        compiled = compile_assets_sync(items, ACTIVE_FLASH_CARDS, tmp_path, renderer)

        assert len(compiled) == 1
        assert compiled[0].phase == Phase.NOUNS
        assert compiled[0].assets.card_en is not None
        assert compiled[0].assets.card_jp is not None

    def test_passive_nouns_produce_bilingual_and_jp_cards(self, tmp_path):
        renderer = _mock_renderer()
        items = {Phase.NOUNS: [_noun()]}
        compiled = compile_assets_sync(items, PASSIVE_VIDEO, tmp_path, renderer)

        assert len(compiled) == 1
        assert compiled[0].assets.card_en_jp is not None
        assert compiled[0].assets.card_jp is not None

    def test_phase_ordering_nouns_verbs_grammar(self, tmp_path):
        renderer = _mock_renderer()
        items = {
            Phase.GRAMMAR: [_sentence()],
            Phase.NOUNS: [_noun()],
            Phase.VERBS: [_verb()],
        }
        compiled = compile_assets_sync(items, ACTIVE_FLASH_CARDS, tmp_path, renderer)

        assert len(compiled) == 3
        assert compiled[0].phase == Phase.NOUNS
        assert compiled[1].phase == Phase.VERBS
        assert compiled[2].phase == Phase.GRAMMAR

    def test_empty_input(self, tmp_path):
        renderer = _mock_renderer()
        compiled = compile_assets_sync({}, ACTIVE_FLASH_CARDS, tmp_path, renderer)
        assert compiled == []

    def test_items_are_preserved(self, tmp_path):
        renderer = _mock_renderer()
        noun = _noun()
        items = {Phase.NOUNS: [noun]}
        compiled = compile_assets_sync(items, ACTIVE_FLASH_CARDS, tmp_path, renderer)
        assert compiled[0].item == noun

    def test_audio_assets_are_none_in_sync(self, tmp_path):
        renderer = _mock_renderer()
        items = {Phase.NOUNS: [_noun()]}
        compiled = compile_assets_sync(items, PASSIVE_VIDEO, tmp_path, renderer)
        assert compiled[0].assets.audio_en is None
        assert compiled[0].assets.audio_jp_f is None
        assert compiled[0].assets.audio_jp_m is None

    def test_creates_cards_directory(self, tmp_path):
        renderer = _mock_renderer()
        out = tmp_path / "lesson_001"
        items = {Phase.NOUNS: [_noun()]}
        compile_assets_sync(items, ACTIVE_FLASH_CARDS, out, renderer)
        assert (out / "cards").is_dir()


# ---------------------------------------------------------------------------
# compile_assets (async, with TTS)
# ---------------------------------------------------------------------------


class TestCompileAssetsAsync:
    @pytest.mark.asyncio
    async def test_passive_noun_generates_three_audio_files(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {Phase.NOUNS: [_noun()]}

        compiled = await compile_assets(
            items, PASSIVE_VIDEO, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 1
        # Passive nouns need: audio_en, audio_jp_f, audio_jp_m
        assert compiled[0].assets.audio_en is not None
        assert compiled[0].assets.audio_jp_f is not None
        assert compiled[0].assets.audio_jp_m is not None

    @pytest.mark.asyncio
    async def test_active_noun_generates_one_audio_file(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {Phase.NOUNS: [_noun()]}

        compiled = await compile_assets(
            items, ACTIVE_FLASH_CARDS, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 1
        # Active nouns need only: audio_jp_f
        assert compiled[0].assets.audio_jp_f is not None
        assert compiled[0].assets.audio_en is None
        assert compiled[0].assets.audio_jp_m is None

    @pytest.mark.asyncio
    async def test_engine_called_with_correct_voices(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {Phase.NOUNS: [_noun()]}

        await compile_assets(items, PASSIVE_VIDEO, tmp_path, renderer, engine_fn)

        voice_keys = [c.args[0] for c in engine_fn.call_args_list]
        assert "english_female" in voice_keys
        assert "japanese_female" in voice_keys
        assert "japanese_male" in voice_keys

    @pytest.mark.asyncio
    async def test_multiple_items_indexed_correctly(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        n1 = NounItem(english="cat", japanese="ねこ", romaji="neko")
        n2 = NounItem(english="dog", japanese="いぬ", romaji="inu")
        items = {Phase.NOUNS: [n1, n2]}

        compiled = await compile_assets(
            items, ACTIVE_FLASH_CARDS, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 2
        assert compiled[0].item.english == "cat"
        assert compiled[1].item.english == "dog"
        # Check file naming: item indices 1 and 2
        assert "001" in compiled[0].assets.card_en.name
        assert "002" in compiled[1].assets.card_en.name

    @pytest.mark.asyncio
    async def test_creates_audio_directory(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        out = tmp_path / "lesson_001"
        items = {Phase.NOUNS: [_noun()]}

        await compile_assets(items, ACTIVE_FLASH_CARDS, out, renderer, engine_fn)
        assert (out / "audio").is_dir()

    @pytest.mark.asyncio
    async def test_full_pipeline_noun_verb_grammar(self, tmp_path):
        renderer = _mock_renderer()
        engine_fn = _mock_engine_factory()
        items = {
            Phase.NOUNS: [_noun()],
            Phase.VERBS: [_verb()],
            Phase.GRAMMAR: [_sentence()],
        }

        compiled = await compile_assets(
            items, ACTIVE_FLASH_CARDS, tmp_path, renderer, engine_fn,
        )

        assert len(compiled) == 3
        phases = [ci.phase for ci in compiled]
        assert phases == [Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR]
