"""RCMStore — SQLAlchemy-backed runtime content management store.

Tables
------
items          : Canonical English items (one row per canonical ID)
branches       : Language-aware GeneralItem resolutions (one per item × language)
assets         : Compiled asset paths (MP3 / PNG), keyed by item × language × asset_key
lesson_items   : Many-to-many membership of items in lessons

All serialisation to/from existing Pydantic types (CanonicalItem / GeneralItem)
is handled via model_dump_json / model_validate_json so no new models are needed.
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
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from jlesson.models import CanonicalItem, GeneralItem, Phase


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
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("item_id", "language_code", name="uq_branch"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, nullable=False, index=True)
    language_code = Column(String, nullable=False, index=True)
    general_item_json = Column(Text, nullable=False)


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
        """Insert or update a canonical item record."""
        with self._Session() as session:
            row = session.get(_ItemRow, item.id)
            canonical_json = item.model_dump_json(exclude={"embeddings"})
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
        """Insert or update the language-aware GeneralItem resolution for an item."""
        with self._Session() as session:
            row = (
                session.query(_BranchRow)
                .filter_by(item_id=item_id, language_code=language_code)
                .first()
            )
            item_json = general_item.model_dump_json(exclude={"canonical": {"embeddings"}})
            if row is None:
                session.add(_BranchRow(
                    item_id=item_id,
                    language_code=language_code,
                    general_item_json=item_json,
                ))
            else:
                row.general_item_json = item_json
            session.commit()

    def get_branch(self, item_id: str, language_code: str) -> GeneralItem | None:
        """Return the cached GeneralItem for an item×language pair, or None."""
        with self._Session() as session:
            row = (
                session.query(_BranchRow)
                .filter_by(item_id=item_id, language_code=language_code)
                .first()
            )
            if row is None:
                return None
            return GeneralItem.model_validate_json(row.general_item_json)

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
    # Vocab coverage (text-level dedup)
    # ------------------------------------------------------------------

    def covered_texts(self, language_code: str, phase: Phase) -> set[str]:
        """Return the normalised text of all items registered for a given
        language and phase — used to prevent vocabulary repetition across lessons.

        Items are counted as covered if they have at least one branch for the
        given *language_code*, meaning they have been LLM-resolved before.
        """
        with self._Session() as session:
            rows = (
                session.query(_ItemRow.text_normalized)
                .join(
                    _BranchRow,
                    (_ItemRow.id == _BranchRow.item_id)
                    & (_BranchRow.language_code == language_code),
                )
                .filter(_ItemRow.phase == phase.value)
                .all()
            )
            return {row[0] for row in rows}

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
