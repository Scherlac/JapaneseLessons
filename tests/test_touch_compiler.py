"""Unit tests for jlesson.touch_compiler — touch sequence compilation."""

import pytest

from jlesson.models import (
    CompiledItem,
    ItemAssets,
    NounItem,
    Phase,
    Sentence,
    Touch,
    TouchIntent,
    TouchType,
    VerbItem,
)
from jlesson.profiles import ACTIVE_FLASH_CARDS, PASSIVE_VIDEO, Profile
from jlesson.touch_compiler import compile_touches, count_touches


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _noun(english: str) -> NounItem:
    return NounItem(english=english, japanese="テスト", romaji="tesuto")


def _verb(english: str) -> VerbItem:
    return VerbItem(english=english, japanese="する", romaji="suru", masu_form="します")


def _sentence(english: str, grammar_id: str = "G1") -> Sentence:
    return Sentence(english=english, japanese="テスト文", romaji="tesuto bun", grammar_id=grammar_id)


def _compiled(item, phase: Phase, **asset_kwargs) -> CompiledItem:
    return CompiledItem(item=item, phase=phase, assets=ItemAssets(**asset_kwargs))


# ---------------------------------------------------------------------------
# count_touches
# ---------------------------------------------------------------------------


class TestCountTouches:
    def test_passive_video_standard_unit(self):
        result = count_touches(6, 6, 9, PASSIVE_VIDEO)
        assert result == {"nouns": 18, "verbs": 18, "grammar": 18, "total": 54}

    def test_active_flash_cards_standard_unit(self):
        result = count_touches(6, 6, 9, ACTIVE_FLASH_CARDS)
        assert result == {"nouns": 30, "verbs": 30, "grammar": 27, "total": 87}

    def test_zero_items(self):
        result = count_touches(0, 0, 0, PASSIVE_VIDEO)
        assert result["total"] == 0

    def test_nouns_only(self):
        result = count_touches(4, 0, 0, ACTIVE_FLASH_CARDS)
        assert result == {"nouns": 20, "verbs": 0, "grammar": 0, "total": 20}


# ---------------------------------------------------------------------------
# compile_touches — basic structure
# ---------------------------------------------------------------------------


class TestCompileTouchesStructure:
    def test_empty_input(self):
        assert compile_touches([], PASSIVE_VIDEO) == []

    def test_single_noun_passive_produces_3_touches(self):
        ci = _compiled(_noun("dog"), Phase.NOUNS)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        assert len(touches) == 3

    def test_single_noun_active_produces_5_touches(self):
        ci = _compiled(_noun("dog"), Phase.NOUNS)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        assert len(touches) == 5

    def test_single_sentence_passive_produces_2_touches(self):
        ci = _compiled(_sentence("I eat"), Phase.GRAMMAR)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        assert len(touches) == 2

    def test_single_sentence_active_produces_3_touches(self):
        ci = _compiled(_sentence("I eat"), Phase.GRAMMAR)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        assert len(touches) == 3


# ---------------------------------------------------------------------------
# compile_touches — interleaving order
# ---------------------------------------------------------------------------


class TestCompileTouchesInterleaving:
    """Verify round-robin ordering: all items do touch 1, then all do touch 2, etc."""

    def test_two_nouns_passive_interleaving(self):
        ci_a = _compiled(_noun("cat"), Phase.NOUNS)
        ci_b = _compiled(_noun("dog"), Phase.NOUNS)
        touches = compile_touches([ci_a, ci_b], PASSIVE_VIDEO)

        # 2 nouns × 3 touches = 6
        assert len(touches) == 6

        # Round 1: cat-t1, dog-t1
        assert touches[0].compiled_item_index == 0
        assert touches[0].touch_index == 1
        assert touches[1].compiled_item_index == 1
        assert touches[1].touch_index == 1

        # Round 2: cat-t2, dog-t2
        assert touches[2].compiled_item_index == 0
        assert touches[2].touch_index == 2
        assert touches[3].compiled_item_index == 1
        assert touches[3].touch_index == 2

    def test_phases_are_concatenated_in_order(self):
        ci_n = _compiled(_noun("cat"), Phase.NOUNS)
        ci_v = _compiled(_verb("run"), Phase.VERBS)
        ci_g = _compiled(_sentence("I run"), Phase.GRAMMAR)
        touches = compile_touches([ci_n, ci_v, ci_g], PASSIVE_VIDEO)

        phases = [t.intent for t in touches]
        # Nouns first (3 touches), then verbs (3), then grammar (2)
        assert len(touches) == 3 + 3 + 2

        # First touch of each phase
        assert touches[0].compiled_item_index == 0  # noun
        assert touches[3].compiled_item_index == 1  # verb
        assert touches[6].compiled_item_index == 2  # grammar


# ---------------------------------------------------------------------------
# compile_touches — touch types and intents
# ---------------------------------------------------------------------------


class TestCompileTouchTypesAndIntents:
    def test_passive_noun_touch_types(self):
        ci = _compiled(_noun("cat"), Phase.NOUNS)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        types = [t.touch_type for t in touches]
        assert types == [
            TouchType.LISTEN_EN_JPM_JPF,
            TouchType.LISTEN_JPF_JPM,
            TouchType.LISTEN_EN_JPM_JPF,
        ]

    def test_passive_noun_intents(self):
        ci = _compiled(_noun("cat"), Phase.NOUNS)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        intents = [t.intent for t in touches]
        assert intents == [
            TouchIntent.INTRODUCE,
            TouchIntent.REINFORCE,
            TouchIntent.LOCK_IN,
        ]

    def test_active_noun_touch_types(self):
        ci = _compiled(_noun("cat"), Phase.NOUNS)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        types = [t.touch_type for t in touches]
        assert types == [
            TouchType.EN_JP,
            TouchType.JP_EN,
            TouchType.EN_JP,
            TouchType.JP_JP,
            TouchType.EN_JP,
        ]

    def test_active_grammar_intents(self):
        ci = _compiled(_sentence("I eat"), Phase.GRAMMAR)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        intents = [t.intent for t in touches]
        assert intents == [
            TouchIntent.TRANSLATE,
            TouchIntent.COMPREHEND,
            TouchIntent.REINFORCE,
        ]


# ---------------------------------------------------------------------------
# compile_touches — asset resolution
# ---------------------------------------------------------------------------


class TestCompileTouchAssetResolution:
    def test_passive_touch_resolves_card_en_jp(self, tmp_path):
        card_path = tmp_path / "card_en_jp.png"
        card_path.touch()
        ci = _compiled(_noun("cat"), Phase.NOUNS, card_en_jp=card_path)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        # Touch 1 (listen:en,jp-m,jp-f) should resolve to card_en_jp
        assert touches[0].card_path == card_path

    def test_passive_touch_2_resolves_card_jp(self, tmp_path):
        card_jp = tmp_path / "card_jp.png"
        card_jp.touch()
        ci = _compiled(_noun("cat"), Phase.NOUNS, card_jp=card_jp)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        # Touch 2 (listen:jp-f,jp-m) should resolve to card_jp
        assert touches[1].card_path == card_jp

    def test_active_touch_resolves_audio_jp_f(self, tmp_path):
        audio = tmp_path / "audio.mp3"
        audio.touch()
        ci = _compiled(_noun("cat"), Phase.NOUNS, audio_jp_f=audio)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        # All active noun touches use audio_jp_f
        assert touches[0].audio_paths == [audio]

    def test_passive_listen_resolves_three_audio_files(self, tmp_path):
        en = tmp_path / "en.mp3"
        jp_m = tmp_path / "jp_m.mp3"
        jp_f = tmp_path / "jp_f.mp3"
        for p in (en, jp_m, jp_f):
            p.touch()
        ci = _compiled(
            _noun("cat"), Phase.NOUNS,
            audio_en=en, audio_jp_m=jp_m, audio_jp_f=jp_f,
        )
        touches = compile_touches([ci], PASSIVE_VIDEO)
        # Touch 1 (listen:en,jp-m,jp-f) → [en, jp_m, jp_f]
        assert touches[0].audio_paths == [en, jp_m, jp_f]

    def test_missing_assets_resolve_to_none(self):
        ci = _compiled(_noun("cat"), Phase.NOUNS)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        assert touches[0].card_path is None
        assert touches[0].audio_paths == []


# ---------------------------------------------------------------------------
# compile_touches — full compilation example from docs/structure.md
# ---------------------------------------------------------------------------


class TestCompileTouchesDocExample:
    """Verify the compilation example from docs/structure.md:
    2 nouns + 2 grammar sentences, passive profile = 10 touches.
    """

    def test_passive_2n_2g_produces_10_touches(self):
        items = [
            _compiled(_noun("cat"), Phase.NOUNS),
            _compiled(_noun("dog"), Phase.NOUNS),
            _compiled(_sentence("I eat"), Phase.GRAMMAR),
            _compiled(_sentence("You drink"), Phase.GRAMMAR),
        ]
        touches = compile_touches(items, PASSIVE_VIDEO)
        # 2 nouns × 3 + 2 grammar × 2 = 10
        assert len(touches) == 10

    def test_active_2n_2g_produces_16_touches(self):
        items = [
            _compiled(_noun("cat"), Phase.NOUNS),
            _compiled(_noun("dog"), Phase.NOUNS),
            _compiled(_sentence("I eat"), Phase.GRAMMAR),
            _compiled(_sentence("You drink"), Phase.GRAMMAR),
        ]
        touches = compile_touches(items, ACTIVE_FLASH_CARDS)
        # 2 nouns × 5 + 2 grammar × 3 = 16
        assert len(touches) == 16
