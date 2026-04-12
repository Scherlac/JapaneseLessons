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
        pattern="Subjekt + Verb + Objekt",
        description="Präsens — Aussagesatz",
        example_target="Ich esse Brot.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="identity_sein",
        pattern="Subjekt + sein + Nomen/Adjektiv",
        description="Identität / Beschreibung mit sein",
        example_target="Sie ist Lehrerin.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="articles_der_die_das",
        pattern="der/die/das + Nomen",
        description="Bestimmte Artikel — der, die, das",
        example_target="der Hund, die Katze, das Haus",
        requires=[],
        level=1,
    ),
    # ── Level 2 — requires Level 1 ───────────────────────────────────────────
    GrammarItem(
        id="present_simple_negative",
        pattern="Subjekt + Verb + nicht + Objekt",
        description="Präsens — Verneinung mit nicht/kein",
        example_target="Ich esse keinen Fisch.",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="present_simple_question",
        pattern="Verb + Subjekt + Objekt?",
        description="Präsens — Ja/Nein-Frage (Inversion)",
        example_target="Magst du Katzen?",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="koennen_ability",
        pattern="Subjekt + können + Infinitiv",
        description="Fähigkeit mit können",
        example_target="Ich kann schnell schwimmen.",
        requires=["present_simple_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="haben_possession",
        pattern="Subjekt + haben + Akkusativ",
        description="Besitz mit haben",
        example_target="Ich habe einen Hund.",
        requires=["present_simple_affirmative", "articles_der_die_das"],
        level=2,
    ),
    GrammarItem(
        id="akkusativ_basics",
        pattern="den/die/das/einen/eine/ein + Nomen",
        description="Akkusativ — direktes Objekt",
        example_target="Ich sehe den Hund.",
        requires=["articles_der_die_das"],
        level=2,
    ),
    # ── Level 3 — requires Level 2 ───────────────────────────────────────────
    GrammarItem(
        id="dativ_basics",
        pattern="dem/der/dem/einem/einer/einem + Nomen",
        description="Dativ — indirektes Objekt",
        example_target="Ich gebe dem Hund einen Knochen.",
        requires=["akkusativ_basics"],
        level=3,
    ),
    GrammarItem(
        id="trennbare_verben",
        pattern="Subjekt + Präfix-Verb … Präfix",
        description="Trennbare Verben — Satzklammer",
        example_target="Ich stehe jeden Tag früh auf.",
        requires=["present_simple_affirmative"],
        level=3,
    ),
    GrammarItem(
        id="w_fragen",
        pattern="W-Wort + Verb + Subjekt?",
        description="W-Fragen — wer, was, wo, wann, warum, wie",
        example_target="Wo wohnst du?",
        requires=["present_simple_question"],
        level=3,
    ),
    GrammarItem(
        id="es_gibt",
        pattern="Es gibt + Akkusativ",
        description="Existenz — es gibt",
        example_target="Es gibt eine Katze auf dem Tisch.",
        requires=["akkusativ_basics"],
        level=3,
    ),
    GrammarItem(
        id="moechten_wollen",
        pattern="Subjekt + möchten/wollen + Infinitiv",
        description="Wünsche mit möchten und wollen",
        example_target="Ich möchte ein Eis.",
        requires=["present_simple_affirmative"],
        level=3,
    ),
    # ── Level 4 — requires Level 3 ───────────────────────────────────────────
    GrammarItem(
        id="perfekt_haben",
        pattern="Subjekt + haben + … + Partizip II",
        description="Perfekt mit haben — Vergangenheit",
        example_target="Ich habe gestern Brot gegessen.",
        requires=["present_simple_affirmative", "haben_possession"],
        level=4,
    ),
    GrammarItem(
        id="perfekt_sein",
        pattern="Subjekt + sein + … + Partizip II",
        description="Perfekt mit sein — Bewegung/Zustandsänderung",
        example_target="Ich bin gestern gelaufen.",
        requires=["perfekt_haben", "identity_sein"],
        level=4,
    ),
    GrammarItem(
        id="perfekt_negative",
        pattern="Subjekt + haben/sein + nicht + Partizip II",
        description="Perfekt — Verneinung",
        example_target="Ich habe keinen Fisch gegessen.",
        requires=["perfekt_haben", "present_simple_negative"],
        level=4,
    ),
    GrammarItem(
        id="perfekt_question",
        pattern="Haben/Sein + Subjekt + … + Partizip II?",
        description="Perfekt — Ja/Nein-Frage",
        example_target="Bist du heute gelaufen?",
        requires=["perfekt_haben", "present_simple_question"],
        level=4,
    ),
    GrammarItem(
        id="regelmaessige_partizipien",
        pattern="ge- + Stamm + -t",
        description="Regelmäßige Partizip-II-Bildung",
        example_target="spielen → gespielt, machen → gemacht",
        requires=["perfekt_haben"],
        level=4,
    ),
    GrammarItem(
        id="unregelmaessige_partizipien_1",
        pattern="ge- + Stamm + -en (Ablaut)",
        description="Unregelmäßige Partizipien — Satz 1",
        example_target="gehen/gegangen, essen/gegessen",
        requires=["perfekt_haben"],
        level=4,
    ),
    # ── Level 5 — requires Level 4 ───────────────────────────────────────────
    GrammarItem(
        id="praeteritum_sein_haben",
        pattern="Subjekt + war/hatte + …",
        description="Präteritum von sein und haben",
        example_target="Sie waren letzte Woche glücklich.",
        requires=["identity_sein", "haben_possession"],
        level=5,
    ),
    GrammarItem(
        id="muessen_sollen",
        pattern="Subjekt + müssen/sollen + Infinitiv",
        description="Pflicht und Ratschlag — müssen / sollen",
        example_target="Du musst jeden Tag lernen.",
        requires=["koennen_ability"],
        level=5,
    ),
    GrammarItem(
        id="unregelmaessige_partizipien_2",
        pattern="ge- + Stamm + -en (Ablaut)",
        description="Weitere unregelmäßige Partizipien — Satz 2",
        example_target="sehen/gesehen, nehmen/genommen",
        requires=["unregelmaessige_partizipien_1"],
        level=5,
    ),
    GrammarItem(
        id="werden_future",
        pattern="Subjekt + werden + … + Infinitiv",
        description="Futur I mit werden",
        example_target="Ich werde später essen.",
        requires=["present_simple_affirmative"],
        level=5,
    ),
    # ── Level 6 — requires Level 5 ───────────────────────────────────────────
    GrammarItem(
        id="komparativ_superlativ",
        pattern="Adjektiv-er / am Adjektiv-sten",
        description="Komparativ und Superlativ",
        example_target="Der Hund ist größer als die Katze.",
        requires=["identity_sein"],
        level=6,
    ),
    GrammarItem(
        id="weil_nebensatz",
        pattern="…, weil + Subjekt + … + Verb",
        description="Kausalsatz mit weil — Verb am Ende",
        example_target="Ich bleibe zu Hause, weil es regnet.",
        requires=["present_simple_affirmative"],
        level=6,
    ),
    GrammarItem(
        id="wenn_conditional",
        pattern="Wenn + Subjekt + … + Verb, Verb + Subjekt",
        description="Konditionalsatz mit wenn",
        example_target="Wenn es regnet, bleibe ich zu Hause.",
        requires=["werden_future", "present_simple_affirmative"],
        level=6,
    ),
]

HUN_TO_GER_GRAMMAR_PROGRESSION = GER_GRAMMAR_PROGRESSION  # backward compat
