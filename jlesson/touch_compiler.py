"""
Touch compiler — Stage 3 of the compilation pipeline.

Takes a list of GeneralItem objects and a Profile, and produces a flat,
ordered list of Touch objects — interleaved by round — ready for output
rendering.

The ordering follows the "round-robin by touch index" pattern described
in docs/structure.md:

    item₁ touch 1   ← round 1
    item₂ touch 1
    item₁ touch 2   ← round 2
    item₂ touch 2
    ...

Items are interleaved in phase batches (nouns → verbs → grammar) based on
profile batch sizes. This avoids large uninterrupted phase blocks and yields
a more balanced learning flow.

Usage:
    from jlesson.touch_compiler import compile_touches
    touches = compile_touches(compiled_items, profile)
"""

from __future__ import annotations

from .models import GeneralItem, Phase, Touch, TouchType
from .profiles import TOUCH_TYPE_AUDIO, TOUCH_TYPE_CARD, Profile


def _resolve_card(item: GeneralItem, touch_type: TouchType):
    """Return the card Path for *touch_type* from the item's assets."""
    asset_key = TOUCH_TYPE_CARD[touch_type]
    if asset_key in item.source.assets:
        return item.source.assets[asset_key]
    elif asset_key in item.target.assets:
        return item.target.assets[asset_key]
    return None


def _resolve_audio(item: GeneralItem, touch_type: TouchType) -> list:
    """Return ordered audio Paths for *touch_type* from the item's assets."""
    keys = TOUCH_TYPE_AUDIO[touch_type]
    paths = []
    for key in keys:
        if key in item.source.assets:
            paths.append(item.source.assets[key])
        elif key in item.target.assets:
            paths.append(item.target.assets[key])
    return paths


def compile_touches(
    compiled_items: list[GeneralItem],
    profile: Profile,
) -> list[Touch]:
    """Compile a flat, ordered touch sequence.

    Parameters
    ----------
    compiled_items : list of GeneralItem objects (output of Stage 2)
    profile : Profile rulebook with repetition cycles per phase

    Returns
    -------
    list[Touch] — ordered sequence ready for rendering
    """
    touches: list[Touch] = []
    # Derive phase order from the profile so any phase with a cycle is included
    # (e.g. ADJECTIVES, NARRATIVE) without requiring manual updates here.
    phase_order = [p for p in Phase if profile.cycle_for(p)]
    block_indices = sorted({max(1, getattr(ci, "block_index", 1)) for ci in compiled_items})

    for block_index in block_indices:
        phase_queues: dict[Phase, list[GeneralItem]] = {
            phase: [
                ci for ci in compiled_items
                if ci.phase == phase and max(1, getattr(ci, "block_index", 1)) == block_index
            ]
            for phase in phase_order
        }

        while any(phase_queues[p] for p in phase_order):
            for phase in phase_order:
                queue = phase_queues[phase]
                if not queue:
                    continue
                batch_size = profile.batch_size_for(phase)
                batch = queue[:batch_size]
                del queue[:batch_size]

                for ci in batch:
                    cycle = profile.cycle_for(phase)

                    for touch_idx, step in enumerate(cycle, 1):
                        touch = Touch(
                            touch_index=touch_idx,
                            phase=phase,
                            item=ci,
                            touch_type=step.touch_type,
                            intent=step.intent,
                            artifacts={},
                        )
                        touch.artifacts["card"] = _resolve_card(ci, step.touch_type)
                        touch.artifacts["audio"] = _resolve_audio(ci, step.touch_type)
                        touches.append(touch)

    return touches


def count_touches(
    n_nouns: int,
    n_verbs: int,
    n_sentences: int,
    profile: Profile,
    n_adjectives: int = 0,
) -> dict[str, int]:
    """Return touch counts per phase and total for the given profile."""
    noun_t = n_nouns * len(profile.cycle_for(Phase.NOUNS))
    verb_t = n_verbs * len(profile.cycle_for(Phase.VERBS))
    adj_t = n_adjectives * len(profile.cycle_for(Phase.ADJECTIVES))
    grammar_t = n_sentences * len(profile.cycle_for(Phase.GRAMMAR))
    return {
        "nouns": noun_t,
        "verbs": verb_t,
        "adjectives": adj_t,
        "grammar": grammar_t,
        "total": noun_t + verb_t + adj_t + grammar_t,
    }
