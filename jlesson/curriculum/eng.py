"""
Hungarian-English grammar progression table.

Provides the ordered, prerequisite-aware grammar sequence for the
hun-eng language pair (Hungarian-speaking children learning English,
ages 8-12).  26 grammar points across 6 prerequisite-aware levels.
"""

from __future__ import annotations

from ..models import GrammarItem


# ── Grammar Progression — Hungarian → English (levels 1-6) ───────────────────

ENG_GRAMMAR_PROGRESSION: list[GrammarItem] = [
    # ── Level 1 — absolute beginner, no prerequisites ────────────────────────
    GrammarItem(
        id="present_simple_affirmative",
        pattern="Subject + verb + object",
        description="Simple present tense — affirmative",
        example_target="I eat bread.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="identity_is_am_are",
        pattern="Subject + is/am/are + noun/adjective",
        description="Identity / description with be-verb",
        example_target="She is a teacher.",
        requires=[],
        level=1,
    ),
    # ── Level 2 — requires Level 1 ───────────────────────────────────────────
    GrammarItem(
        id="present_simple_negative",
        pattern="Subject + do/does not + verb",
        description="Simple present tense — negative",
        example_target="I do not eat fish.",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="present_simple_question",
        pattern="Do/Does + subject + verb?",
        description="Simple present tense — yes/no question",
        example_target="Do you like cats?",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="can_ability",
        pattern="Subject + can + verb",
        description="Ability with can",
        example_target="I can swim fast.",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="have_got",
        pattern="Subject + have/has got + noun",
        description="Possession with have got",
        example_target="I have got a dog.",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    # ── Level 3 — requires Level 2 ───────────────────────────────────────────
    GrammarItem(
        id="present_continuous",
        pattern="Subject + is/am/are + verb-ing",
        description="Present continuous — action happening now",
        example_target="I am eating now.",
        requires=["present_simple_affirmative", "identity_is_am_are"],
        level=3,
    ),
    GrammarItem(
        id="present_continuous_question",
        pattern="Is/Am/Are + subject + verb-ing?",
        description="Present continuous — yes/no question",
        example_target="Are you eating now?",
        requires=["present_continuous", "present_simple_question"],
        level=3,
    ),
    GrammarItem(
        id="present_continuous_negative",
        pattern="Subject + is/am/are not + verb-ing",
        description="Present continuous — negative",
        example_target="She is not eating right now.",
        requires=["present_continuous", "present_simple_negative"],
        level=3,
    ),
    GrammarItem(
        id="there_is_are",
        pattern="There is/are + noun",
        description="Existence — there is / there are",
        example_target="There is a cat on the table.",
        requires=["identity_is_am_are"],
        level=3,
    ),
    # ── Level 4 — requires Level 3 ───────────────────────────────────────────
    GrammarItem(
        id="past_simple_affirmative",
        pattern="Subject + past verb + object",
        description="Simple past tense — affirmative",
        example_target="I ate bread yesterday.",
        requires=["present_simple_affirmative"],
        level=4,
    ),
    GrammarItem(
        id="past_simple_negative",
        pattern="Subject + did not + verb",
        description="Simple past tense — negative",
        example_target="I did not eat fish.",
        requires=["past_simple_affirmative", "present_simple_negative"],
        level=4,
    ),
    GrammarItem(
        id="past_simple_question",
        pattern="Did + subject + verb?",
        description="Simple past tense — yes/no question",
        example_target="Did you run today?",
        requires=["past_simple_affirmative", "present_simple_question"],
        level=4,
    ),
    GrammarItem(
        id="be_was_were",
        pattern="Subject + was/were + noun/adjective",
        description="Past tense of be — was / were",
        example_target="They were happy last week.",
        requires=["identity_is_am_are", "past_simple_affirmative"],
        level=4,
    ),
    GrammarItem(
        id="regular_verbs_formation",
        pattern="Base verb + -ed",
        description="Regular past tense formation — add -ed",
        example_target="walk → walked, play → played",
        requires=["past_simple_affirmative"],
        level=4,
    ),
    GrammarItem(
        id="irregular_verbs_3forms_1",
        pattern="base / past / past participle",
        description="Common irregular verbs — three forms (set 1)",
        example_target="go/went/gone, eat/ate/eaten",
        requires=["past_simple_affirmative"],
        level=4,
    ),
    # ── Level 5 — requires Level 4 ───────────────────────────────────────────
    GrammarItem(
        id="past_continuous",
        pattern="Subject + was/were + verb-ing",
        description="Past continuous — action was happening",
        example_target="I was eating when you called.",
        requires=["present_continuous", "past_simple_affirmative"],
        level=5,
    ),
    GrammarItem(
        id="past_continuous_question",
        pattern="Was/Were + subject + verb-ing?",
        description="Past continuous — yes/no question",
        example_target="Were you eating when I called?",
        requires=["past_continuous", "past_simple_question"],
        level=5,
    ),
    GrammarItem(
        id="past_continuous_negative",
        pattern="Subject + was/were not + verb-ing",
        description="Past continuous — negative",
        example_target="She was not eating when I arrived.",
        requires=["past_continuous", "past_simple_negative"],
        level=5,
    ),
    GrammarItem(
        id="irregular_verbs_3forms_2",
        pattern="base / past / past participle",
        description="More irregular verbs — three forms (set 2)",
        example_target="see/saw/seen, take/took/taken",
        requires=["irregular_verbs_3forms_1"],
        level=5,
    ),
    GrammarItem(
        id="will_future",
        pattern="Subject + will + verb",
        description="Simple future with will",
        example_target="I will eat later.",
        requires=["present_simple_affirmative"],
        level=5,
    ),
    GrammarItem(
        id="going_to_future",
        pattern="Subject + is/am/are going to + verb",
        description="Near future with going to",
        example_target="I am going to eat lunch.",
        requires=["present_continuous"],
        level=5,
    ),
    # ── Level 6 — requires Level 5 ───────────────────────────────────────────
    GrammarItem(
        id="comparisons",
        pattern="noun + is + adjective-er + than + noun",
        description="Comparatives — comparing two things",
        example_target="The dog is bigger than the cat.",
        requires=["identity_is_am_are"],
        level=6,
    ),
    GrammarItem(
        id="present_perfect",
        pattern="Subject + has/have + past participle",
        description="Present perfect — completed action with current relevance",
        example_target="I have eaten already.",
        requires=["past_simple_affirmative", "irregular_verbs_3forms_1"],
        level=6,
    ),
    GrammarItem(
        id="first_conditional",
        pattern="If + present, subject + will + verb",
        description="First conditional — real possibility",
        example_target="If it rains, I will stay home.",
        requires=["will_future", "present_simple_affirmative"],
        level=6,
    ),
    GrammarItem(
        id="must_should",
        pattern="Subject + must/should + verb",
        description="Obligation and advice — must / should",
        example_target="You must study every day.",
        requires=["present_simple_affirmative", "can_ability"],
        level=6,
    ),
]

HUN_TO_ENG_GRAMMAR_PROGRESSION = ENG_GRAMMAR_PROGRESSION  # backward compat
