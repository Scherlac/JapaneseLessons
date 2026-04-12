"""language_config — facade for language-pair configuration registry.

Defines the shared FieldMap/LanguageConfig types and registers all
known language pairs so callers can resolve a config by code.

Usage:
    from jlesson.language_config import get_language_config, LanguageConfig
    cfg = get_language_config("eng-jap")
    print(cfg.display_name)  # "English-Japanese"
"""

from ._base import FieldMap, LanguageConfig, PartialFieldMap, PartialLanguageConfig, _CONFIGS, get_language_config
from .config_eng import ENGLISH_LANGUAGE
from .config_fre import FRENCH_LANGUAGE
from .config_jap import JAPANESE_LANGUAGE
from .config_hun import HUNGARIAN_LANGUAGE
from .config_ger import GERMAN_LANGUAGE
from .eng_jap import ENG_JAP_CONFIG
from .hun_eng import HUN_ENG_CONFIG
from .hun_ger import HUN_GER_CONFIG
from .eng_fre import ENG_FRE_CONFIG

# Populate the registry — order determines the error message when an unknown
# code is supplied (sorted anyway, so order doesn't matter functionally).
_CONFIGS[ENG_JAP_CONFIG.code] = ENG_JAP_CONFIG
_CONFIGS[HUN_ENG_CONFIG.code] = HUN_ENG_CONFIG
_CONFIGS[HUN_GER_CONFIG.code] = HUN_GER_CONFIG
_CONFIGS[ENG_FRE_CONFIG.code] = ENG_FRE_CONFIG

__all__ = [
    "FieldMap",
    "LanguageConfig",
    "PartialFieldMap",
    "PartialLanguageConfig",
    "get_language_config",
    # Individual language configs
    "ENGLISH_LANGUAGE",
    "FRENCH_LANGUAGE",
    "JAPANESE_LANGUAGE",
    "HUNGARIAN_LANGUAGE",
    "GERMAN_LANGUAGE",
    # Language pair configs
    "ENG_JAP_CONFIG",
    "HUN_ENG_CONFIG",
    "HUN_GER_CONFIG",
    "ENG_FRE_CONFIG",
]
