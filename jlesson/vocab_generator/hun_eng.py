"""Schema validation for Hungarian-English vocabulary files."""

_REQUIRED_HUN_NOUN_FIELDS = {"english", "hungarian", "pronunciation"}
_REQUIRED_HUN_VERB_FIELDS = {"english", "hungarian", "pronunciation", "past_tense"}


def validate_hungarian_vocab_schema(vocab: dict) -> list[str]:
    """Validate a Hungarian vocab dict against the required schema.

    Returns a list of human-readable error strings.
    An empty list means the vocab is valid.
    """
    errors: list[str] = []

    if "theme" not in vocab:
        errors.append("Missing top-level 'theme' field")

    nouns = vocab.get("nouns")
    if not isinstance(nouns, list) or len(nouns) == 0:
        errors.append("'nouns' must be a non-empty list")
    else:
        for i, noun in enumerate(nouns):
            missing = _REQUIRED_HUN_NOUN_FIELDS - set(noun.keys())
            if missing:
                errors.append(
                    f"nouns[{i}] ({noun.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )

    verbs = vocab.get("verbs")
    if not isinstance(verbs, list) or len(verbs) == 0:
        errors.append("'verbs' must be a non-empty list")
    else:
        for i, verb in enumerate(verbs):
            missing = _REQUIRED_HUN_VERB_FIELDS - set(verb.keys())
            if missing:
                errors.append(
                    f"verbs[{i}] ({verb.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )

    return errors
