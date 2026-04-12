"""Action: resolve canonical lesson block into language-specific lesson block."""

from __future__ import annotations

from typing import Any

from jlesson.models import CanonicalItem, GeneralItem, Phase, PartialItem

from ..pipeline_core import (
    ActionConfig,
    StepAction,
    CanonicalLessonBlock,
    LessonBlock,
)
from .prompt import build_item_resolve_prompt


class LessonPlannerAction(StepAction[CanonicalLessonBlock, LessonBlock]):
    """Resolve a single canonical block into a language-specific lesson block.

    Each canonical item (English-only) is sent to the LLM along with its
    narrative context.  The LLM returns source/target pairs enriched with
    pronunciation, display text, and TTS text for the configured language pair.
    """

    def run(self, config: ActionConfig, input: CanonicalLessonBlock) -> LessonBlock:
        lang = config.language.code

        # --- RCM cache lookup ---
        cached: list[GeneralItem] = []
        uncached_sequences: dict[Phase, list[CanonicalItem]] = {}
        if config.rcm is not None:
            for phase, items in input.content_sequences.items():
                for canonical_item in items:
                    gi = config.rcm.get_branch(canonical_item.id, lang)
                    if gi is not None:
                        cached.append(gi)
                    else:
                        uncached_sequences.setdefault(phase, []).append(canonical_item)
        else:
            uncached_sequences = dict(input.content_sequences)

        # Build an input block with only uncached items for the LLM
        newly_resolved: list[GeneralItem] = []
        if uncached_sequences:
            modified_input = input.model_copy(update={"content_sequences": uncached_sequences})
            prompt = build_item_resolve_prompt(
                source_language=config.language.source.display_name,
                target_language=config.language.target.display_name,
                canonical_language=config.language.canonical_language,
                block_index=modified_input.block_index,
                narrative_content=modified_input.narrative.narrative,
                grammar_ids=modified_input.grammar_ids,
                content_sequences=modified_input.content_sequences,
                source_config=config.language.source,
                target_config=config.language.target,
            )
            raw = config.runtime.call_llm(prompt)
            lesson_block = self._parse_response(raw, modified_input)
            for phase_items in lesson_block.content_sequences.values():
                newly_resolved.extend(phase_items)

            # Persist new resolutions to RCM
            if config.rcm is not None:
                for gi in newly_resolved:
                    if gi.canonical is not None:
                        config.rcm.upsert_item(gi.canonical)
                    config.rcm.upsert_branch(gi.id, lang, gi)
                trace = config.runtime.latest_llm_trace()
                if trace is not None and newly_resolved:
                    config.rcm.record_item_llm_usage(trace, lang, newly_resolved)

        # Merge cached + newly resolved into a single LessonBlock
        all_items = cached + newly_resolved
        content_sequences: dict[Phase, list[GeneralItem]] = {}
        for gi in all_items:
            phase = gi.phase or Phase.UNKNOWN
            content_sequences.setdefault(phase, []).append(gi)
        for phase in input.content_sequences:
            content_sequences.setdefault(phase, [])

        return LessonBlock(
            block_index=input.block_index,
            grammar_ids=list(input.grammar_ids),
            content_sequences=content_sequences,
        )

    @staticmethod
    def _parse_response(
        raw: dict[str, Any],
        canonical_block: CanonicalLessonBlock,
    ) -> LessonBlock:
        """Parse LLM JSON response into a ``LessonBlock``."""
        resolved_items: list[GeneralItem] = []
        for item_raw in raw.get("items", []):
            source_raw = item_raw.get("source", {})
            target_raw = item_raw.get("target", {})
            canonical_raw = item_raw.get("canonical", {})

            item_phase = Phase(item_raw["phase"]) if item_raw.get("phase") else None
            canonical_id = canonical_raw.get("id", "") or item_raw.get("id", "")
            general_item = GeneralItem(
                id=canonical_id,
                phase=item_phase,
                block_index=canonical_block.block_index,
                canonical=CanonicalItem(
                    id=canonical_id,
                    text=canonical_raw.get("text", ""),
                    gloss=canonical_raw.get("gloss", ""),
                    type=item_phase or Phase.UNKNOWN,
                ),
                source=PartialItem(
                    text=source_raw.get("text", ""),
                    display_text=source_raw.get("display_text", ""),
                    tts_text=source_raw.get("tts_text", ""),
                    pronunciation=source_raw.get("pronunciation", ""),
                    extra=source_raw.get("extra", {}),
                ),
                target=PartialItem(
                    text=target_raw.get("text", ""),
                    display_text=target_raw.get("display_text", ""),
                    tts_text=target_raw.get("tts_text", ""),
                    pronunciation=target_raw.get("pronunciation", ""),
                    extra=target_raw.get("extra", {}),
                ),
            )
            resolved_items.append(general_item)

        # Group resolved items by phase, matching the canonical block's structure
        content_sequences: dict[Phase, list[GeneralItem]] = {}
        for item in resolved_items:
            phase = item.phase or Phase.UNKNOWN
            content_sequences.setdefault(phase, []).append(item)

        # Preserve phase ordering from canonical block even if LLM omitted some phases
        for phase in canonical_block.content_sequences:
            content_sequences.setdefault(phase, [])

        return LessonBlock(
            block_index=canonical_block.block_index,
            grammar_ids=list(canonical_block.grammar_ids),
            content_sequences=content_sequences,
        )
