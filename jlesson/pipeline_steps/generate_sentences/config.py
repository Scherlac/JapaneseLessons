"""Step-local language configuration for the narrative_grammar step."""
from __future__ import annotations

from dataclasses import dataclass

from jlesson.language_config import LanguageConfig


@dataclass(frozen=True)
class NarrativeGrammarLanguageConfig:
    """Language-specific settings used only by the narrative_grammar step.

    Captures the minimal language-pair knowledge the step needs independently
    of the broader ``LanguageConfig``:

    persons
        Tuples of (native_label, target_label, phonetic) for each grammatical
        person to generate sentences for.  Derived from ``LanguageConfig.persons``
        (the single source of truth for the lesson language pair).

    teacher_description
        How the LLM is framed in the opening line of the prompt, e.g.
        ``"a Japanese language teacher"``.

    output_source_field / output_target_field / output_phonetic_field
        JSON key names the LLM must use in its ``sentences`` array.  These must
        match what ``ItemGenerator.convert_sentence`` reads so no changes to the
        language-specific converters are needed.  ``output_phonetic_field`` may
        be empty — the field is then omitted from both the task description and
        the output schema.
    """

    persons: tuple[tuple[str, str, str], ...]
    teacher_description: str = "a language teacher"
    output_source_field: str = "source_text"
    output_target_field: str = "target_text"
    output_phonetic_field: str = ""


# ---------------------------------------------------------------------------
# Per-language-pair defaults
# ---------------------------------------------------------------------------

_ENG_JAP_CONFIG = NarrativeGrammarLanguageConfig(
    persons=(),  # replaced at build time from LanguageConfig.persons
    teacher_description="a Japanese language teacher",
    output_source_field="english",
    output_target_field="japanese",
    output_phonetic_field="romaji",
)

_HUN_ENG_CONFIG = NarrativeGrammarLanguageConfig(
    persons=(),  # replaced at build time from LanguageConfig.persons
    teacher_description="an English teacher for Hungarian beginners",
    output_source_field="hungarian",
    output_target_field="english",
    output_phonetic_field="pronunciation",
)

_HUN_GER_CONFIG = NarrativeGrammarLanguageConfig(
    persons=(),  # replaced at build time from LanguageConfig.persons
    teacher_description="a German teacher for Hungarian beginners",
    output_source_field="hungarian",
    output_target_field="german",
    output_phonetic_field="",
)

_LANGUAGE_DEFAULTS: dict[str, NarrativeGrammarLanguageConfig] = {
    "eng-jap": _ENG_JAP_CONFIG,
    "hun-eng": _HUN_ENG_CONFIG,
    "hun-ger": _HUN_GER_CONFIG,
}

_FALLBACK = NarrativeGrammarLanguageConfig(persons=())


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_narrative_grammar_language_config(
    language_config: LanguageConfig,
) -> NarrativeGrammarLanguageConfig:
    """Return the step-local config derived from *language_config*.

    Persons are read from ``LanguageConfig.persons`` (set per language pair in
    the language-config module) so the step does not duplicate that list.
    Framing and output-field names come from the per-pair defaults above.
    """
    base = _LANGUAGE_DEFAULTS.get(language_config.code, _FALLBACK)
    persons = language_config.persons if language_config.persons else base.persons
    return NarrativeGrammarLanguageConfig(
        persons=persons,
        teacher_description=base.teacher_description,
        output_source_field=base.output_source_field,
        output_target_field=base.output_target_field,
        output_phonetic_field=base.output_phonetic_field,
    )
