"""Runtime Content Management (RCM) — shared item store across lessons.

Provides three tiers of persistence:
- SQLAlchemy/SQLite: item catalog, language branches, asset manifest, lesson membership
- Chroma vector index: semantic search over canonical items
- Filesystem: stable per-ID compiled assets (MP3 / PNG)

Usage::

    from jlesson.rcm import open_rcm

    with open_rcm(Path("rcm/")) as store:
        store.upsert_item(canonical_item)
        store.upsert_branch(item_id, "eng-fre", general_item)
        branch = store.get_branch(item_id, "eng-fre")
        covered = store.covered_texts("eng-fre", Phase.NOUNS)
"""

from .store import RCMStore, open_rcm

__all__ = ["RCMStore", "open_rcm"]
