"""vocab_generator — facade for vocabulary generation and schema validation.

Generation orchestration and the unified schema validator live in _base.
The validator is parameterised by LanguageConfig so no language-specific
sibling modules are needed.

Usage:
    from jlesson.vocab_generator import generate_vocab, extend_vocab
    from jlesson.vocab_generator import validate_vocab_schema
"""

from ._base import VOCAB_DIR, extend_vocab, generate_vocab, normalize_vocab_item, validate_vocab_schema

__all__ = [
    "generate_vocab",
    "extend_vocab",
    "normalize_vocab_item",
    "validate_vocab_schema",
    "VOCAB_DIR",
]
