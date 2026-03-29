"""
English-Japanese grammar progression table and derived helpers.

Provides the ordered, prerequisite-aware grammar sequence for the
eng-jap language pair, plus convenience wrappers (get_next_grammar,
get_grammar_by_id, summary) that default to this progression.
"""

from __future__ import annotations

from ..models import GrammarItem
from ._base import CurriculumData, create_curriculum, get_next_grammar_from, grammar_summary_lines


# ── Grammar Progression — English → Japanese (levels 1-4) ────────────────────
# "level" is a rough JLPT-aligned difficulty bucket (1 = absolute beginner).

ENG_TO_JAP_GRAMMAR_PROGRESSION: list[GrammarItem] = [
    # ── Level 1 — absolute beginner, no prerequisites ────────────────────────
    GrammarItem(
        id="action_present_affirmative",
        pattern="Subject + object + verb (polite)",
        description="Subject does verb to object — present affirmative (polite)",
        example_source="I eat fish.",
        example_target="私は魚を食べます。",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="identity_present_affirmative",
        pattern="Subject + は + noun + です",
        description="A is B — identity / description sentence",
        example_source="This is bread.",
        example_target="これはパンです。",
        requires=[],
        level=1,
    ),
    # ── Level 2 — requires one level-1 milestone ─────────────────────────────
    GrammarItem(
        id="action_present_negative",
        pattern="Subject + object + verb + ません",
        description="Subject does NOT verb object — present negative (polite)",
        example_source="He does not eat meat.",
        example_target="彼は肉を食べません。",
        requires=["action_present_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="action_past_affirmative",
        pattern="Subject + object + verb + ました",
        description="Subject did verb to object — past affirmative (polite)",
        example_source="I drank water.",
        example_target="私は水を飲みました。",
        requires=["action_present_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="question_ka",
        pattern="Sentence + か",
        description="Yes/no question — append か to any polite sentence",
        example_source="Do you drink tea?",
        example_target="あなたはお茶を飲みますか。",
        requires=["action_present_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="direction_ni_ikimasu",
        pattern="Direction + に/へ + 行きます",
        description="Subject goes to destination — destination particle に/へ",
        example_source="I go to the station.",
        example_target="私は駅に行きます。",
        requires=["action_present_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="existence_arimasu",
        pattern="Location + に + object + が + あります",
        description="There is X at/in Y — inanimate objects (あります)",
        example_source="There is bread on the table.",
        example_target="テーブルにパンがあります。",
        requires=["action_present_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="adjective_na",
        pattern="Subject + は + な-adjective + です",
        description="な-adjective predicate — subject is [な-adjective]",
        example_source="I like this dish.",
        example_target="この料理は好きです。",
        requires=["identity_present_affirmative"],
        level=2,
    ),
    # ── Level 3 — requires two level-2 milestones ────────────────────────────
    GrammarItem(
        id="action_past_negative",
        pattern="Subject + object + verb + ませんでした",
        description="Subject did NOT verb object — past negative (polite)",
        example_source="I did not eat vegetables yesterday.",
        example_target="私は昨日野菜を食べませんでした。",
        requires=["action_present_negative", "action_past_affirmative"],
        level=3,
    ),
    GrammarItem(
        id="desire_tai",
        pattern="Subject + verb-stem + たいです",
        description="Subject wants to do verb — verb stem + たいです",
        example_source="I want to drink tea.",
        example_target="私はお茶を飲みたいです。",
        requires=["action_present_affirmative", "action_present_negative"],
        level=3,
    ),
    GrammarItem(
        id="desire_hoshii",
        pattern="Subject + object + が + ほしいです",
        description="Subject wants noun — subject が ほしいです",
        example_source="I want water.",
        example_target="私は水がほしいです。",
        requires=["action_present_affirmative"],
        level=3,
    ),
    GrammarItem(
        id="reason_kara",
        pattern="Clause + から",
        description="Because … — append から to a clause to give a reason",
        example_source="Because I am hungry, I eat rice.",
        example_target="お腹が空いていますから、ご飯を食べます。",
        requires=["action_present_affirmative", "action_present_negative"],
        level=3,
    ),
    # ── Level 4 — intermediate────────────────────────────────────────────────
    GrammarItem(
        id="te_form_request",
        pattern="Verb-te + ください",
        description="Please do verb — て-form + ください",
        example_source="Please eat the bread.",
        example_target="パンを食べてください。",
        requires=["action_present_affirmative", "desire_tai"],
        level=4,
    ),
    GrammarItem(
        id="te_form_progressive",
        pattern="Verb-te + います",
        description="Subject is doing verb — て-form + います (continuous aspect)",
        example_source="He is eating rice now.",
        example_target="彼は今ご飯を食べています。",
        requires=["te_form_request"],
        level=4,
    ),
    GrammarItem(
        id="potential_dekimasu",
        pattern="Verb-potential + ます/できます",
        description="Subject can do verb — potential form / できます",
        example_source="I can speak Japanese.",
        example_target="私は日本語が話せます。",
        requires=["action_present_affirmative", "action_present_negative"],
        level=4,
    ),
]

# Backward-compat alias — existing code imports GRAMMAR_PROGRESSION everywhere.
GRAMMAR_PROGRESSION = ENG_TO_JAP_GRAMMAR_PROGRESSION

# Fast lookup by id.
_GRAMMAR_BY_ID: dict[str, GrammarItem] = {g.id: g for g in GRAMMAR_PROGRESSION}


# ── Convenience wrappers with eng-jap defaults ────────────────────────────────

def get_next_grammar(covered_grammar_ids: list[str]) -> list[GrammarItem]:
    """Return grammar steps that are unlocked but not yet covered (eng-jap).

    A step is unlocked when all its prerequisites appear in covered_grammar_ids.
    Results are sorted by level (easiest first).
    """
    return get_next_grammar_from(GRAMMAR_PROGRESSION, covered_grammar_ids)


def get_grammar_by_id(grammar_id: str) -> GrammarItem:
    """Return an eng-jap grammar spec by its id.  Raises KeyError if not found."""
    if grammar_id not in _GRAMMAR_BY_ID:
        raise KeyError(f"Unknown grammar id: {grammar_id!r}")
    return _GRAMMAR_BY_ID[grammar_id]


def summary(curriculum: dict) -> str:
    """Return a human-readable curriculum summary string (eng-jap grammar)."""
    lines = [
        f"Curriculum: {curriculum['name']}",
        f"  Total lessons : {len(curriculum['lessons'])}",
        f"  Covered nouns : {len(curriculum['covered_nouns'])}",
        f"  Covered verbs : {len(curriculum['covered_verbs'])}",
        f"  Grammar done  : {len(curriculum['covered_grammar_ids'])}",
    ]

    if curriculum["lessons"]:
        lines.append("")
        lines.append("  Lessons:")
        for lesson in curriculum["lessons"]:
            icon = "✅" if lesson["status"] == "completed" else "📝"
            grammar_str = ", ".join(lesson["grammar_ids"]) or "—"
            lines.append(
                f"    {icon} #{lesson['id']:02d}  {lesson['title']}"
                f"  ({lesson['items_count']} items | grammar: {grammar_str})"
            )

    unlocked = get_next_grammar(curriculum["covered_grammar_ids"])
    if unlocked:
        lines.append("")
        lines.append(f"  Next available grammar ({len(unlocked)} steps unlocked):")
        for g in unlocked[:5]:
            lines.append(f"    \u2022 [{g.level}] {g.id}: {g.description}")
        if len(unlocked) > 5:
            lines.append(f"    … and {len(unlocked) - 5} more")
    else:
        lines.append("")
        lines.append("  All grammar steps have been covered — curriculum complete!")

    return "\n".join(lines)
