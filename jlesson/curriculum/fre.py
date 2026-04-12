"""
English → French grammar progression table.

Provides the ordered, prerequisite-aware grammar sequence for the
eng-fre language pair (English-speaking learners beginning French).
26 grammar points across 6 prerequisite-aware levels.
"""

from __future__ import annotations

from ..models import GrammarItem


# ── Grammar Progression — English → French (levels 1-6) ──────────────────────

FRE_GRAMMAR_PROGRESSION: list[GrammarItem] = [
    # ── Level 1 — absolute beginner, no prerequisites ────────────────────────
    GrammarItem(
        id="present_etre_identity",
        pattern="Sujet + être + nom/adjectif",
        description="Identity and description with être (to be)",
        example_target="Elle est professeure.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="present_avoir_possession",
        pattern="Sujet + avoir + nom",
        description="Possession and age with avoir (to have)",
        example_target="J'ai un chien.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="present_er_verbs_affirmative",
        pattern="Sujet + verbe(-er) conjugué",
        description="Regular -er verbs in the present tense — affirmative",
        example_target="Je mange du pain.",
        requires=[],
        level=1,
    ),
    GrammarItem(
        id="noun_gender_articles",
        pattern="article défini/indéfini + nom",
        description="Noun gender — definite and indefinite articles (le/la/un/une)",
        example_target="Le chat. Un livre.",
        requires=[],
        level=1,
    ),
    # ── Level 2 — requires Level 1 ───────────────────────────────────────────
    GrammarItem(
        id="negation_ne_pas",
        pattern="Sujet + ne + verbe + pas",
        description="Sentence negation with ne … pas",
        example_target="Je ne mange pas de poisson.",
        requires=["present_er_verbs_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="yes_no_question_est_ce_que",
        pattern="Est-ce que + sujet + verbe?",
        description="Yes/no questions with est-ce que",
        example_target="Est-ce que tu aimes les chats?",
        requires=["present_er_verbs_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="present_ir_verbs",
        pattern="Sujet + verbe(-ir) conjugué",
        description="Regular -ir verbs in the present tense",
        example_target="Elle choisit un livre.",
        requires=["present_er_verbs_affirmative"],
        level=2,
    ),
    GrammarItem(
        id="adjective_agreement",
        pattern="nom + adjectif (accordé)",
        description="Adjective agreement in gender and number",
        example_target="Une grande maison. Une grande voiture.",
        requires=["noun_gender_articles"],
        level=2,
    ),
    GrammarItem(
        id="plural_nouns_articles",
        pattern="les/des + nom (pluriel)",
        description="Plural nouns with definite and indefinite articles",
        example_target="Les chiens. Des livres.",
        requires=["noun_gender_articles"],
        level=2,
    ),
    # ── Level 3 — requires Level 2 ───────────────────────────────────────────
    GrammarItem(
        id="present_aller_immediate_future",
        pattern="Sujet + aller + infinitif",
        description="Immediate future with aller + infinitive",
        example_target="Je vais manger.",
        requires=["present_er_verbs_affirmative", "present_etre_identity"],
        level=3,
    ),
    GrammarItem(
        id="present_re_verbs",
        pattern="Sujet + verbe(-re) conjugué",
        description="Regular -re verbs in the present tense",
        example_target="Elle attend le bus.",
        requires=["present_er_verbs_affirmative"],
        level=3,
    ),
    GrammarItem(
        id="interrogative_pronouns_que_qui",
        pattern="Qui/Que + est-ce que + sujet + verbe?",
        description="Interrogative pronouns — qui (who) and que (what)",
        example_target="Qu'est-ce que tu manges? Qui est-elle?",
        requires=["yes_no_question_est_ce_que"],
        level=3,
    ),
    GrammarItem(
        id="possessive_adjectives",
        pattern="mon/ma/mes + nom",
        description="Possessive adjectives (mon, ma, mes, ton, ta, tes, son, sa, ses)",
        example_target="Mon livre. Son chien.",
        requires=["noun_gender_articles", "adjective_agreement"],
        level=3,
    ),
    GrammarItem(
        id="prepositions_place",
        pattern="préposition + lieu",
        description="Common prepositions of place (à, en, dans, sur, sous, devant, derrière)",
        example_target="Le chat est sur la table.",
        requires=["present_etre_identity"],
        level=3,
    ),
    # ── Level 4 — requires Level 3 ───────────────────────────────────────────
    GrammarItem(
        id="passe_compose_avoir",
        pattern="Sujet + avoir (conjugué) + participe passé",
        description="Passé composé with avoir (most verbs)",
        example_target="J'ai mangé une pomme.",
        requires=["present_avoir_possession", "present_er_verbs_affirmative"],
        level=4,
    ),
    GrammarItem(
        id="passe_compose_etre",
        pattern="Sujet + être (conjugué) + participe passé",
        description="Passé composé with être (motion and reflexive verbs)",
        example_target="Elle est allée au magasin.",
        requires=["present_etre_identity", "present_aller_immediate_future"],
        level=4,
    ),
    GrammarItem(
        id="object_pronouns_direct",
        pattern="Sujet + pronom COD + verbe",
        description="Direct object pronouns (le, la, les, me, te)",
        example_target="Je le mange. Elle me voit.",
        requires=["present_er_verbs_affirmative", "negation_ne_pas"],
        level=4,
    ),
    GrammarItem(
        id="imperatives",
        pattern="Verbe (impératif) + complément",
        description="Imperative mood — affirmative and negative commands",
        example_target="Mange ton pain! Ne cours pas!",
        requires=["negation_ne_pas", "present_er_verbs_affirmative"],
        level=4,
    ),
    GrammarItem(
        id="comparatives",
        pattern="plus/moins/aussi + adjectif + que",
        description="Comparatives — more, less, as … as",
        example_target="Elle est plus grande que lui.",
        requires=["adjective_agreement"],
        level=4,
    ),
    # ── Level 5 — requires Level 4 ───────────────────────────────────────────
    GrammarItem(
        id="imparfait",
        pattern="Sujet + verbe (imparfait)",
        description="Imperfect tense — ongoing or habitual past actions",
        example_target="Je mangeais ici tous les jours.",
        requires=["passe_compose_avoir"],
        level=5,
    ),
    GrammarItem(
        id="futur_simple",
        pattern="Sujet + verbe (futur simple)",
        description="Simple future tense",
        example_target="Je mangerai demain.",
        requires=["present_aller_immediate_future"],
        level=5,
    ),
    GrammarItem(
        id="reflexive_verbs_present",
        pattern="Sujet + se + verbe (réfléchi)",
        description="Reflexive verbs in the present tense",
        example_target="Je me lave. Elle se réveille.",
        requires=["present_er_verbs_affirmative"],
        level=5,
    ),
    GrammarItem(
        id="conditional_present",
        pattern="Sujet + verbe (conditionnel présent)",
        description="Present conditional — would + verb",
        example_target="Je voudrais un café.",
        requires=["futur_simple"],
        level=5,
    ),
    # ── Level 6 — requires Level 5 ───────────────────────────────────────────
    GrammarItem(
        id="subjonctif_present",
        pattern="il faut que / vouloir que + subjonctif",
        description="Present subjunctive after common trigger verbs",
        example_target="Il faut que tu viennes.",
        requires=["conditional_present", "present_er_verbs_affirmative"],
        level=6,
    ),
    GrammarItem(
        id="relative_pronouns_qui_que",
        pattern="nom + qui/que + proposition",
        description="Relative pronouns qui (subject) and que (object)",
        example_target="Le livre que je lis. L'homme qui chante.",
        requires=["present_er_verbs_affirmative", "object_pronouns_direct"],
        level=6,
    ),
    GrammarItem(
        id="indirect_speech",
        pattern="Il dit que + sujet + verbe (discours indirect)",
        description="Indirect speech — reporting what someone said",
        example_target="Il dit qu'il a faim.",
        requires=["present_etre_identity", "present_avoir_possession"],
        level=6,
    ),
]

ENG_TO_FRE_GRAMMAR_PROGRESSION = FRE_GRAMMAR_PROGRESSION  # backward compat
