from __future__ import annotations

from pathlib import Path

from jlesson.language_config import get_language_config


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