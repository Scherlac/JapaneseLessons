from __future__ import annotations

import json
from pathlib import Path

_VOCAB_DIR = Path(__file__).parent.parent / "vocab"


def load_vocab(theme: str, vocab_dir: Path | None = None) -> dict:
    """Load vocab file; generate via LLM if missing."""
    base_dir = vocab_dir if vocab_dir is not None else _VOCAB_DIR
    path = base_dir / f"{theme}.json"
    if path.exists():
        with open(path, encoding="utf-8") as file_handle:
            return json.load(file_handle)
    print(f"  [vocab] {theme}.json not found - generating via LLM...")
    from jlesson.vocab_generator import generate_vocab

    return generate_vocab(
        theme=theme,
        num_nouns=12,
        num_verbs=10,
        output_dir=base_dir,
    )