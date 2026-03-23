from __future__ import annotations

from .pipeline_core import LessonContext, PipelineStep
from .pipeline_grammar import coerce_grammar_items
from .pipeline_gadgets import PipelineGadgets


class ReviewSentencesStep(PipelineStep):
    """Step 4 — LLM: rate sentences for naturalness, rewrite awkward ones."""

    name = "review_sentences"
    description = "LLM: review sentence naturalness + rewrite"

    NATURALNESS_THRESHOLD = 3
    BATCH_SIZE = 30  # max sentences per LLM call

    def execute(self, ctx: LessonContext) -> LessonContext:
        if not ctx.sentences:
            self._log(ctx, "       (no sentences to review)")
            return ctx

        for index, sentence in enumerate(ctx.sentences):
            if isinstance(sentence, dict):
                ctx.sentences[index] = ctx.language_config.generator.convert_sentence(sentence)

        noun_items = [ctx.language_config.generator.convert_raw_noun(n) for n in ctx.nouns]
        verb_items = [ctx.language_config.generator.convert_raw_verb(v) for v in ctx.verbs]

        all_reviews: list[dict] = []
        for batch_start in range(0, len(ctx.sentences), self.BATCH_SIZE):
            batch = ctx.sentences[batch_start: batch_start + self.BATCH_SIZE]
            prompt = ctx.language_config.prompts.build_sentence_review_prompt(
                batch,
                noun_items,
                verb_items,
                coerce_grammar_items(ctx.selected_grammar),
            )
            result = PipelineGadgets.ask_llm(ctx, prompt)
            for review in result.get("reviews", []):
                # Offset review index back to global sentence index
                if isinstance(review.get("index"), int):
                    review = dict(review, index=review["index"] + batch_start)
                all_reviews.append(review)

        revised_count = 0
        for review in all_reviews:
            idx = review.get("index")
            score = review.get("score", 5)
            revised = review.get("revised_sentence")
            if (
                idx is not None
                and score < self.NATURALNESS_THRESHOLD
                and isinstance(revised, dict)
                and 0 <= idx < len(ctx.sentences)
            ):
                original_en = ctx.sentences[idx].source.display_text
                original_sentence = ctx.sentences[idx]
                revised_sentence = ctx.language_config.generator.convert_sentence(revised)
                revised_sentence.block_index = original_sentence.block_index
                revised_sentence.phase = original_sentence.phase
                ctx.sentences[idx] = revised_sentence
                revised_count += 1
                self._log(
                    ctx,
                    f"       [{idx}] score {score} - revised: {original_en!r}",
                )

        overall = "?"
        if all_reviews:
            scores = [r.get("score", 5) for r in all_reviews if isinstance(r.get("score"), (int, float))]
            overall = f"{sum(scores) / len(scores):.1f}" if scores else "?"
        self._log(
            ctx,
            f"       {len(ctx.sentences)} sentences reviewed "
            f"(naturalness: {overall}/5, revised: {revised_count})",
        )

        if revised_count > 0:
            ctx.report.add(
                "review_notes",
                self._review_section(all_reviews, revised_count),
            )
        return ctx

    @staticmethod
    def _review_section(reviews: list[dict], revised_count: int) -> str:
        lines = [
            "## Sentence Review",
            "",
            f"> {revised_count} sentence(s) revised for naturalness.",
            "",
        ]
        for review in reviews:
            score = review.get("score", "?")
            issue = review.get("issue")
            if issue:
                lines.append(f"- **[{review.get('index', '?')}]** score {score}: {issue}")
        lines.append("")
        return "\n".join(lines)