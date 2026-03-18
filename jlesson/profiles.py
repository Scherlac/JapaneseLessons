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
    batch_sizes: dict[Phase, int] = field(default_factory=dict)

    def cycle_for(self, phase: Phase) -> list[RepetitionStep]:
        """Return the repetition cycle for *phase*."""
        return self.cycles.get(phase, [])

    def batch_size_for(self, phase: Phase) -> int:
        """Return the interleaving batch size for *phase* (minimum 1)."""
        return max(1, self.batch_sizes.get(phase, 1))

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
    TouchType.SOURCE_TARGET: {"card_src", "card_tar", "audio_tar_f"},
    TouchType.TARGET_SOURCE: {"card_tar", "card_src", "audio_tar_f"},
    TouchType.SOURCE_ONLY: {"card_src", "audio_tar_f"},
    TouchType.TARGET_ONLY: {"card_tar", "audio_tar_f"},
    TouchType.LISTEN_DUAL_M: {"card_src_tar", "audio_src", "audio_tar_m", "audio_tar_f"},
    TouchType.LISTEN_DUAL_F: {"card_src_tar", "audio_src", "audio_tar_f"},
    TouchType.LISTEN_REVERSE_M: {"card_tar", "audio_tar_m", "audio_src"},
    TouchType.LISTEN_REVERSE_F: {"card_tar", "audio_tar_f", "audio_tar_m"},
    TouchType.LISTEN_TARGET_M: {"card_tar", "audio_tar_m"},
    TouchType.LISTEN_TARGET_F: {"card_tar", "audio_tar_f"},
}

# Resolve card path for each touch type: prompt card shown during the touch.
TOUCH_TYPE_CARD: dict[TouchType, str] = {
    TouchType.SOURCE_TARGET: "card_src",
    TouchType.TARGET_SOURCE: "card_tar",
    TouchType.SOURCE_ONLY: "card_src",
    TouchType.TARGET_ONLY: "card_tar",
    TouchType.LISTEN_DUAL_M: "card_src_tar",
    TouchType.LISTEN_DUAL_F: "card_src_tar",
    TouchType.LISTEN_REVERSE_M: "card_tar",
    TouchType.LISTEN_REVERSE_F: "card_tar",
    TouchType.LISTEN_TARGET_M: "card_tar",
    TouchType.LISTEN_TARGET_F: "card_tar",
}

# Resolve ordered audio sequence for each touch type.
TOUCH_TYPE_AUDIO: dict[TouchType, list[str]] = {
    TouchType.SOURCE_TARGET: ["audio_tar_f"],
    TouchType.TARGET_SOURCE: ["audio_tar_f"],
    TouchType.SOURCE_ONLY: ["audio_tar_f"],
    TouchType.TARGET_ONLY: ["audio_tar_f"],
    TouchType.LISTEN_DUAL_M: ["audio_src", "audio_tar_m", "audio_tar_f"],
    TouchType.LISTEN_DUAL_F: ["audio_src", "audio_tar_f"],
    TouchType.LISTEN_REVERSE_M: ["audio_tar_m", "audio_src"],
    TouchType.LISTEN_REVERSE_F: ["audio_tar_f", "audio_tar_m"],
    TouchType.LISTEN_TARGET_M: ["audio_tar_m"],
    TouchType.LISTEN_TARGET_F: ["audio_tar_f"],
}


# ---------------------------------------------------------------------------
# Profile: Passive Video
# ---------------------------------------------------------------------------

_PASSIVE_NOUN_VERB_CYCLE = [
    RepetitionStep(touch_type=TouchType.LISTEN_DUAL_M, intent=TouchIntent.INTRODUCE),
    RepetitionStep(touch_type=TouchType.LISTEN_REVERSE_F, intent=TouchIntent.REINFORCE),
    RepetitionStep(touch_type=TouchType.LISTEN_DUAL_M, intent=TouchIntent.LOCK_IN),
]

_PASSIVE_GRAMMAR_CYCLE = [
    RepetitionStep(touch_type=TouchType.LISTEN_DUAL_M, intent=TouchIntent.TRANSLATE),
    RepetitionStep(touch_type=TouchType.LISTEN_DUAL_F, intent=TouchIntent.REINFORCE),
]

PASSIVE_VIDEO = Profile(
    name="passive_video",
    cycles={
        Phase.NOUNS: _PASSIVE_NOUN_VERB_CYCLE,
        Phase.VERBS: _PASSIVE_NOUN_VERB_CYCLE,
        Phase.GRAMMAR: _PASSIVE_GRAMMAR_CYCLE,
    },
    batch_sizes={
        Phase.NOUNS: 4,
        Phase.VERBS: 4,
        Phase.GRAMMAR: 6,
    },
)


# ---------------------------------------------------------------------------
# Profile: Active Flash Cards
# ---------------------------------------------------------------------------

_ACTIVE_NOUN_VERB_CYCLE = [
    RepetitionStep(touch_type=TouchType.SOURCE_TARGET, intent=TouchIntent.INTRODUCE),
    RepetitionStep(touch_type=TouchType.TARGET_SOURCE, intent=TouchIntent.RECALL),
    RepetitionStep(touch_type=TouchType.SOURCE_TARGET, intent=TouchIntent.REINFORCE),
    RepetitionStep(touch_type=TouchType.TARGET_ONLY, intent=TouchIntent.CONFIRM),
    RepetitionStep(touch_type=TouchType.SOURCE_TARGET, intent=TouchIntent.LOCK_IN),
]

_ACTIVE_GRAMMAR_CYCLE = [
    RepetitionStep(touch_type=TouchType.SOURCE_TARGET, intent=TouchIntent.TRANSLATE),
    RepetitionStep(touch_type=TouchType.TARGET_SOURCE, intent=TouchIntent.COMPREHEND),
    RepetitionStep(touch_type=TouchType.SOURCE_TARGET, intent=TouchIntent.REINFORCE),
]

ACTIVE_FLASH_CARDS = Profile(
    name="active_flash_cards",
    cycles={
        Phase.NOUNS: _ACTIVE_NOUN_VERB_CYCLE,
        Phase.VERBS: _ACTIVE_NOUN_VERB_CYCLE,
        Phase.GRAMMAR: _ACTIVE_GRAMMAR_CYCLE,
    },
    batch_sizes={
        Phase.NOUNS: 4,
        Phase.VERBS: 4,
        Phase.GRAMMAR: 6,
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
