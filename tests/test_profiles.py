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
            TouchType.LISTEN_DUAL_M,
            TouchType.LISTEN_REVERSE_F,
            TouchType.LISTEN_DUAL_M,
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
        assert "card_src_tar" in assets
        assert "card_tar" in assets
        assert "audio_src" in assets
        assert "audio_tar_f" in assets
        assert "audio_tar_m" in assets

    def test_required_assets_grammar(self):
        assets = PASSIVE_VIDEO.required_assets(Phase.GRAMMAR)
        assert "card_src_tar" in assets
        assert "audio_src" in assets
        assert "audio_tar_f" in assets


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
            TouchType.SOURCE_TARGET,
            TouchType.TARGET_SOURCE,
            TouchType.SOURCE_TARGET,
            TouchType.TARGET_ONLY,
            TouchType.SOURCE_TARGET,
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
        assert "card_src" in assets
        assert "card_tar" in assets
        assert "audio_tar_f" in assets
        # Active cards don't use src audio or tar male for nouns
        assert "audio_src" not in assets
        assert "audio_tar_m" not in assets


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

    def test_source_target_assets(self):
        assert TOUCH_TYPE_ASSETS[TouchType.SOURCE_TARGET] == {"card_src", "card_tar", "audio_tar_f"}

    def test_listen_dual_m_assets(self):
        assert TOUCH_TYPE_ASSETS[TouchType.LISTEN_DUAL_M] == {
            "card_src_tar", "audio_src", "audio_tar_m", "audio_tar_f",
        }

    def test_source_target_card_is_src(self):
        assert TOUCH_TYPE_CARD[TouchType.SOURCE_TARGET] == "card_src"

    def test_target_source_card_is_tar(self):
        assert TOUCH_TYPE_CARD[TouchType.TARGET_SOURCE] == "card_tar"

    def test_listen_dual_audio_order(self):
        assert TOUCH_TYPE_AUDIO[TouchType.LISTEN_DUAL_M] == [
            "audio_src", "audio_tar_m", "audio_tar_f",
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
