"""RCMStore — SQLAlchemy-backed runtime content management store.

Tables
------
items          : Canonical English items (one row per canonical ID)
branches       : Language-aware GeneralItem resolutions (one per item × language)
assets         : Compiled asset paths (MP3 / PNG), keyed by item × language × asset_key
lesson_items   : Many-to-many membership of items in lessons

All serialisation to/from existing Pydantic types (CanonicalItem / GeneralItem / Sentence)
is handled via model_dump_json / model_validate_json so no new models are needed.

Grammar dimension columns (dim_1 … dim_8) on branches are populated at write time from
target.extra using a per-language, per-phase mapping registered via register_dim_map().
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from jlesson.models import CanonicalItem, GeneralItem, Phase, Sentence


# ---------------------------------------------------------------------------
# ORM schema (internal — not exported)
# ---------------------------------------------------------------------------

class _Base(DeclarativeBase):
    pass


class _ItemRow(_Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True)
    text = Column(String, nullable=False)
    text_normalized = Column(String, nullable=False, index=True)
    phase = Column(String, nullable=False, default="")
    canonical_json = Column(Text, nullable=False)


class _BranchRow(_Base):
    """One row per item × language resolution.

    Fixed grammar-dimension columns (dim_1 … dim_8) are populated from
    target.extra using the registered dim map — enabling SQL-level filtering
    by language-specific grammar attributes (e.g. auxiliary verb, article,
    verb conjugation type).

    grammar_id and grammar_parameters_json are only set when the stored item
    is a Sentence; they preserve the grammar-point connection that would
    otherwise be lost when deserialising as a plain GeneralItem.
    """
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("item_id", "language_code", name="uq_branch"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, nullable=False, index=True)
    language_code = Column(String, nullable=False, index=True)
    general_item_json = Column(Text, nullable=False)
    # Always populated from target.display_text
    target_text_normalized = Column(String, nullable=True, index=True)
    # Configurable grammar-dimension columns (populated from target.extra via dim map)
    dim_1 = Column(String, nullable=True, index=True)
    dim_2 = Column(String, nullable=True, index=True)
    dim_3 = Column(String, nullable=True, index=True)
    dim_4 = Column(String, nullable=True, index=True)
    dim_5 = Column(String, nullable=True, index=True)
    dim_6 = Column(String, nullable=True, index=True)
    dim_7 = Column(String, nullable=True, index=True)
    dim_8 = Column(String, nullable=True, index=True)
    # Sentence-only fields
    grammar_id = Column(String, nullable=True, index=True)
    grammar_parameters_json = Column(Text, nullable=True)


class _AssetRow(_Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("item_id", "language_code", "asset_key", name="uq_asset"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, nullable=False, index=True)
    language_code = Column(String, nullable=False)
    asset_key = Column(String, nullable=False)
    file_path = Column(String, nullable=False)


class _LessonItemRow(_Base):
    __tablename__ = "lesson_items"
    __table_args__ = (UniqueConstraint("lesson_id", "language_code", "item_id", name="uq_lesson_item"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, nullable=False, index=True)
    theme = Column(String, nullable=False)
    language_code = Column(String, nullable=False)
    item_id = Column(String, nullable=False, index=True)


# ---------------------------------------------------------------------------
# Dim column names (ordered, matches schema)
# ---------------------------------------------------------------------------

_DIM_COLS = ("dim_1", "dim_2", "dim_3", "dim_4", "dim_5", "dim_6", "dim_7", "dim_8")


# ---------------------------------------------------------------------------
# Public store
# ---------------------------------------------------------------------------

class RCMStore:
    """Thread-safe (one session per operation) runtime content management store."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        self._engine = create_engine(url, connect_args={"check_same_thread": False})
        # Enable WAL mode for concurrent reads during pipeline runs
        with self._engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            conn.commit()
        _Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(self._engine, expire_on_commit=False)
        # language_code -> { phase_value -> { dim_col -> extra_key } }
        self._dim_maps: dict[str, dict[str, dict[str, str]]] = {}

    # ------------------------------------------------------------------
    # Dim map registration
    # ------------------------------------------------------------------

    def register_dim_map(
        self,
        language_code: str,
        dim_map: dict[str, dict[str, str]],
    ) -> None:
        """Register a grammar-dimension mapping for *language_code*.

        *dim_map* is a dict as defined on PartialLanguageConfig.rcm_dim_map:
            { phase_value_or_empty_str -> { dim_col_name -> target.extra_key } }

        The empty string "" acts as a wildcard applied to all phases.
        """
        self._dim_maps[language_code] = dim_map

    def _resolve_dims(
        self,
        language_code: str,
        phase_value: str,
        extra: dict,
    ) -> dict[str, str | None]:
        """Return a dict of dim_col -> value for the given language and phase."""
        result: dict[str, str | None] = {col: None for col in _DIM_COLS}
        lang_map = self._dim_maps.get(language_code, {})
        # Wildcard mapping applied first, then phase-specific overrides on top
        merged: dict[str, str] = {}
        merged.update(lang_map.get("", {}))
        merged.update(lang_map.get(phase_value, {}))
        for dim_col, extra_key in merged.items():
            if dim_col in result:
                val = extra.get(extra_key)
                result[dim_col] = str(val) if val is not None else None
        return result

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._engine.dispose()

    def __enter__(self) -> "RCMStore":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def upsert_item(self, item: CanonicalItem) -> None:
        """Insert or update a canonical item record.

        Embeddings are preserved if populated — do not exclude them.
        """
        with self._Session() as session:
            row = session.get(_ItemRow, item.id)
            canonical_json = item.model_dump_json()
            text_norm = item.text.lower().strip()
            if row is None:
                session.add(_ItemRow(
                    id=item.id,
                    text=item.text,
                    text_normalized=text_norm,
                    phase=item.type.value if item.type else "",
                    canonical_json=canonical_json,
                ))
            else:
                row.text = item.text
                row.text_normalized = text_norm
                row.phase = item.type.value if item.type else ""
                row.canonical_json = canonical_json
            session.commit()

    # ------------------------------------------------------------------
    # Branches
    # ------------------------------------------------------------------

    def upsert_branch(
        self,
        item_id: str,
        language_code: str,
        general_item: GeneralItem,
    ) -> None:
        """Insert or update the language-aware resolution for an item.

        Populates grammar-dimension columns from target.extra using the registered
        dim map.  Preserves grammar_id / grammar_parameters when the item is a
        Sentence so the grammar-point connection survives round-trip.
        """
        phase_value = (general_item.phase or Phase.UNKNOWN).value
        extra = general_item.target.extra if general_item.target else {}
        dims = self._resolve_dims(language_code, phase_value, extra)

        target_text_norm = (
            general_item.target.display_text.lower().strip()
            if general_item.target and general_item.target.display_text
            else None
        )

        is_sentence = isinstance(general_item, Sentence)
        grammar_id = general_item.grammar_id if is_sentence else None  # type: ignore[attr-defined]
        grammar_params_json = (
            json.dumps(general_item.grammar_parameters)  # type: ignore[attr-defined]
            if is_sentence
            else None
        )

        item_json = general_item.model_dump_json()

        with self._Session() as session:
            row = (
                session.query(_BranchRow)
                .filter_by(item_id=item_id, language_code=language_code)
                .first()
            )
            if row is None:
                session.add(_BranchRow(
                    item_id=item_id,
                    language_code=language_code,
                    general_item_json=item_json,
                    target_text_normalized=target_text_norm,
                    grammar_id=grammar_id,
                    grammar_parameters_json=grammar_params_json,
                    **dims,
                ))
            else:
                row.general_item_json = item_json
                row.target_text_normalized = target_text_norm
                row.grammar_id = grammar_id
                row.grammar_parameters_json = grammar_params_json
                for col, val in dims.items():
                    setattr(row, col, val)
            session.commit()

    def get_branch(self, item_id: str, language_code: str) -> GeneralItem | None:
        """Return the cached item for an item×language pair.

        Returns a ``Sentence`` when the stored branch has a ``grammar_id``
        (i.e. it was written from a Sentence), otherwise a plain ``GeneralItem``.
        """
        with self._Session() as session:
            row = (
                session.query(_BranchRow)
                .filter_by(item_id=item_id, language_code=language_code)
                .first()
            )
            if row is None:
                return None
            if row.grammar_id:
                return Sentence.model_validate_json(row.general_item_json)
            return GeneralItem.model_validate_json(row.general_item_json)

    def query_branches(
        self,
        language_code: str,
        phase: Phase | None = None,
        grammar_id: str | None = None,
        dim_1: str | None = None,
        dim_2: str | None = None,
        dim_3: str | None = None,
        dim_4: str | None = None,
        dim_5: str | None = None,
        dim_6: str | None = None,
        dim_7: str | None = None,
        dim_8: str | None = None,
    ) -> list[GeneralItem | Sentence]:
        """Return all branches matching the given filters.

        Any ``None`` argument is ignored (not filtered on).  Use the dim
        arguments to filter by language-specific grammar attributes, e.g.::

            store.query_branches("eng-fre", Phase.VERBS, dim_1="être")
            store.query_branches("eng-jap", Phase.VERBS, dim_1="る-verb")
        """
        with self._Session() as session:
            q = session.query(_BranchRow).filter(
                _BranchRow.language_code == language_code
            )
            if phase is not None:
                q = q.join(_ItemRow, _ItemRow.id == _BranchRow.item_id).filter(
                    _ItemRow.phase == phase.value
                )
            if grammar_id is not None:
                q = q.filter(_BranchRow.grammar_id == grammar_id)
            for col, val in zip(_DIM_COLS, (dim_1, dim_2, dim_3, dim_4, dim_5, dim_6, dim_7, dim_8)):
                if val is not None:
                    q = q.filter(getattr(_BranchRow, col) == val)
            rows = q.all()

        result: list[GeneralItem | Sentence] = []
        for row in rows:
            if row.grammar_id:
                result.append(Sentence.model_validate_json(row.general_item_json))
            else:
                result.append(GeneralItem.model_validate_json(row.general_item_json))
        return result

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------

    def register_asset(
        self,
        item_id: str,
        language_code: str,
        asset_key: str,
        file_path: Path,
    ) -> None:
        """Record a compiled asset path for an item×language×asset_key triple."""
        with self._Session() as session:
            row = (
                session.query(_AssetRow)
                .filter_by(item_id=item_id, language_code=language_code, asset_key=asset_key)
                .first()
            )
            path_str = str(file_path)
            if row is None:
                session.add(_AssetRow(
                    item_id=item_id,
                    language_code=language_code,
                    asset_key=asset_key,
                    file_path=path_str,
                ))
            else:
                row.file_path = path_str
            session.commit()

    def get_asset(
        self,
        item_id: str,
        language_code: str,
        asset_key: str,
    ) -> Path | None:
        """Return the registered path for an asset, or None if not registered."""
        with self._Session() as session:
            row = (
                session.query(_AssetRow)
                .filter_by(item_id=item_id, language_code=language_code, asset_key=asset_key)
                .first()
            )
            if row is None:
                return None
            p = Path(row.file_path)
            return p if p.exists() else None

    # ------------------------------------------------------------------
    # Vocab coverage (canonical + target text dedup)
    # ------------------------------------------------------------------

    def covered_vocab(self, language_code: str, phase: Phase) -> dict[str, set[str]]:
        """Return a mapping of canonical text_normalized -> set[gloss] for all
        items that have been LLM-resolved for *language_code* and *phase*.

        The gloss set lets the caller distinguish genuinely different senses of
        the same word (e.g. "father" with gloss "formal register" vs "informal
        register") from meaningless duplicates.  An empty gloss set means the
        word was stored without disambiguation.
        """
        with self._Session() as session:
            rows = (
                session.query(_ItemRow.text_normalized, _ItemRow.canonical_json)
                .join(
                    _BranchRow,
                    (_ItemRow.id == _BranchRow.item_id)
                    & (_BranchRow.language_code == language_code),
                )
                .filter(_ItemRow.phase == phase.value)
                .all()
            )
        result: dict[str, set[str]] = {}
        for text_norm, canonical_json in rows:
            try:
                gloss = json.loads(canonical_json).get("gloss", "") or ""
            except (json.JSONDecodeError, AttributeError):
                gloss = ""
            result.setdefault(text_norm, set())
            if gloss:
                result[text_norm].add(gloss)
        return result

    def covered_target_texts(self, language_code: str, phase: Phase) -> set[str]:
        """Return target-language display_text (normalised) for all resolved items.

        Used to catch the case where two different canonical English words resolve
        to the same target-language word (e.g. 'to say' and 'to tell' both → 'dire').
        """
        with self._Session() as session:
            rows = (
                session.query(_BranchRow.target_text_normalized)
                .join(_ItemRow, _ItemRow.id == _BranchRow.item_id)
                .filter(
                    _BranchRow.language_code == language_code,
                    _ItemRow.phase == phase.value,
                    _BranchRow.target_text_normalized.isnot(None),
                )
                .all()
            )
        return {row[0] for row in rows if row[0]}

    # ------------------------------------------------------------------
    # Lesson membership
    # ------------------------------------------------------------------

    def record_lesson_items(
        self,
        lesson_id: int,
        theme: str,
        language_code: str,
        items: list[GeneralItem],
    ) -> None:
        """Associate a list of GeneralItems with a lesson record."""
        with self._Session() as session:
            for item in items:
                exists = (
                    session.query(_LessonItemRow)
                    .filter_by(
                        lesson_id=lesson_id,
                        language_code=language_code,
                        item_id=item.canonical.id,
                    )
                    .first()
                )
                if exists is None:
                    session.add(_LessonItemRow(
                        lesson_id=lesson_id,
                        theme=theme,
                        language_code=language_code,
                        item_id=item.canonical.id,
                    ))
            session.commit()

    # ------------------------------------------------------------------
    # Stats / reporting
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return a summary dict for CLI reporting."""
        with self._Session() as session:
            n_items = session.query(_ItemRow).count()
            n_branches = session.query(_BranchRow).count()
            n_assets = session.query(_AssetRow).count()
            n_lesson_items = session.query(_LessonItemRow).count()

            # Find text-normalised duplicates (same word, different IDs)
            dup_rows = session.execute(text(
                "SELECT text_normalized, COUNT(*) as cnt "
                "FROM items GROUP BY text_normalized HAVING cnt > 1 ORDER BY cnt DESC"
            )).fetchall()
            duplicates = [{"text": row[0], "count": row[1]} for row in dup_rows]

        return {
            "items": n_items,
            "branches": n_branches,
            "assets": n_assets,
            "lesson_items": n_lesson_items,
            "duplicate_texts": duplicates,
        }




# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

@contextmanager
def open_rcm(rcm_path: Path) -> Generator[RCMStore, None, None]:
    """Context manager that opens an RCMStore at *rcm_path*/rcm.db and closes it on exit."""
    store = RCMStore(rcm_path / "rcm.db")
    try:
        yield store
    finally:
        store.close()
