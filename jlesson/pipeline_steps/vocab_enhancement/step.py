from __future__ import annotations

from jlesson.models import GeneralItem, Phase

from ..pipeline_core import ActionStep, LessonContext, VocabEnhancementArtifact
from .action import VocabEnhancementAction, VocabEnhancementRequest


class VocabEnhancementStep(ActionStep[VocabEnhancementRequest, VocabEnhancementArtifact]):
    """Merged noun/verb enrichment step following selected vocab."""

    name = "vocab_enhancement"
    description = "LLM: enrich selected vocabulary with examples, tips, and forms"
    enabled_parts: tuple[str, ...] = ("nouns", "verbs")
    _action = VocabEnhancementAction()

    @property
    def action(self) -> VocabEnhancementAction:
        return self._action

    def should_skip(self, ctx: LessonContext) -> bool:
        pending_parts = self._pending_parts(ctx)
        if not pending_parts:
            if self.enabled_parts == ("nouns",):
                self._log(ctx, "       using retrieved noun items")
            elif self.enabled_parts == ("verbs",):
                self._log(ctx, "       using retrieved verb items")
            else:
                self._log(ctx, "       using retrieved vocab enhancement")
            return True
        return False

    def build_chunks(self, ctx: LessonContext) -> list[VocabEnhancementRequest]:
        return [
            VocabEnhancementRequest(
                vocab=ctx.vocab,
                nouns=list(ctx.nouns),
                verbs=list(ctx.verbs),
                lesson_number=len(ctx.curriculum.lessons) + 1,
                enabled_parts=self._pending_parts(ctx),
            )
        ]

    def merge_outputs(self, ctx: LessonContext, outputs: list[VocabEnhancementArtifact]) -> LessonContext:
        result = outputs[-1]
        pending_parts = self._pending_parts(ctx)
        src_lbl = ctx.language_config.source_label
        tgt_lbl = ctx.language_config.target_label
        ph_lbl = ctx.language_config.phonetic_label
        has_phonetic = bool(ph_lbl)

        if "nouns" in pending_parts:
            ctx.noun_items = list(result.noun_items)
            for index, item in enumerate(ctx.noun_items):
                item.phase = Phase.NOUNS
                item.block_index = index // max(1, ctx.config.num_nouns) + 1
            self._log(ctx, f"       {len(ctx.noun_items)} noun items")
            ctx.report.add("vocabulary", self._noun_vocab_table(ctx.noun_items, src_lbl, tgt_lbl, ph_lbl, has_phonetic))
            ctx.report.add("noun_practice", self._noun_practice_section(ctx.noun_items, tgt_lbl, ph_lbl))

        if "verbs" in pending_parts:
            ctx.verb_items = list(result.verb_items)
            for index, item in enumerate(ctx.verb_items):
                item.phase = Phase.VERBS
                item.block_index = index // max(1, ctx.config.num_verbs) + 1
            self._log(ctx, f"       {len(ctx.verb_items)} verb items")
            special_labels = ctx.language_config.target_special_labels
            ctx.report.add(
                "vocabulary",
                self._verb_vocab_table(ctx.verb_items, src_lbl, tgt_lbl, ph_lbl, has_phonetic, special_labels),
            )
            ctx.report.add(
                "verb_practice",
                self._verb_practice_section(ctx.verb_items, tgt_lbl, ph_lbl, special_labels),
            )

        return ctx

    def _pending_parts(self, ctx: LessonContext) -> tuple[str, ...]:
        pending: list[str] = []
        if "nouns" in self.enabled_parts and not ctx.noun_items:
            pending.append("nouns")
        if "verbs" in self.enabled_parts and not ctx.verb_items:
            pending.append("verbs")
        return tuple(pending)

    @staticmethod
    def _noun_vocab_table(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool) -> str:
        header = f"| # | {src_lbl} | {tgt_lbl} |"
        sep = "|---|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        lines = ["## Vocabulary", "", "### Nouns", ""]
        by_block: dict[int, list[GeneralItem]] = {}
        for item in items:
            by_block.setdefault(max(1, item.block_index), []).append(item)
        for block_index in sorted(by_block):
            if len(by_block) > 1:
                lines.extend([f"#### Block {block_index}", ""])
            lines.extend([header, sep])
            for index, item in enumerate(by_block[block_index], 1):
                row = f"| {index} | {item.source.display_text} | {item.target.display_text} |"
                if has_phonetic and item.target.pronunciation:
                    row += f" {item.target.pronunciation} |"
                lines.append(row)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _noun_practice_section(items: list[GeneralItem], tgt_lbl: str, ph_lbl: str) -> str:
        lines: list[str] = ["## Phase 1 - Noun Practice", ""]
        by_block: dict[int, list[GeneralItem]] = {}
        for item in items:
            by_block.setdefault(max(1, item.block_index), []).append(item)
        for block_index in sorted(by_block):
            if len(by_block) > 1:
                lines.extend([f"### Block {block_index}", ""])
            for index, item in enumerate(by_block[block_index], 1):
                lines.extend([f"#### {index}. {item.source.display_text}" if len(by_block) > 1 else f"### {index}. {item.source.display_text}", ""])
                lines.append(f"- **{tgt_lbl}:** {item.target.display_text}")
                if item.target.pronunciation:
                    lines.append(f"- **{ph_lbl}:** {item.target.pronunciation}")
                if item.target.extra.get("example_sentence_target"):
                    lines.append(f"- **Example:** {item.target.extra['example_sentence_target']}")
                if item.target.extra.get("example_sentence_source"):
                    lines.append(f"  *{item.target.extra['example_sentence_source']}*")
                if item.target.extra.get("memory_tip"):
                    lines.append(f"- **Memory tip:** {item.target.extra['memory_tip']}")
                lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _verb_vocab_table(items: list[GeneralItem], src_lbl: str, tgt_lbl: str, ph_lbl: str, has_phonetic: bool, special_labels: dict[str, str]) -> str:
        header = f"| # | {src_lbl} | {tgt_lbl} |"
        sep = "|---|---------|----------|"
        if has_phonetic:
            header += f" {ph_lbl} |"
            sep += "--------|"
        for label in special_labels.values():
            header += f" {label} |"
            sep += "-------------|"
        lines = ["### Verbs", ""]
        by_block: dict[int, list[GeneralItem]] = {}
        for item in items:
            by_block.setdefault(max(1, item.block_index), []).append(item)
        for block_index in sorted(by_block):
            if len(by_block) > 1:
                lines.extend([f"#### Block {block_index}", ""])
            lines.extend([header, sep])
            for index, item in enumerate(by_block[block_index], 1):
                row = f"| {index} | {item.source.display_text} | {item.target.display_text} |"
                if has_phonetic and item.target.pronunciation:
                    row += f" {item.target.pronunciation} |"
                for role in special_labels:
                    row += f" {item.target.extra.get(role, '')} |"
                lines.append(row)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _verb_practice_section(items: list[GeneralItem], tgt_lbl: str, ph_lbl: str, special_labels: dict[str, str]) -> str:
        lines: list[str] = ["## Phase 2 - Verb Practice", ""]
        by_block: dict[int, list[GeneralItem]] = {}
        for item in items:
            by_block.setdefault(max(1, item.block_index), []).append(item)
        for block_index in sorted(by_block):
            if len(by_block) > 1:
                lines.extend([f"### Block {block_index}", ""])
            for index, item in enumerate(by_block[block_index], 1):
                lines.extend([f"#### {index}. {item.source.display_text}" if len(by_block) > 1 else f"### {index}. {item.source.display_text}", ""])
                lines.append(f"- **{tgt_lbl}:** {item.target.display_text}")
                if item.target.pronunciation:
                    lines.append(f"- **{ph_lbl}:** {item.target.pronunciation}")
                for role, label in special_labels.items():
                    value = item.target.extra.get(role)
                    if value:
                        lines.append(f"- **{label}:** {value}")
                polite = item.target.extra.get("polite_forms", {})
                if polite:
                    for form_name, form_value in polite.items():
                        lines.append(f"  - {form_name}: {form_value}")
                if item.target.extra.get("example_sentence_target"):
                    lines.append(f"- **Example:** {item.target.extra['example_sentence_target']}")
                if item.target.extra.get("example_sentence_source"):
                    lines.append(f"  *{item.target.extra['example_sentence_source']}*")
                if item.target.extra.get("memory_tip"):
                    lines.append(f"- **Memory tip:** {item.target.extra['memory_tip']}")
                lines.append("")
        return "\n".join(lines)


class NounPracticeStep(VocabEnhancementStep):
    name = "noun_practice"
    description = "LLM: enrich nouns with examples + memory tips"
    enabled_parts = ("nouns",)


class VerbPracticeStep(VocabEnhancementStep):
    name = "verb_practice"
    description = "LLM: enrich verbs with conjugations + memory tips"
    enabled_parts = ("verbs",)