from __future__ import annotations

import jlesson.touch_compiler as touch_compiler
from jlesson.profiles import get_profile

from ..pipeline_core import ActionConfig, CompiledItemSequence, StepAction, TouchSequence


class CompileTouchesAction(StepAction[CompiledItemSequence, TouchSequence]):
    """Compile a profile-specific touch sequence from compiled render items."""

    def run(self, config: ActionConfig, chunk: CompiledItemSequence) -> TouchSequence:
        profile = get_profile(config.lesson.profile)
        touches = touch_compiler.compile_touches(chunk.items, profile)
        return TouchSequence(items=touches)