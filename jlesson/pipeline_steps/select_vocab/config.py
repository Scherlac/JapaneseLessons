from __future__ import annotations

from dataclasses import dataclass

from jlesson.language_config import LanguageConfig


@dataclass(frozen=True)
class SelectVocabLanguageConfig:
    """Language-specific configuration used only by the select_vocab step.

    Isolates the one piece of language-pair knowledge the step needs:
    how to normalise verb strings when comparing them against covered vocab.
    English uses the infinitive prefix "to " (e.g. "to eat" → "eat").
    Languages without a mandatory infinitive prefix leave this empty.
    """

    verb_infinitive_prefix: str = ""


_LANGUAGE_CONFIGS: dict[str, SelectVocabLanguageConfig] = {
    "eng-jap": SelectVocabLanguageConfig(verb_infinitive_prefix="to "),
    "hun-eng": SelectVocabLanguageConfig(verb_infinitive_prefix="to "),
}

_FALLBACK = SelectVocabLanguageConfig()


def build_select_vocab_language_config(
    language_config: LanguageConfig,
) -> SelectVocabLanguageConfig:
    """Return the step-local config for *language_config*."""
    return _LANGUAGE_CONFIGS.get(language_config.code, _FALLBACK)
