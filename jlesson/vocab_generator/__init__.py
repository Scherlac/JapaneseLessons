"""vocab_generator — facade for vocabulary generation and schema validation.

Language-specific schema constants and validators live in the eng_jap / hun_eng
sibling modules.  Generation orchestration lives in _base.  Callers can import
any symbol from this package without knowing the internal file layout.

Usage:
    from jlesson.vocab_generator import generate_vocab, extend_vocab
    from jlesson.vocab_generator import validate_vocab_schema
    from jlesson.vocab_generator import validate_hungarian_vocab_schema
"""

from ._base import VOCAB_DIR, extend_vocab, generate_vocab
from .eng_jap import validate_vocab_schema
from .hun_eng import validate_hungarian_vocab_schema

__all__ = [
    "generate_vocab",
    "extend_vocab",
    "validate_vocab_schema",
    "validate_hungarian_vocab_schema",
    "VOCAB_DIR",
]
