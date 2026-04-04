from __future__ import annotations

import jlesson.touch_compiler as touch_compiler
from jlesson.profiles import get_profile

from ..pipeline_core import ActionConfig, GeneralItemSequence, StepAction, TouchSequence


class CompileTouchesAction(StepAction[GeneralItemSequence, TouchSequence]):
    """Compile a profile-specific touch sequence from compiled render items."""

    def run(self, config: ActionConfig, chunk: GeneralItemSequence) -> TouchSequence:
        profile = get_profile(config.lesson.profile)
        touches = touch_compiler.compile_touches(chunk.items, profile)
        return TouchSequence(items=touches)