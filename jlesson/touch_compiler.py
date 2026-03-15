"""
Touch compiler — Stage 3 of the compilation pipeline.

Takes a list of CompiledItem objects and a Profile, and produces a flat,
ordered list of Touch objects — interleaved by round — ready for output
rendering.

The ordering follows the "round-robin by touch index" pattern described
in docs/structure.md:

    item₁ touch 1   ← round 1
    item₂ touch 1
    item₁ touch 2   ← round 2
    item₂ touch 2
    ...

Each phase (nouns, verbs, grammar) is compiled independently and the
results are concatenated in phase order.

Usage:
    from jlesson.touch_compiler import compile_touches
    touches = compile_touches(compiled_items, profile)
"""

from __future__ import annotations

from .models import CompiledItem, Phase, Touch, TouchType
from .profiles import TOUCH_TYPE_AUDIO, TOUCH_TYPE_CARD, Profile


def _resolve_card(compiled: CompiledItem, touch_type: TouchType):
    """Return the card Path for *touch_type* from the compiled item's assets."""
    asset_key = TOUCH_TYPE_CARD[touch_type]
    return getattr(compiled.assets, asset_key, None)


def _resolve_audio(compiled: CompiledItem, touch_type: TouchType) -> list:
    """Return ordered audio Paths for *touch_type* from the compiled item's assets."""
    keys = TOUCH_TYPE_AUDIO[touch_type]
    paths = []
    for key in keys:
        path = getattr(compiled.assets, key, None)
        if path is not None:
            paths.append(path)
    return paths


def compile_touches(
    compiled_items: list[CompiledItem],
    profile: Profile,
) -> list[Touch]:
    """Compile a flat, round-interleaved touch sequence.

    Parameters
    ----------
    compiled_items : list of CompiledItem objects (output of Stage 2)
    profile : Profile rulebook with repetition cycles per phase

    Returns
    -------
    list[Touch] — ordered sequence ready for rendering
    """
    # Build a global index for each compiled item
    index_map: dict[int, int] = {id(ci): i for i, ci in enumerate(compiled_items)}

    touches: list[Touch] = []

    for phase in (Phase.NOUNS, Phase.VERBS, Phase.GRAMMAR):
        phase_items = [ci for ci in compiled_items if ci.phase == phase]
        cycle = profile.cycle_for(phase)

        if not phase_items or not cycle:
            continue

        # Round-robin: for each touch index in the cycle, iterate all items
        for touch_idx, step in enumerate(cycle, 1):
            for ci in phase_items:
                touches.append(
                    Touch(
                        compiled_item_index=index_map[id(ci)],
                        touch_index=touch_idx,
                        touch_type=step.touch_type,
                        intent=step.intent,
                        card_path=_resolve_card(ci, step.touch_type),
                        audio_paths=_resolve_audio(ci, step.touch_type),
                    )
                )

    return touches


def count_touches(
    n_nouns: int,
    n_verbs: int,
    n_sentences: int,
    profile: Profile,
) -> dict[str, int]:
    """Return touch counts per phase and total for the given profile."""
    noun_t = n_nouns * len(profile.cycle_for(Phase.NOUNS))
    verb_t = n_verbs * len(profile.cycle_for(Phase.VERBS))
    grammar_t = n_sentences * len(profile.cycle_for(Phase.GRAMMAR))
    return {
        "nouns": noun_t,
        "verbs": verb_t,
        "grammar": grammar_t,
        "total": noun_t + verb_t + grammar_t,
    }
