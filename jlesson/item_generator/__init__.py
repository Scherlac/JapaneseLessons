"""item_generator — facade for language-specific item converter implementations.

Provides a common interface (ItemGenerator ABC) and concrete implementations
for each supported language pair.  Callers can import any symbol from this
package without knowing the internal file layout.

Usage:
    from jlesson.item_generator import ItemGenerator
    from jlesson.item_generator import EngJapItemGenerator, HunEngItemGenerator
"""

from ._base import ItemGenerator
from .eng_jap import EngJapItemGenerator
from .hun_eng import HunEngItemGenerator
from .hun_ger import HunGerItemGenerator
from .eng_fre import EngFrItemGenerator

__all__ = [
    "ItemGenerator",
    "EngJapItemGenerator",
    "HunEngItemGenerator",
    "HunGerItemGenerator",
    "EngFrItemGenerator",
]
