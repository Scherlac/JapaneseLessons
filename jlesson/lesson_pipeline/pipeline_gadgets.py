from __future__ import annotations

import json
from pathlib import Path

from jlesson.language_config import get_language_config
from jlesson.llm_client import ask_llm_json_free
from jlesson.models import GrammarItem

_VOCAB_DIR = Path(__file__).parent.parent / "vocab"


class PipelineGadgets:
    """Temporary shared helpers for lesson pipeline steps."""

    @staticmethod
    def load_vocab(theme: str, vocab_dir: Path | None = None) -> dict:
        """Load vocab file; generate via LLM if missing."""
        base_dir = vocab_dir if vocab_dir is not None else _VOCAB_DIR
        path = base_dir / f"{theme}.json"
        if path.exists():
            with open(path, encoding="utf-8") as file_handle:
                return json.load(file_handle)
        print(f"  [vocab] {theme}.json not found — generating via LLM...")
        from jlesson.vocab_generator import generate_vocab

        return generate_vocab(
            theme=theme,
            num_nouns=12,
            num_verbs=10,
            output_dir=base_dir,
        )

    @staticmethod
    def ask_llm(ctx, prompt: str) -> dict:
        """Route LLM call through cache when use_cache is enabled."""
        if ctx.config.use_cache:
            from jlesson.llm_cache import ask_llm_cached

            return ask_llm_cached(prompt)
        return ask_llm_json_free(prompt)

    @staticmethod
    def coerce_grammar_items(
        grammar_items: list[GrammarItem | dict],
    ) -> list[GrammarItem]:
        coerced: list[GrammarItem] = []
        for item in grammar_items:
            if isinstance(item, GrammarItem):
                coerced.append(item)
            else:
                coerced.append(GrammarItem(**item))
        return coerced

    @staticmethod
    def grammar_id(grammar: GrammarItem | dict) -> str:
        if isinstance(grammar, GrammarItem):
            return grammar.id
        return str(grammar.get("id", ""))

    @staticmethod
    def resolve_output_dir(config) -> Path:
        base = (
            Path(config.output_dir)
            if config.output_dir is not None
            else Path(__file__).parent.parent / "output"
        )
        if config.language != "eng-jap":
            lang_cfg = get_language_config(config.language)
            return base / lang_cfg.native_language.lower()
        return base