"""Spike 2: vector retrieval with metadata filtering.

Usage:
    conda activate py312
    python spike/vector_indexing/spike_02_vector_metadata_filtering/spike_02_metadata.py

This script is intentionally lightweight and safe to extend.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> None:
    # TODO: wire filtered search over metadata fields:
    # theme, level, concept_type, grammar_progression.ja
    out = {
        "spike": "spike_02_vector_metadata_filtering",
        "status": "scaffold_ready",
        "timestamp_utc": utc_now(),
        "notes": [
            "Reuse embeddings/index from spike 1",
            "Apply metadata filters in retrieval",
            "Compare no-filter vs filtered precision@k",
            "Measure off-topic reduction",
        ],
    }

    out_path = Path(__file__).parent / "results_spike_02.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote scaffold artifact: {out_path}")


if __name__ == "__main__":
    main()
