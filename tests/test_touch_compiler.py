"""Unit tests for jlesson.touch_compiler — touch sequence compilation."""

import pytest

from jlesson.models import (
    CompiledItem,
    GeneralItem,
    PartialItem,
    Phase,
    Sentence,
    Touch,
    TouchIntent,
    TouchType,
)
from jlesson.profiles import ACTIVE_FLASH_CARDS, PASSIVE_VIDEO, Profile
from jlesson.touch_compiler import compile_touches, count_touches


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _noun(english: str) -> GeneralItem:
    return GeneralItem(
        source=PartialItem(display_text=english),
        target=PartialItem(display_text="テスト", pronunciation="tesuto")
    )


def _verb(english: str) -> GeneralItem:
    return GeneralItem(
        source=PartialItem(display_text=english),
        target=PartialItem(display_text="する", pronunciation="suru", extra={"masu_form": "します"})
    )


def _sentence(english: str, grammar_id: str = "G1") -> Sentence:
    return Sentence(
        source=PartialItem(display_text=english),
        target=PartialItem(display_text="テスト文", pronunciation="tesuto bun"),
        grammar_id=grammar_id,
        grammar_parameters={}
    )


def _compiled(item, phase: Phase, **asset_kwargs) -> GeneralItem:
    compiled = item.model_copy()
    for k, v in asset_kwargs.items():
        if k.startswith("card_") or k.startswith("audio_"):
            if "src" in k and "tar" not in k:
                compiled.source.assets[k] = v
            else:
                compiled.target.assets[k] = v
    compiled.phase = phase  # Add phase attribute
    return compiled


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

        # All touches for first item, then second
        assert touches[0].touch_index == 1
        assert touches[0].item.source.display_text == "cat"
        assert touches[1].touch_index == 2
        assert touches[1].item.source.display_text == "cat"
        assert touches[2].touch_index == 3
        assert touches[2].item.source.display_text == "cat"
        
        assert touches[3].touch_index == 1
        assert touches[3].item.source.display_text == "dog"
        assert touches[4].touch_index == 2
        assert touches[4].item.source.display_text == "dog"
        assert touches[5].touch_index == 3
        assert touches[5].item.source.display_text == "dog"

    def test_phases_are_concatenated_in_order(self):
        ci_n = _compiled(_noun("cat"), Phase.NOUNS)
        ci_v = _compiled(_verb("run"), Phase.VERBS)
        ci_g = _compiled(_sentence("I run"), Phase.GRAMMAR)
        touches = compile_touches([ci_n, ci_v, ci_g], PASSIVE_VIDEO)

        # Nouns first (3 touches), then verbs (3), then grammar (2)
        assert len(touches) == 3 + 3 + 2

        # First touch of each phase
        assert touches[0].item.source.display_text == "cat"  # noun
        assert touches[3].item.source.display_text == "run"  # verb
        assert touches[6].item.source.display_text == "I run"  # grammar

    def test_multi_phase_items_are_batch_interleaved(self):
        items = [
            _compiled(_noun("n1"), Phase.NOUNS),
            _compiled(_noun("n2"), Phase.NOUNS),
            _compiled(_verb("v1"), Phase.VERBS),
            _compiled(_verb("v2"), Phase.VERBS),
            _compiled(_sentence("g1"), Phase.GRAMMAR),
            _compiled(_sentence("g2"), Phase.GRAMMAR),
        ]
        touches = compile_touches(items, PASSIVE_VIDEO)

        # With batch size 1 per phase: n1 -> v1 -> g1 -> n2 -> v2 -> g2
        block_starts = [0, 3, 6, 8, 11, 14]
        expected_items = ["n1", "v1", "g1", "n2", "v2", "g2"]
        for idx, expected in zip(block_starts, expected_items):
            assert touches[idx].item.source.display_text == expected

    def test_profile_batch_size_controls_phase_chunks(self):
        custom = Profile(
            name="custom",
            cycles=PASSIVE_VIDEO.cycles,
            batch_sizes={
                Phase.NOUNS: 2,
                Phase.VERBS: 1,
                Phase.GRAMMAR: 1,
            },
        )
        items = [
            _compiled(_noun("n1"), Phase.NOUNS),
            _compiled(_noun("n2"), Phase.NOUNS),
            _compiled(_verb("v1"), Phase.VERBS),
            _compiled(_sentence("g1"), Phase.GRAMMAR),
        ]
        touches = compile_touches(items, custom)

        # First round should emit 2 nouns first, then verb, then grammar.
        assert touches[0].item.source.display_text == "n1"
        assert touches[3].item.source.display_text == "n2"
        assert touches[6].item.source.display_text == "v1"
        assert touches[9].item.source.display_text == "g1"


# ---------------------------------------------------------------------------
# compile_touches — touch types and intents
# ---------------------------------------------------------------------------


class TestCompileTouchTypesAndIntents:
    def test_passive_noun_touch_types(self):
        ci = _compiled(_noun("cat"), Phase.NOUNS)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        types = [t.touch_type for t in touches]
        assert types == [
            TouchType.LISTEN_DUAL_M,
            TouchType.LISTEN_REVERSE_F,
            TouchType.LISTEN_DUAL_M,
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
            TouchType.SOURCE_TARGET,
            TouchType.TARGET_SOURCE,
            TouchType.SOURCE_TARGET,
            TouchType.TARGET_ONLY,
            TouchType.SOURCE_TARGET,
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
        card_path = tmp_path / "card_src_tar.png"
        card_path.touch()
        ci = _compiled(_noun("cat"), Phase.NOUNS, card_src_tar=card_path)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        # Touch 1 (listen dual m) should resolve to card_src_tar
        assert touches[0].artifacts["card"] == card_path

    def test_passive_touch_2_resolves_card_jp(self, tmp_path):
        card_jp = tmp_path / "card_tar.png"
        card_jp.touch()
        ci = _compiled(_noun("cat"), Phase.NOUNS, card_tar=card_jp)
        touches = compile_touches([ci], PASSIVE_VIDEO)
        # Touch 2 (listen reverse f) should resolve to card_tar
        assert touches[1].artifacts["card"] == card_jp

    def test_active_touch_resolves_audio_jp_f(self, tmp_path):
        audio = tmp_path / "audio.mp3"
        audio.touch()
        ci = _compiled(_noun("cat"), Phase.NOUNS, audio_tar_f=audio)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        # All active noun touches use audio_tar_f
        assert touches[0].artifacts["audio"] == [audio]

    def test_passive_listen_resolves_three_audio_files(self, tmp_path):
        en = tmp_path / "en.mp3"
        jp_m = tmp_path / "jp_m.mp3"
        jp_f = tmp_path / "jp_f.mp3"
        for p in (en, jp_m, jp_f):
            p.touch()
        ci = _compiled(
            _noun("cat"), Phase.NOUNS,
            audio_src=en, audio_tar_m=jp_m, audio_tar_f=jp_f,
        )
        touches = compile_touches([ci], PASSIVE_VIDEO)
        # Touch 1 (listen dual m) → [en, jp_m, jp_f]
        assert touches[0].artifacts["audio"] == [en, jp_m, jp_f]

    def test_missing_assets_resolve_to_none(self):
        ci = _compiled(_noun("cat"), Phase.NOUNS)
        touches = compile_touches([ci], ACTIVE_FLASH_CARDS)
        assert touches[0].artifacts["card"] is None
        assert touches[0].artifacts["audio"] == []


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
