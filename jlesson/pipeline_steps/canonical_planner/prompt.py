"""Language-agnostic prompts for the two-pass lesson planner."""

from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import GrammarItem


# ── Fibonacci learning-cycle stages ──────────────────────────────────────────

FIBONACCI_THRESHOLDS: list[tuple[int, str]] = [
    (21, "mastered — no further repetition needed"),
    (13, "well-known — rare refresh every 13-21 blocks"),
    (8, "reliable short-term — lighter refresh every 8-13 blocks"),
    (5, "consolidating — repeat within 5-8 blocks"),
    (3, "beginning to stick — repeat within 3-5 blocks"),
    (2, "still fragile — repeat within 2-3 blocks"),
    (1, "brand-new — needs immediate repetition in next 1-2 blocks"),
]


def fibonacci_stage_label(times_seen: int) -> str:
    """Return a human-readable Fibonacci pacing label for *times_seen*."""
    for threshold, label in FIBONACCI_THRESHOLDS:
        if times_seen >= threshold:
            return f"{times_seen}× seen: {label}"
    return f"{times_seen}× seen: not yet introduced"


@dataclass(frozen=True)
class GrammarCoverageInfo:
    """Covered grammar ID with Fibonacci pacing metadata."""

    grammar_id: str
    lessons_seen: int
    fibonacci_label: str


# ── Fibonacci learning-cycle reference ───────────────────────────────────────
# Repetition stages expressed as relative encounter counts.
# The planner uses this to decide how densely a grammar point should recur
# across blocks.

FIBONACCI_CYCLE_DESCRIPTION = """\
FIBONACCI LEARNING CYCLE (block repetition guidance):
  Stage 1 — 1× seen:  brand-new item, needs immediate repetition in the next 1-2 blocks
  Stage 2 — 2× seen:  still fragile, repeat within 2-3 blocks
  Stage 3 — 3× seen:  beginning to stick, repeat within 3-5 blocks
  Stage 5 — 5× seen:  consolidating, repeat within 5-8 blocks
  Stage 8 — 8× seen:  reliable short-term, lighter refresh every 8-13 blocks
  Stage 13 — 13× seen: well-known, rare refresh every 13-21 blocks
  Stage 21 — 21× seen: mastered item, no further repetition needed in this lesson

IMPLICATION FOR PLANNING:
  - Items at early stages (1-2× seen) from previous lessons should still
    appear frequently if selected for this lesson.
  - Items at later stages (8-13×) only need rare refreshes.
  - Items at 21×+ can be omitted entirely.
  - A NEW grammar point introduced in this lesson should appear in many
    consecutive blocks at the start.
  - A grammar point introduced mid-lesson needs denser grouping in the blocks
    that follow its first appearance.
  - Multiple grammar points can share a block, but each should follow its own
    Fibonacci pacing independently.\
"""


def build_lesson_plan_prompt(
    *,
    lesson_number: int,
    lesson_blocks: int,
    narrative_blocks: list[str],
    unlocked_grammar: list[GrammarItem],
    covered_grammar: list[GrammarCoverageInfo],
    grammar_points_per_lesson: int,
    grammar_points_per_block: int,
    sentences_per_grammar: int,
    noun_names: list[str],
    verb_names: list[str],
    previous_outline_json: str | None = None,
) -> str:
    """Build the language-agnostic lesson plan prompt.

    Pass 1: ``previous_outline_json`` is ``None`` → draft outline.
    Pass 2: ``previous_outline_json`` is the pass-1 JSON → revised outline.
    """
    grammar_lines = "\n".join(
        f"  - id: {g.id}  |  level: {g.level}  |  requires: {g.requires or '(none)'}\n"
        f"    pattern: {g.pattern}\n"
        f"    description: {g.description}\n"
        f"    example: {g.example_source} → {g.example_target}"
        for g in unlocked_grammar
    )
    if covered_grammar:
        covered_lines = "\n".join(
            f"  - {c.grammar_id}  ({c.fibonacci_label})"
            for c in covered_grammar
        )
    else:
        covered_lines = "  (none)"
    nouns_str = ", ".join(noun_names) if noun_names else "(none)"
    verbs_str = ", ".join(verb_names) if verb_names else "(none)"

    narrative_section = "\n\n".join(
        f"--- Block {i + 1} ---\n{block}"
        for i, block in enumerate(narrative_blocks)
    )

    revision_section = ""
    if previous_outline_json is not None:
        revision_section = f"""

PREVIOUS OUTLINE (pass 1):
{previous_outline_json}

REVISION INSTRUCTIONS:
You are revising your own earlier outline. Improve it by:
1. Ensuring Fibonacci pacing is respected — new grammar appears densely first,
   then spaces out. Check the block assignments above against the cycle table.
2. Verifying that grammar prerequisites are met before a grammar point appears.
3. Balancing vocabulary across blocks — no block should be overloaded.
4. Making sure every grammar point appears in at least {grammar_points_per_block} blocks
   to give learners enough practice.
5. Ensuring sentence counts per block are reasonable and sum correctly.
"""

    return f"""\
You are a lesson planner for an educational language course.
You are planning lesson {lesson_number} which has {lesson_blocks} blocks.

{FIBONACCI_CYCLE_DESCRIPTION}

ALREADY COVERED GRAMMAR (from previous lessons, with Fibonacci pacing stage):
{covered_lines}

AVAILABLE VOCABULARY:
  Nouns: {nouns_str}
  Verbs: {verbs_str}

UNLOCKED GRAMMAR POINTS (prerequisites met, ready to teach):
{grammar_lines}

NARRATIVE BLOCKS:
{narrative_section}

CONSTRAINTS:
- Select exactly {grammar_points_per_lesson} grammar points for this lesson
  (or all available if fewer than {grammar_points_per_lesson} are unlocked).
- Each block should practise up to {grammar_points_per_block} grammar points.
- Plan {sentences_per_grammar} sentences per grammar point per block where that
  grammar point appears.
- Distribute grammar across blocks following Fibonacci pacing:
  introduce a grammar point, then repeat it in subsequent blocks with
  gradually increasing gaps.
- Assign nouns and verbs to blocks so they align with the narrative content
  and the grammar being practised.
{revision_section}
Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "grammar_ids": ["<id1>", "<id2>", ...],
  "rationale": "Brief explanation of grammar selection and pacing strategy.",
  "blocks": [
    {{
      "block_index": 1,
      "grammar_ids": ["<id1>"],
      "noun_suggestions": ["<noun1>", "<noun2>"],
      "verb_suggestions": ["<verb1>"],
      "sentence_count": {sentences_per_grammar},
      "narrative_summary": "One-line summary of this block's narrative."
    }}
  ]
}}
""".strip()
