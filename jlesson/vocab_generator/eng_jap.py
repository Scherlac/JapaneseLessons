"""Schema validation for English-Japanese vocabulary files."""

_REQUIRED_NOUN_FIELDS = {"english", "japanese", "kanji", "romaji"}
_REQUIRED_VERB_FIELDS = {"english", "japanese", "kanji", "romaji", "type", "masu_form"}
_VALID_VERB_TYPES = {"る-verb", "う-verb", "irregular", "な-adj"}
_REQUIRED_ADJ_FIELDS = {"english", "japanese", "kanji", "romaji", "type"}
_VALID_ADJ_TYPES = {"い-adj", "な-adj"}


def validate_vocab_schema(vocab: dict) -> list[str]:
    """Validate a vocab dict against the eng-jap required schema.

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
            missing = _REQUIRED_NOUN_FIELDS - set(noun.keys())
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
            missing = _REQUIRED_VERB_FIELDS - set(verb.keys())
            if missing:
                errors.append(
                    f"verbs[{i}] ({verb.get('english', '?')!r}): "
                    f"missing fields {sorted(missing)}"
                )
                continue  # can't check type if fields are missing
            if verb["type"] not in _VALID_VERB_TYPES:
                errors.append(
                    f"verbs[{i}] ({verb['english']!r}): "
                    f"invalid type {verb['type']!r} — "
                    f"must be one of {sorted(_VALID_VERB_TYPES)}"
                )

    adjectives = vocab.get("adjectives")
    if adjectives is not None:
        if not isinstance(adjectives, list):
            errors.append("'adjectives' must be a list when provided")
        else:
            for i, adj in enumerate(adjectives):
                missing = _REQUIRED_ADJ_FIELDS - set(adj.keys())
                if missing:
                    errors.append(
                        f"adjectives[{i}] ({adj.get('english', '?')!r}): "
                        f"missing fields {sorted(missing)}"
                    )
                    continue
                if adj["type"] not in _VALID_ADJ_TYPES:
                    errors.append(
                        f"adjectives[{i}] ({adj['english']!r}): "
                        f"invalid type {adj['type']!r} — "
                        f"must be one of {sorted(_VALID_ADJ_TYPES)}"
                    )

    return errors
