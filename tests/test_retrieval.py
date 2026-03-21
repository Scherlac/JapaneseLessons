from pathlib import Path

import pytest

from jlesson.retrieval import (
    CanonicalMetadata,
    CanonicalLessonNode,
    ChromaVectorRetrievalService,
    FileBackedRetrievalService,
    LanguageBranch,
    RetrievalQuery,
    get_retrieval_service,
)


def test_canonical_metadata_uses_spike_storage_keys():
    metadata = CanonicalMetadata(
        theme="food",
        level="beginner",
        concept_type="noun",
        language_scope="eng-jap",
        grammar_progression_ja="beginner.l1.s2",
    )

    assert metadata.to_storage_dict() == {
        "theme": "food",
        "level": "beginner",
        "concept_type": "noun",
        "language_scope": "eng-jap",
        "grammar_progression.ja": "beginner.l1.s2",
    }


def test_file_backed_retrieval_projects_branch_payload(tmp_path: Path):
    store_path = tmp_path / "retrieval.json"
    service = FileBackedRetrievalService(store_path)

    service.ingest_canonical_node(
        CanonicalLessonNode(
            node_id="noun-water",
            canonical_text_en="water",
            concept_type="noun",
            metadata_tags={"theme": "food", "level": "beginner"},
            source_payload={"english": "water"},
        )
    )
    service.attach_branch(
        LanguageBranch(
            node_id="noun-water",
            language_code="japanese",
            payload={"japanese": "みず", "romaji": "mizu", "kanji": "水"},
        )
    )

    result = service.search(
        "water",
        requested_language="japanese",
        filters={"theme": "food", "level": "beginner"},
    )

    assert len(result.candidates) == 1
    assert result.material.nouns == [
        {"english": "water", "japanese": "みず", "romaji": "mizu", "kanji": "水"}
    ]


def test_file_backed_retrieval_accepts_spike_query_model(tmp_path: Path):
    store_path = tmp_path / "retrieval.json"
    service = FileBackedRetrievalService(store_path)

    service.ingest_canonical_node(
        CanonicalLessonNode(
            node_id="noun-water",
            canonical_text_en="Theme: food. Type: noun. English: water.",
            concept_type="noun",
            metadata=CanonicalMetadata(
                theme="food",
                level="beginner",
                concept_type="noun",
                language_scope="eng-jap",
            ),
            source_payload={"english": "water"},
        )
    )
    service.attach_branch(
        LanguageBranch(
            node_id="noun-water",
            language_code="japanese",
            payload={"japanese": "みず", "romaji": "mizu"},
        )
    )

    result = service.search(
        RetrievalQuery(
            query_id="q_theme_food",
            query_text="Beginner lesson concepts in theme food",
            query_type="theme_constraint",
            metadata_filter={"theme": "food", "concept_type": "noun"},
        ),
        requested_language="japanese",
    )

    assert len(result.candidates) == 1
    assert result.filters == {"theme": "food", "concept_type": "noun"}
    assert result.material.nouns[0]["english"] == "water"


def test_attach_branch_requires_existing_canonical_node(tmp_path: Path):
    service = FileBackedRetrievalService(tmp_path / "retrieval.json")

    with pytest.raises(ValueError):
        service.attach_branch(
            LanguageBranch(
                node_id="missing-node",
                language_code="japanese",
                payload={"japanese": "みず"},
            )
        )


def test_get_retrieval_service_selects_file_backend(tmp_path: Path):
    service = get_retrieval_service(True, tmp_path / "retrieval.json")

    assert isinstance(service, FileBackedRetrievalService)


def test_get_retrieval_service_selects_chroma_backend(tmp_path: Path):
    service = get_retrieval_service(
        True,
        tmp_path / "retrieval.json",
        backend="chroma",
        embedding_model="text-embedding-3-small",
    )

    assert isinstance(service, ChromaVectorRetrievalService)