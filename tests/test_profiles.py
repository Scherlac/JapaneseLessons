"""Unit tests for jlesson.profiles — profile definitions and asset requirements."""

import pytest

from jlesson.models import Phase, RepetitionStep, TouchIntent, TouchType
from jlesson.profiles import (
    ACTIVE_FLASH_CARDS,
    PASSIVE_VIDEO,
    PROFILES,
    TOUCH_TYPE_ASSETS,
    TOUCH_TYPE_AUDIO,
    TOUCH_TYPE_CARD,
    Profile,
    get_profile,
)


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------


def test_registry_contains_both_profiles():
    assert "passive_video" in PROFILES
    assert "active_flash_cards" in PROFILES


def test_get_profile_returns_correct_profile():
    p = get_profile("passive_video")
    assert p.name == "passive_video"


def test_get_profile_raises_on_unknown():
    with pytest.raises(KeyError):
        get_profile("nonexistent")


# ---------------------------------------------------------------------------
# Passive Video profile
# ---------------------------------------------------------------------------


class TestPassiveVideo:
    def test_noun_cycle_length(self):
        assert len(PASSIVE_VIDEO.cycle_for(Phase.NOUNS)) == 3

    def test_verb_cycle_length(self):
        assert len(PASSIVE_VIDEO.cycle_for(Phase.VERBS)) == 3

    def test_grammar_cycle_length(self):
        assert len(PASSIVE_VIDEO.cycle_for(Phase.GRAMMAR)) == 2

    def test_noun_cycle_types(self):
        types = [s.touch_type for s in PASSIVE_VIDEO.cycle_for(Phase.NOUNS)]
        assert types == [
            TouchType.LISTEN_EN_JPM_JPF,
            TouchType.LISTEN_JPF_JPM,
            TouchType.LISTEN_EN_JPM_JPF,
        ]

    def test_noun_cycle_intents(self):
        intents = [s.intent for s in PASSIVE_VIDEO.cycle_for(Phase.NOUNS)]
        assert intents == [
            TouchIntent.INTRODUCE,
            TouchIntent.REINFORCE,
            TouchIntent.LOCK_IN,
        ]

    def test_grammar_first_touch_is_translate(self):
        step = PASSIVE_VIDEO.cycle_for(Phase.GRAMMAR)[0]
        assert step.intent == TouchIntent.TRANSLATE

    def test_total_touches_6n_6v_9g(self):
        """6 nouns × 3 + 6 verbs × 3 + 9 grammar × 2 = 54."""
        total = (
            6 * len(PASSIVE_VIDEO.cycle_for(Phase.NOUNS))
            + 6 * len(PASSIVE_VIDEO.cycle_for(Phase.VERBS))
            + 9 * len(PASSIVE_VIDEO.cycle_for(Phase.GRAMMAR))
        )
        assert total == 54

    def test_required_assets_nouns(self):
        assets = PASSIVE_VIDEO.required_assets(Phase.NOUNS)
        assert "card_en_jp" in assets
        assert "card_jp" in assets
        assert "audio_en" in assets
        assert "audio_jp_f" in assets
        assert "audio_jp_m" in assets

    def test_required_assets_grammar(self):
        assets = PASSIVE_VIDEO.required_assets(Phase.GRAMMAR)
        assert "card_en_jp" in assets
        assert "audio_en" in assets
        assert "audio_jp_f" in assets


# ---------------------------------------------------------------------------
# Active Flash Cards profile
# ---------------------------------------------------------------------------


class TestActiveFlashCards:
    def test_noun_cycle_length(self):
        assert len(ACTIVE_FLASH_CARDS.cycle_for(Phase.NOUNS)) == 5

    def test_verb_cycle_length(self):
        assert len(ACTIVE_FLASH_CARDS.cycle_for(Phase.VERBS)) == 5

    def test_grammar_cycle_length(self):
        assert len(ACTIVE_FLASH_CARDS.cycle_for(Phase.GRAMMAR)) == 3

    def test_noun_cycle_types(self):
        types = [s.touch_type for s in ACTIVE_FLASH_CARDS.cycle_for(Phase.NOUNS)]
        assert types == [
            TouchType.EN_JP,
            TouchType.JP_EN,
            TouchType.EN_JP,
            TouchType.JP_JP,
            TouchType.EN_JP,
        ]

    def test_noun_cycle_intents(self):
        intents = [s.intent for s in ACTIVE_FLASH_CARDS.cycle_for(Phase.NOUNS)]
        assert intents == [
            TouchIntent.INTRODUCE,
            TouchIntent.RECALL,
            TouchIntent.REINFORCE,
            TouchIntent.CONFIRM,
            TouchIntent.LOCK_IN,
        ]

    def test_total_touches_6n_6v_9g(self):
        """6 nouns × 5 + 6 verbs × 5 + 9 grammar × 3 = 87."""
        total = (
            6 * len(ACTIVE_FLASH_CARDS.cycle_for(Phase.NOUNS))
            + 6 * len(ACTIVE_FLASH_CARDS.cycle_for(Phase.VERBS))
            + 9 * len(ACTIVE_FLASH_CARDS.cycle_for(Phase.GRAMMAR))
        )
        assert total == 87

    def test_required_assets_nouns(self):
        assets = ACTIVE_FLASH_CARDS.required_assets(Phase.NOUNS)
        assert "card_en" in assets
        assert "card_jp" in assets
        assert "audio_jp_f" in assets
        # Active cards don't use EN audio or JP male for nouns
        assert "audio_en" not in assets
        assert "audio_jp_m" not in assets


# ---------------------------------------------------------------------------
# Touch type mappings
# ---------------------------------------------------------------------------


class TestTouchTypeMappings:
    def test_all_touch_types_have_assets(self):
        for tt in TouchType:
            assert tt in TOUCH_TYPE_ASSETS

    def test_all_touch_types_have_card(self):
        for tt in TouchType:
            assert tt in TOUCH_TYPE_CARD

    def test_all_touch_types_have_audio(self):
        for tt in TouchType:
            assert tt in TOUCH_TYPE_AUDIO

    def test_en_jp_assets(self):
        assert TOUCH_TYPE_ASSETS[TouchType.EN_JP] == {"card_en", "card_jp", "audio_jp_f"}

    def test_listen_en_jpm_jpf_assets(self):
        assert TOUCH_TYPE_ASSETS[TouchType.LISTEN_EN_JPM_JPF] == {
            "card_en_jp", "audio_en", "audio_jp_m", "audio_jp_f",
        }

    def test_en_jp_card_is_en(self):
        assert TOUCH_TYPE_CARD[TouchType.EN_JP] == "card_en"

    def test_jp_en_card_is_jp(self):
        assert TOUCH_TYPE_CARD[TouchType.JP_EN] == "card_jp"

    def test_listen_audio_order(self):
        assert TOUCH_TYPE_AUDIO[TouchType.LISTEN_EN_JPM_JPF] == [
            "audio_en", "audio_jp_m", "audio_jp_f",
        ]


# ---------------------------------------------------------------------------
# Profile.cycle_for edge cases
# ---------------------------------------------------------------------------


def test_cycle_for_missing_phase_returns_empty():
    """A custom profile missing a phase should return an empty cycle."""
    p = Profile(name="empty", cycles={})
    assert p.cycle_for(Phase.NOUNS) == []


def test_required_assets_empty_when_no_cycle():
    p = Profile(name="empty", cycles={})
    assert p.required_assets(Phase.NOUNS) == set()
