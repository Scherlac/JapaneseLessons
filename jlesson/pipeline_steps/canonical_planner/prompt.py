"""Language-agnostic prompts for the two-pass lesson planner."""

from __future__ import annotations

from dataclasses import dataclass

from jlesson.models import CanonicalItem, GrammarItem, Phase
from jlesson.pipeline_steps.pipeline_core import NarrativeBlock


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


PHASE_PARSE_DETAILS = {
    Phase.NOUNS: {
        "name": "noun",
        "description": "nouns",
        "field": "noun_items",
        "is_vocab": True,
        "is_grammar": False,
        "json_template_example": '"noun_items": {"house": "place of residence", "tree": "tall plant with branches and leaves"}',
    },
    Phase.VERBS: {
        "name": "verb",
        "description": "verbs",
        "field": "verb_items",
        "is_vocab": True,
        "is_grammar": False,
        "json_template_example": '"verb_items": {"to move": "action of changing location or position."}',
    },
    Phase.ADJECTIVES: {
        "name": "adjective",
        "description": "adjectives",
        "field": "adjective_items",
        "is_vocab": True,
        "is_grammar": False,
        "json_template_example": '"adjective_items": {"big": "large size or extent."}',
    },
    Phase.GRAMMAR: {
        "name": "grammar sentence",
        "description": "sentences adherent to the grammar points being practised in the block",
        "field": "grammar_list",
        "is_vocab": False,
        "is_grammar": True,
        "json_template_example": '"grammar_list": ["I eat an apple.", "She goes to school."]',
    },
    Phase.NARRATIVE: {
        "name": "story narrative",
        "description": "exciting narrative content that motivates learners keeping up with the lessons",
        "field": "narrative_list",
        "is_vocab": False,
        "is_grammar": False,
        "json_template_example": '"narrative_list": ["Once upon a time...", "In a faraway land..."]',
    },
}


def build_lesson_plan_prompt(
    *,
    lesson_number: int,
    lesson_blocks: int,
    narrative_blocks: list[NarrativeBlock],
    unlocked_grammar: list[GrammarItem],
    covered_grammar: list[GrammarCoverageInfo],
    grammar_points_per_lesson: int,
    grammar_points_per_block: int,
    content_sequences: dict[Phase, list[CanonicalItem]],
    content_counts: dict[Phase, int],
    canonical_language: str = "english",
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


    narrative_section = "\n\n".join(
        f"--- Block {i + 1} ---\n"
        f"    Narrative: {block.narrative}\n" if block.narrative else ""
        f"    Alignment Notes: {block.alignment_notes}\n" if block.alignment_notes else ""
        f"    Sentiment: {block.sentiment}" if block.sentiment else ""
        for i, block in enumerate(narrative_blocks)
    )

    dynamic_item_counts_str = ", ".join(
        f"{PHASE_PARSE_DETAILS[phase]['name'].capitalize()}s: {content_counts.get(phase, 0)}"
        for phase in Phase
        if PHASE_PARSE_DETAILS[phase]["is_vocab"]
    )
    dynamic_vocab_str = "\n".join(
        f"  - {PHASE_PARSE_DETAILS[phase]['name'].capitalize()}s:\n"
        + "\n".join(
            f"    - {item.text}: {item.gloss}"
            for item in content_sequences.get(phase, [])
        )
        for phase in Phase
        if PHASE_PARSE_DETAILS[phase]["is_vocab"]
    )

    dynamic_json_template_example = ",\n      ".join(
        PHASE_PARSE_DETAILS[phase]["json_template_example"]
        for phase in Phase
    )

    dynamic_json_item_list = ", ".join(
        PHASE_PARSE_DETAILS[phase]["field"]
        for phase in Phase
        if content_counts.get(phase, 0) > 0
    )

    dynamic_planning_constraints = "\n".join(
        f"- Plan {content_counts.get(phase, 0)} {PHASE_PARSE_DETAILS[phase]['description']} according to the lesson narrative "
        f"and distribute them across the blocks using the {PHASE_PARSE_DETAILS[phase]['field']} field in the JSON response."
        for phase in Phase
        if content_counts.get(phase, 0) > 0
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
2. Balancing vocabulary across blocks — no block should be overloaded.
3. Making sure every grammar point appears in at least {grammar_points_per_block} blocks
   to give learners enough practice.
4. Ensuring sentence alignment across blocks is consistent and logical given the narrative flow.
5. Avoid spoiling the narrative, add believable backstory to support the grammar and
   vocabulary choices, but do not alter or break any narrative content that was not in the narrative blocks.
6. Checking that each block has close to the required item counts:
{dynamic_item_counts_str}
"""

    return f"""\
You are a lesson planner for an educational language course.
You are planning lesson {lesson_number} which has {lesson_blocks} blocks.

Main goal to design a lesson plan that effectively teaches the unlocked grammar points
while creating engaging and motivating content for learners. 
Use believable and exciting narrative or small backstory if needed to keep learners hooked, but do not
sacrifice the quality of grammar practice. The narrative shall follow the one provided in the narrative blocks, 
but you can add believable backstory to support the grammar and vocabulary choices, as long as you do not alter
or break any narrative content that was not in the narrative blocks.
Follow the constraints carefully, especially the Fibonacci learning cycle for spaced repetition of grammar points.

{FIBONACCI_CYCLE_DESCRIPTION}

ALREADY COVERED GRAMMAR (from previous lessons, with Fibonacci pacing stage):
{covered_lines}

AVAILABLE VOCABULARY:
{dynamic_vocab_str}

UNLOCKED GRAMMAR POINTS (prerequisites met, ready to teach):
{grammar_lines}

NARRATIVE BLOCKS:
{narrative_section}

CONSTRAINTS:
- Select exactly {grammar_points_per_lesson} grammar points for this lesson
  (or all available if fewer than {grammar_points_per_lesson} are unlocked).
- Each block should practise up to {grammar_points_per_block} grammar points.
{dynamic_planning_constraints}
- Distribute grammar across blocks following Fibonacci pacing:
  introduce a grammar point, then repeat it in subsequent blocks with
  gradually increasing gaps.
- Assign items to blocks so they align with the narrative content
  and the grammar being practised.
- IMPORTANT: All {dynamic_json_item_list} MUST be in {canonical_language}.
  This is a canonical (language-neutral) plan. Use plain {canonical_language} words
  (e.g. "house", "father", "tree", "to move", "to find"). Do NOT use any
  target-language words in the suggestions.
{revision_section}
Return ONLY a raw JSON object — no markdown fences, no commentary:
{{
  "grammar_ids": ["<id1>", "<id2>", ...],
  "rationale": "Brief explanation of grammar selection and pacing strategy.",
  "blocks": [
    {{
      "block_index": 1,
      "grammar_ids": ["<id1>"],
      {dynamic_json_template_example},
      "narrative_content": "Brief description of the narrative content covered in this block",
      "alignment_notes": "Optional notes on added backstory to support grammar/vocab choices",
      "sentiment": "Optional sentiment or tone label for the block, e.g. 'mysterious', 'heartwarming', 'tense', etc."
    }}
  ]
}}
""".strip()
