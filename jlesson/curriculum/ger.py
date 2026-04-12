"""
Hungarian-German grammar progression table.

Provides the ordered, prerequisite-aware grammar sequence for the
hun-ger language pair (Hungarian-speaking children learning German,
ages 8-12).  26 grammar points across 6 prerequisite-aware levels.
"""

from __future__ import annotations

from ..models import GrammarItem


# ── Grammar Progression — Hungarian → German (levels 1-6) ────────────────────

GER_GRAMMAR_PROGRESSION: list[GrammarItem] = [
    # ── Level 1 — absolute beginner, no prerequisites ────────────────────────
    GrammarItem(
        id="present_simple_affirmative",
        pattern="Subject + Verb + Object",
        description="Present simple — affirmative",
        example_target="Ich esse Brot.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="identity_sein",
        pattern="Subject + sein + Noun/Adjective",
        description="Identity / description with sein",
        example_target="Sie ist Lehrerin.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="articles_der_die_das",
        pattern="der/die/das + Noun",
        description="Definite articles — der, die, das",
        example_target="der Hund, die Katze, das Haus",
        requires=[],
        level=1,
    ),
    # ── Level 2 — requires Level 1 ───────────────────────────────────────────
    GrammarItem(
        id="present_simple_negative",
        pattern="Subject + Verb + nicht + Object",
        description="Present simple — negation with nicht/kein",
        example_target="Ich esse keinen Fisch.",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="present_simple_question",
        pattern="Verb + Subject + Object?",
        description="Present simple — yes/no question (inversion)",
        example_target="Magst du Katzen?",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="koennen_ability",
        pattern="Subject + können + Infinitive",
        description="Ability with können",
        example_target="Ich kann schnell schwimmen.",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="haben_possession",
        pattern="Subject + haben + Accusative",
        description="Possession with haben",
        example_target="Ich habe einen Hund.",
        requires=["present_simple_affirmative", "articles_der_die_das"],
        level=2,
    ),
    GrammarItem(
        id="akkusativ_basics",
        pattern="den/die/das/einen/eine/ein + Noun",
        description="Accusative — direct object",
        example_target="Ich sehe den Hund.",
        requires=["articles_der_die_das"],
        level=2,
    ),
    # ── Level 3 — requires Level 2 ───────────────────────────────────────────
    GrammarItem(
        id="dativ_basics",
        pattern="dem/der/dem/einem/einer/einem + Noun",
        description="Dative — indirect object",
        example_target="Ich gebe dem Hund einen Knochen.",
        requires=["akkusativ_basics"],
        level=3,
    ),
    GrammarItem(
        id="trennbare_verben",
        pattern="Subject + Prefix-Verb … Prefix",
        description="Separable verbs — verb bracket",
        example_target="Ich stehe jeden Tag früh auf.",
        requires=["present_simple_affirmative"],
        level=3,
    ),
    GrammarItem(
        id="w_fragen",
        pattern="W-Word + Verb + Subject?",
        description="W-questions — wer, was, wo, wann, warum, wie",
        example_target="Wo wohnst du?",
        requires=["present_simple_question"],
        level=3,
    ),
    GrammarItem(
        id="es_gibt",
        pattern="Es gibt + Accusative",
        description="Existence — es gibt",
        example_target="Es gibt eine Katze auf dem Tisch.",
        requires=["akkusativ_basics"],
        level=3,
    ),
    GrammarItem(
        id="moechten_wollen",
        pattern="Subject + möchten/wollen + Infinitive",
        description="Wishes with möchten and wollen",
        example_target="Ich möchte ein Eis.",
        requires=["present_simple_affirmative"],
        level=3,
    ),
    # ── Level 4 — requires Level 3 ───────────────────────────────────────────
    GrammarItem(
        id="perfekt_haben",
        pattern="Subject + haben + … + Past Participle",
        description="Perfekt with haben — past",
        example_target="Ich habe gestern Brot gegessen.",
        requires=["present_simple_affirmative", "haben_possession"],
        level=4,
    ),
    GrammarItem(
        id="perfekt_sein",
        pattern="Subject + sein + … + Past Participle",
        description="Perfekt with sein — movement/change of state",
        example_target="Ich bin gestern gelaufen.",
        requires=["perfekt_haben", "identity_sein"],
        level=4,
    ),
    GrammarItem(
        id="perfekt_negative",
        pattern="Subject + haben/sein + nicht + Past Participle",
        description="Perfekt — negation",
        example_target="Ich habe keinen Fisch gegessen.",
        requires=["perfekt_haben", "present_simple_negative"],
        level=4,
    ),
    GrammarItem(
        id="perfekt_question",
        pattern="Haben/Sein + Subject + … + Past Participle?",
        description="Perfekt — yes/no question",
        example_target="Bist du heute gelaufen?",
        requires=["perfekt_haben", "present_simple_question"],
        level=4,
    ),
    GrammarItem(
        id="regelmaessige_partizipien",
        pattern="ge- + Stem + -t",
        description="Regular past participle formation",
        example_target="spielen → gespielt, machen → gemacht",
        requires=["perfekt_haben"],
        level=4,
    ),
    GrammarItem(
        id="unregelmaessige_partizipien_1",
        pattern="ge- + Stem + -en (vowel change)",
        description="Irregular past participles — set 1",
        example_target="gehen/gegangen, essen/gegessen",
        requires=["perfekt_haben"],
        level=4,
    ),
    # ── Level 5 — requires Level 4 ───────────────────────────────────────────
    GrammarItem(
        id="praeteritum_sein_haben",
        pattern="Subject + war/hatte + …",
        description="Präteritum of sein and haben",
        example_target="Sie waren letzte Woche glücklich.",
        requires=["identity_sein", "haben_possession"],
        level=5,
    ),
    GrammarItem(
        id="muessen_sollen",
        pattern="Subject + müssen/sollen + Infinitive",
        description="Obligation and advice — müssen / sollen",
        example_target="Du musst jeden Tag lernen.",
        requires=["koennen_ability"],
        level=5,
    ),
    GrammarItem(
        id="unregelmaessige_partizipien_2",
        pattern="ge- + Stem + -en (vowel change)",
        description="More irregular past participles — set 2",
        example_target="sehen/gesehen, nehmen/genommen",
        requires=["unregelmaessige_partizipien_1"],
        level=5,
    ),
    GrammarItem(
        id="werden_future",
        pattern="Subject + werden + … + Infinitive",
        description="Future I with werden",
        example_target="Ich werde später essen.",
        requires=["present_simple_affirmative"],
        level=5,
    ),
    # ── Level 6 — requires Level 5 ───────────────────────────────────────────
    GrammarItem(
        id="komparativ_superlativ",
        pattern="Adjective-er / am Adjective-sten",
        description="Comparative and superlative",
        example_target="Der Hund ist größer als die Katze.",
        requires=["identity_sein"],
        level=6,
    ),
    GrammarItem(
        id="weil_nebensatz",
        pattern="…, weil + Subject + … + Verb",
        description="Causal clause with weil — verb at the end",
        example_target="Ich bleibe zu Hause, weil es regnet.",
        requires=["present_simple_affirmative"],
        level=6,
    ),
    GrammarItem(
        id="wenn_conditional",
        pattern="Wenn + Subject + … + Verb, Verb + Subject",
        description="Conditional clause with wenn",
        example_target="Wenn es regnet, bleibe ich zu Hause.",
        requires=["werden_future", "present_simple_affirmative"],
        level=6,
    ),
]

HUN_TO_GER_GRAMMAR_PROGRESSION = GER_GRAMMAR_PROGRESSION  # backward compat
