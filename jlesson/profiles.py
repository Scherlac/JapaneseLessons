"""
Profile definitions for the touch system.

A profile is a named rulebook that maps each lesson phase to a repetition cycle.
The repetition cycle is an ordered list of (touch_type, intent) pairs applied to
every item in that phase.

Two profiles are defined:

  - **passive_video** — listen-only; 3 touches per noun/verb, 2 per grammar.
  - **active_flash_cards** — card-based recall; 5 touches per noun/verb, 3 per grammar.

Profiles are pure data — no I/O, no rendering logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Phase, RepetitionStep, TouchIntent, TouchType

# ---------------------------------------------------------------------------
# Profile dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    """Named rulebook: maps phase → repetition cycle."""

    name: str
    cycles: dict[Phase, list[RepetitionStep]] = field(default_factory=dict)

    def cycle_for(self, phase: Phase) -> list[RepetitionStep]:
        """Return the repetition cycle for *phase*."""
        return self.cycles.get(phase, [])

    def required_assets(self, phase: Phase) -> set[str]:
        """Return the set of asset keys needed by all touches in *phase*.

        Asset keys match ItemAssets field names:
        card_en, card_jp, card_en_jp, audio_en, audio_jp_f, audio_jp_m.
        """
        assets: set[str] = set()
        for step in self.cycle_for(phase):
            assets.update(TOUCH_TYPE_ASSETS[step.touch_type])
        return assets


# ---------------------------------------------------------------------------
# Touch type → required assets mapping
# ---------------------------------------------------------------------------

TOUCH_TYPE_ASSETS: dict[TouchType, set[str]] = {
    # Card-based
    TouchType.EN_JP: {"card_en", "card_jp", "audio_jp_f"},
    TouchType.JP_EN: {"card_jp", "card_en", "audio_jp_f"},
    TouchType.JP_JP: {"card_jp", "audio_jp_f"},
    # Listen-first
    TouchType.LISTEN_EN_JPM_JPF: {"card_en_jp", "audio_en", "audio_jp_m", "audio_jp_f"},
    TouchType.LISTEN_JPF_JPM: {"card_jp", "audio_jp_f", "audio_jp_m"},
    TouchType.LISTEN_EN_JPF: {"card_en_jp", "audio_en", "audio_jp_f"},
}

# Resolve card path for each touch type: prompt card shown during the touch.
TOUCH_TYPE_CARD: dict[TouchType, str] = {
    TouchType.EN_JP: "card_en",
    TouchType.JP_EN: "card_jp",
    TouchType.JP_JP: "card_jp",
    TouchType.LISTEN_EN_JPM_JPF: "card_en_jp",
    TouchType.LISTEN_JPF_JPM: "card_jp",
    TouchType.LISTEN_EN_JPF: "card_en_jp",
}

# Resolve ordered audio sequence for each touch type.
TOUCH_TYPE_AUDIO: dict[TouchType, list[str]] = {
    TouchType.EN_JP: ["audio_jp_f"],
    TouchType.JP_EN: ["audio_jp_f"],
    TouchType.JP_JP: ["audio_jp_f"],
    TouchType.LISTEN_EN_JPM_JPF: ["audio_en", "audio_jp_m", "audio_jp_f"],
    TouchType.LISTEN_JPF_JPM: ["audio_jp_f", "audio_jp_m"],
    TouchType.LISTEN_EN_JPF: ["audio_en", "audio_jp_f"],
}


# ---------------------------------------------------------------------------
# Profile: Passive Video
# ---------------------------------------------------------------------------

_PASSIVE_NOUN_VERB_CYCLE = [
    RepetitionStep(touch_type=TouchType.LISTEN_EN_JPM_JPF, intent=TouchIntent.INTRODUCE),
    RepetitionStep(touch_type=TouchType.LISTEN_JPF_JPM, intent=TouchIntent.REINFORCE),
    RepetitionStep(touch_type=TouchType.LISTEN_EN_JPM_JPF, intent=TouchIntent.LOCK_IN),
]

_PASSIVE_GRAMMAR_CYCLE = [
    RepetitionStep(touch_type=TouchType.LISTEN_EN_JPM_JPF, intent=TouchIntent.TRANSLATE),
    RepetitionStep(touch_type=TouchType.LISTEN_EN_JPF, intent=TouchIntent.REINFORCE),
]

PASSIVE_VIDEO = Profile(
    name="passive_video",
    cycles={
        Phase.NOUNS: _PASSIVE_NOUN_VERB_CYCLE,
        Phase.VERBS: _PASSIVE_NOUN_VERB_CYCLE,
        Phase.GRAMMAR: _PASSIVE_GRAMMAR_CYCLE,
    },
)


# ---------------------------------------------------------------------------
# Profile: Active Flash Cards
# ---------------------------------------------------------------------------

_ACTIVE_NOUN_VERB_CYCLE = [
    RepetitionStep(touch_type=TouchType.EN_JP, intent=TouchIntent.INTRODUCE),
    RepetitionStep(touch_type=TouchType.JP_EN, intent=TouchIntent.RECALL),
    RepetitionStep(touch_type=TouchType.EN_JP, intent=TouchIntent.REINFORCE),
    RepetitionStep(touch_type=TouchType.JP_JP, intent=TouchIntent.CONFIRM),
    RepetitionStep(touch_type=TouchType.EN_JP, intent=TouchIntent.LOCK_IN),
]

_ACTIVE_GRAMMAR_CYCLE = [
    RepetitionStep(touch_type=TouchType.EN_JP, intent=TouchIntent.TRANSLATE),
    RepetitionStep(touch_type=TouchType.JP_EN, intent=TouchIntent.COMPREHEND),
    RepetitionStep(touch_type=TouchType.EN_JP, intent=TouchIntent.REINFORCE),
]

ACTIVE_FLASH_CARDS = Profile(
    name="active_flash_cards",
    cycles={
        Phase.NOUNS: _ACTIVE_NOUN_VERB_CYCLE,
        Phase.VERBS: _ACTIVE_NOUN_VERB_CYCLE,
        Phase.GRAMMAR: _ACTIVE_GRAMMAR_CYCLE,
    },
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PROFILES: dict[str, Profile] = {
    PASSIVE_VIDEO.name: PASSIVE_VIDEO,
    ACTIVE_FLASH_CARDS.name: ACTIVE_FLASH_CARDS,
}


def get_profile(name: str) -> Profile:
    """Return a profile by name. Raises KeyError if not found."""
    return PROFILES[name]
