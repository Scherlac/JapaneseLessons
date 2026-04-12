"""RCM-backed vector retrieval service.

Combines RCMStore (SQLAlchemy/SQLite) with a persistent Chroma vector index.

Search flow
-----------
1. Embed the query text via the configured embedding model.
2. Query the Chroma collection for the top-k matching canonical item IDs.
3. For each hit, look up whether the requested language branch exists in SQL.
4. Return (CanonicalItem, GeneralItem | Sentence) pairs, ordered by vector
   similarity, skipping items that have no branch for the requested language.

Ingestion
---------
Calling ``ingest_item()`` stores the canonical item in SQL via
``RCMStore.upsert_item()`` and upserts its embedding into Chroma.

- If ``item.embeddings`` is already populated, those are used as-is.
- If the item already exists in SQL with embeddings, those are reused
  (avoids redundant API calls on repeated ingestion).
- Only when neither is available is a new embedding generated.

This means any canonical item — noun, verb, sentence, grammar point, narrative
fragment — can be ingested and will be discoverable by vector search.  Language
branch narrowing happens in SQL after the vector stage.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..models import CanonicalItem, GeneralItem, Phase, Sentence
from .store import RCMStore


class RCMVectorRetrievalService:
    """Retrieval service backed directly by RCMStore and a persistent Chroma index.

    Unlike the spike-era ``RetrievalService`` / ``ChromaVectorRetrievalService``,
    this class:

    - Works with ``CanonicalItem`` / ``GeneralItem`` / ``Sentence`` directly.
    - Uses the shared SQLite store (``RCMStore``) as the canonical source of
      truth — no separate JSON sidecar file.
    - Maintains an incremental Chroma collection (upsert, never delete/recreate).
    - Resolves language branches via SQL after the Chroma vector stage, so the
      search always operates on canonical English content and language narrowing
      is a cheap SQL lookup.

    Usage::

        from jlesson.rcm import open_rcm, RCMVectorRetrievalService

        with open_rcm(Path("rcm/")) as store:
            svc = RCMVectorRetrievalService(store, chroma_path=Path("rcm/chroma"))
            svc.ingest_item(canonical_item)
            results = svc.search("farm animals", "hun-ger", phase=Phase.NOUNS)
            for canonical, branch in results:
                print(canonical.text, "→", branch.target.display_text)
    """

    COLLECTION_NAME = "rcm_canonical"

    def __init__(
        self,
        store: RCMStore,
        chroma_path: Path | str,
        *,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._store = store
        self._chroma_path = Path(chroma_path)
        self._embedding_model = embedding_model
        self._collection: Any = None  # lazy-initialised on first use

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_item(self, item: CanonicalItem) -> None:
        """Store canonical item in SQL + upsert embedding into Chroma.

        For bulk ingestion prefer ``ingest_items_batch()`` which makes a single
        API call for all items that need new embeddings.

        Embedding resolution order:
        1. ``item.embeddings`` already populated — use as-is.
        2. Item already exists in SQL with embeddings — reuse them (no API call).
        3. Neither — generate a new embedding via the embedding model.
        """
        if not item.embeddings:
            existing = self._store.get_item(item.id)
            if existing and existing.embeddings:
                item.embeddings = existing.embeddings
            else:
                item.embeddings = self._embed_texts([item.text])[0]

        self._store.upsert_item(item)

        collection = self._get_collection()
        collection.upsert(
            ids=[item.id],
            embeddings=[item.embeddings],
            documents=[item.text],
            metadatas=[{
                "phase": item.type.value if item.type else "",
                "gloss": item.gloss or "",
            }],
        )

    def ingest_items_batch(
        self,
        items: list[CanonicalItem],
        *,
        batch_size: int = 500,
        progress_callback: "Any | None" = None,
    ) -> tuple[int, int]:
        """Bulk-ingest a list of canonical items into SQL and Chroma.

        Embeddings are resolved in three passes:
        1. Items with embeddings already on the object — used as-is.
        2. Items whose SQL record already has embeddings — reused (no API call).
        3. Remaining items — embedded in batches with a single API call per batch.

        Then all items are upserted into SQL and Chroma in batches.

        Parameters
        ----------
        items:
            Canonical items to ingest. Items already present in Chroma are
            upserted (idempotent), so it is safe to call this on a full list.
        batch_size:
            Maximum items per OpenAI embedding API call and per Chroma upsert.
        progress_callback:
            Optional callable(n_done: int, n_total: int) called after each
            batch completes.

        Returns
        -------
        (n_cached, n_generated)
            Number of embeddings reused from SQL vs generated via API.
        """
        if not items:
            return 0, 0

        # Pass 1: collect items that need SQL lookup or API call
        need_lookup: list[CanonicalItem] = []
        have_embedding: list[CanonicalItem] = []
        for item in items:
            if item.embeddings:
                have_embedding.append(item)
            else:
                need_lookup.append(item)

        # Pass 2: bulk-fetch SQL records for items without embeddings
        need_api: list[CanonicalItem] = []
        n_cached = len(have_embedding)
        for item in need_lookup:
            existing = self._store.get_item(item.id)
            if existing and existing.embeddings:
                item.embeddings = existing.embeddings
                n_cached += 1
            else:
                need_api.append(item)

        # Pass 3: batch API calls for items with no cached embedding
        n_generated = 0
        for batch_start in range(0, len(need_api), batch_size):
            batch = need_api[batch_start: batch_start + batch_size]
            texts = [it.text for it in batch]
            embeddings = self._embed_texts(texts)
            for item, embedding in zip(batch, embeddings):
                item.embeddings = embedding
            n_generated += len(batch)

        # Pass 4: bulk SQL upsert + Chroma upsert in batches
        collection = self._get_collection()
        n_done = 0
        for batch_start in range(0, len(items), batch_size):
            batch = items[batch_start: batch_start + batch_size]
            for item in batch:
                self._store.upsert_item(item)
            collection.upsert(
                ids=[it.id for it in batch],
                embeddings=[it.embeddings for it in batch],
                documents=[it.text for it in batch],
                metadatas=[{
                    "phase": it.type.value if it.type else "",
                    "gloss": it.gloss or "",
                } for it in batch],
            )
            n_done += len(batch)
            if progress_callback is not None:
                progress_callback(n_done, len(items))

        return n_cached, n_generated

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        requested_language: str,
        *,
        phase: Phase | None = None,
        limit: int = 10,
    ) -> list[tuple[CanonicalItem, GeneralItem | Sentence]]:
        """Vector-search canonical items, then narrow to those with a branch for *requested_language*.

        Returns ``(CanonicalItem, GeneralItem | Sentence)`` pairs ordered by
        decreasing vector similarity.  Items without a branch for
        *requested_language* are silently skipped; more candidates than *limit*
        are fetched from Chroma to compensate.

        Parameters
        ----------
        query:
            Free-text query in English (canonical language).
        requested_language:
            Language code, e.g. ``"hun-ger"`` or ``"eng-jap"``.
        phase:
            Optional phase filter applied at the Chroma metadata level before
            SQL branch lookup.
        limit:
            Maximum number of (canonical, branch) pairs to return.
        """
        collection = self._get_collection()
        total = collection.count()
        if total == 0:
            return []

        query_embedding = self._embed_texts([query])[0]
        # Fetch more candidates than needed to absorb branch misses
        fetch_count = min(total, max(limit * 4, 20))

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": fetch_count,
            "include": ["distances"],
        }
        if phase is not None:
            kwargs["where"] = {"phase": phase.value}

        result = collection.query(**kwargs)
        ids: list[str] = result.get("ids", [[]])[0]

        pairs: list[tuple[CanonicalItem, GeneralItem | Sentence]] = []
        for item_id in ids:
            if len(pairs) >= limit:
                break
            branch = self._store.get_branch(item_id, requested_language)
            if branch is None:
                continue
            canonical = self._store.get_item(item_id)
            if canonical is None:
                continue
            pairs.append((canonical, branch))

        return pairs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_collection(self) -> Any:
        """Return (creating if necessary) the persistent Chroma collection."""
        if self._collection is None:
            try:
                import chromadb
            except ImportError as exc:
                raise RuntimeError(
                    "chromadb is not installed. Run: pip install chromadb"
                ) from exc
            self._chroma_path.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self._chroma_path))
            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed") from exc

        base_url = (
            os.getenv("OPENAI_BASE_URL", "").strip()
            or os.getenv("LLM_BASE_URL", "").strip()
        )
        api_key = (
            os.getenv("OPENAI_API_KEY", "").strip()
            or os.getenv("LLM_API_KEY", "").strip()
        )
        if not api_key and base_url and "api.openai.com" not in base_url.lower():
            api_key = "lm-studio"
        if not api_key:
            raise RuntimeError(
                "No API key found. Set OPENAI_API_KEY or LLM_API_KEY."
            )

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)
        response = client.embeddings.create(model=self._embedding_model, input=texts)
        return [list(item.embedding) for item in response.data]
