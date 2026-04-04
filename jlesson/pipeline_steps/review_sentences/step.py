from __future__ import annotations

from ..pipeline_core import ActionStep, LessonContext
from .action import ReviewSentencesAction, SentenceReviewBatch, SentenceReviewResult

BATCH_SIZE = 30


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


class ReviewSentencesStep(ActionStep[SentenceReviewBatch, SentenceReviewResult]):
    """Step — LLM: rate sentences for naturalness, rewrite awkward ones.

    Inter-step type alignment
    -------------------------
    ``SentenceReviewBatch`` extends ``ItemBatch[Sentence]``, where ``Sentence``
    is the direct output item type of ``NarrativeGrammarStep``.
    ``build_input`` wraps ``ctx.sentences`` — the list ``NarrativeGrammarStep``
    produced — into batches of at most ``BATCH_SIZE``, attaching the
    noun/verb/grammar context needed by the review prompt.

    This makes the inter-step dependency visible in the type signature:

        NarrativeGrammarStep → list[Sentence] → ReviewSentencesStep

    Outputs
    -------
    One ``SentenceReviewResult`` per batch → reassembled into ``ctx.sentences``
    by ``merge_output``.
    """

    name = "review_sentences"
    description = "LLM: review sentence naturalness + rewrite"

    @property
    def action(self) -> ReviewSentencesAction:
        return ReviewSentencesAction()

    def should_skip(self, ctx: LessonContext) -> bool:
        if not ctx.sentences:
            self._log(ctx, "       (no sentences to review)")
            return True
        return False

    def build_input(self, ctx: LessonContext) -> list[SentenceReviewBatch]:
        return [
            SentenceReviewBatch(
                batch_index=i,
                block_index=-1,
                items=ctx.sentences[start : start + BATCH_SIZE],
                nouns=list(ctx.nouns),
                verbs=list(ctx.verbs),
                selected_grammar=list(ctx.selected_grammar),
            )
            for i, start in enumerate(range(0, len(ctx.sentences), BATCH_SIZE))
        ]

    def merge_output(
        self, ctx: LessonContext, outputs: list[SentenceReviewResult]
    ) -> LessonContext:
        ctx.review_results = outputs

        all_reviews: list[dict] = []
        total_revised = 0
        for batch_index, result in enumerate(outputs):
            batch_offset = batch_index * BATCH_SIZE
            for review in result.reviews:
                if isinstance(review.get("index"), int):
                    review = dict(review, index=review["index"] + batch_offset)
                all_reviews.append(review)
            for revision in result.revisions:
                global_idx = batch_offset + revision.local_index
                self._log(
                    ctx,
                    f"       [{global_idx}] score {revision.score}"
                    f" - revised: {revision.original_text!r}",
                )
            total_revised += len(result.revisions)

        overall = "?"
        if all_reviews:
            scores = [
                r.get("score", 5)
                for r in all_reviews
                if isinstance(r.get("score"), (int, float))
            ]
            overall = f"{sum(scores) / len(scores):.1f}" if scores else "?"
        self._log(
            ctx,
            f"       {len(ctx.sentences)} sentences reviewed"
            f" (naturalness: {overall}/5, revised: {total_revised})",
        )

        if total_revised > 0:
            ctx.report.add("review_notes", _review_section(all_reviews, total_revised))

        return ctx
