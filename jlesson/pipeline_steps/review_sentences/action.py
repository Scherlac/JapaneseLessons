"""Stateless sentence review action.

``ReviewSentencesAction`` takes a ``SentenceReviewBatch`` — a typed chunk
carrying sentences from ``NarrativeGrammarStep`` alongside the vocabulary and
grammar context needed to build the review prompt.

Using ``Sentence`` as the batch item type (``ItemBatch[Sentence]``) makes the
inter-step dependency explicit at the type level:

    NarrativeGrammarStep → list[Sentence] → ReviewSentencesStep

The action works entirely in local (intra-batch) index space.  The enclosing
``ReviewSentencesStep.merge_outputs`` is responsible for mapping local indices
back to global sentence positions for logging and the report section.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from jlesson.models import GeneralItem, GrammarItem, Sentence
from ..pipeline_core import ActionConfig, ItemBatch, StepAction

NATURALNESS_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Chunk type
# ---------------------------------------------------------------------------

@dataclass
class SentenceReviewBatch(ItemBatch[Sentence]):
    """Input chunk for ``ReviewSentencesAction``.

    Extends ``ItemBatch[Sentence]`` with the vocabulary and grammar context
    needed to build the review prompt.  Using ``Sentence`` — the output item
    type of ``NarrativeGrammarStep`` — as the batch item type makes the
    inter-step dependency explicit:

        NarrativeGrammarStep → list[Sentence] → ReviewSentencesStep

    Context fields
    --------------
    items               list[Sentence]
        Sliced from ``LessonContext.sentences`` (up to ``BATCH_SIZE`` per
        chunk).  These are the artifacts ``NarrativeGrammarStep`` produced.
    nouns               list[GeneralItem]
        From ``LessonContext.nouns``; passed unchanged to the prompt builder.
    verbs               list[GeneralItem]
        From ``LessonContext.verbs``; passed unchanged to the prompt builder.
    selected_grammar    list[GrammarItem]
        From ``LessonContext.selected_grammar``; needed by the review prompt.
    """

    nouns: list[GeneralItem] = field(default_factory=list)
    verbs: list[GeneralItem] = field(default_factory=list)
    selected_grammar: list[GrammarItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class SentenceRevisionRecord:
    """One revision applied during review, for logging in ``merge_outputs``.

    Carries the local (intra-batch) index so ``merge_outputs`` can compute
    the global sentence position as ``batch_offset + local_index``.
    """

    local_index: int
    score: int | float
    original_text: str


@dataclass
class SentenceReviewResult:
    """Typed output of ``ReviewSentencesAction``.

    One result per ``SentenceReviewBatch``.

    sentences   list[Sentence]
        Possibly-revised sentences for this batch.  ``merge_outputs``
        concatenates these across all batches to rebuild ``ctx.sentences``.
    reviews     list[dict]
        Raw LLM review records for report generation.  Indices are
        local (intra-batch); ``merge_outputs`` adjusts them to global
        positions before building the report section.
    revisions   list[SentenceRevisionRecord]
        Per-revision records capturing the local index, score, and original
        text for step-level logging in ``merge_outputs``.

    Context field: ``LessonContext.sentences``  (reassembled by ``merge_outputs``)
    """

    sentences: list[Sentence]
    reviews: list[dict]
    revisions: list[SentenceRevisionRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class ReviewSentencesAction(StepAction[SentenceReviewBatch, SentenceReviewResult]):
    """Rate sentences for naturalness and optionally rewrite awkward ones.

    Input
    -----
    chunk : SentenceReviewBatch
        One batch of ``Sentence`` items (up to ``BATCH_SIZE``) with the
        noun/verb/grammar context needed for the review prompt.  ``Sentence``
        is the direct output item type of ``NarrativeGrammarStep``, making
        the inter-step dependency visible in the chunk's type parameter.

    Output
    ------
    SentenceReviewResult
        Possibly-revised sentences for the batch, the raw LLM review records,
        and per-revision records for logging in ``merge_outputs``.

    The action normalises any dict sentences (retrieval may return untyped
    data) before building the prompt.  All revision decisions use local
    (intra-batch) indices; the step's ``merge_outputs`` handles the global
    offset.
    """

    def run(self, config: ActionConfig, chunk: SentenceReviewBatch) -> SentenceReviewResult:
        sentences = [
            config.language.generator.convert_sentence(s) if isinstance(s, dict) else s
            for s in chunk.items
        ]

        prompt = config.language.prompts.build_sentence_review_prompt(
            sentences,
            chunk.nouns,
            chunk.verbs,
            chunk.selected_grammar,
        )
        result = config.runtime.call_llm(prompt)
        reviews = result.get("reviews", [])

        revised = list(sentences)
        revisions: list[SentenceRevisionRecord] = []

        for review in reviews:
            idx = review.get("index")
            score = review.get("score", 5)
            revised_source = review.get("revised_sentence")
            if (
                idx is not None
                and score < NATURALNESS_THRESHOLD
                and isinstance(revised_source, dict)
                and 0 <= idx < len(revised)
            ):
                original_text = revised[idx].source.display_text
                new_sentence = config.language.generator.convert_sentence(revised_source)
                new_sentence.block_index = revised[idx].block_index
                new_sentence.phase = revised[idx].phase
                revised[idx] = new_sentence
                revisions.append(SentenceRevisionRecord(
                    local_index=idx,
                    score=score,
                    original_text=original_text,
                ))

        return SentenceReviewResult(sentences=revised, reviews=reviews, revisions=revisions)
