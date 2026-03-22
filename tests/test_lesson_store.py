"""Unit tests for jlesson.lesson_store — JSON persistence layer."""

import json

import pytest

from jlesson.lesson_store import load_lesson_content, save_lesson_content
from jlesson.models import LessonContent, NounItem, Sentence, VerbItem, GeneralItem, PartialItem, Phase


@pytest.fixture()
def sample_content() -> LessonContent:
    return LessonContent(
        lesson_id=1,
        theme="food",
        grammar_ids=["action_present_affirmative"],
        words=[
            GeneralItem(
                phase=Phase.NOUNS,
                source=PartialItem(display_text="water", extra={"english": "water"}),
                target=PartialItem(display_text="みず", pronunciation="mizu", extra={"kanji": "水", "japanese": "みず", "romaji": "mizu", "example_sentence_jp": "水を飲みます。", "example_sentence_en": "I drink water.", "memory_tip": "Sounds like 'mizu'."}),
            ),
            GeneralItem(
                phase=Phase.VERBS,
                source=PartialItem(display_text="to drink", extra={"english": "to drink"}),
                target=PartialItem(display_text="のむ", pronunciation="nomu", extra={"kanji": "飲む", "japanese": "のむ", "romaji": "nomu", "masu_form": "飲みます", "polite_forms": {"present_aff": "飲みます", "present_neg": "飲みません", "past_aff": "飲みました", "past_neg": "飲みませんでした"}, "memory_tip": "Rhymes with 'nome' in Italian."}),
            ),
        ],
        sentences=[
            Sentence(
                grammar_id="action_present_affirmative",
                phase=Phase.GRAMMAR,
                source=PartialItem(display_text="I drink water.", extra={"english": "I drink water."}),
                target=PartialItem(display_text="私は水を飲みます。", pronunciation="watashi wa mizu wo nomimasu", extra={"japanese": "私は水を飲みます。", "romaji": "watashi wa mizu wo nomimasu"}),
                grammar_parameters={"person": "I"},
            )
        ],
        created_at="2026-03-15T12:00:00Z",
    )


# ---------------------------------------------------------------------------
# save_lesson_content
# ---------------------------------------------------------------------------

def test_save_creates_file(tmp_path, sample_content):
    path = save_lesson_content(sample_content, output_dir=tmp_path)
    assert path.exists()


def test_save_filename_is_content_json(tmp_path, sample_content):
    path = save_lesson_content(sample_content, output_dir=tmp_path)
    assert path.name == "content.json"


def test_save_directory_named_by_lesson_id(tmp_path, sample_content):
    path = save_lesson_content(sample_content, output_dir=tmp_path)
    assert path.parent.name == "lesson_001"


def test_save_produces_valid_json(tmp_path, sample_content):
    path = save_lesson_content(sample_content, output_dir=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["lesson_id"] == 1
    assert data["theme"] == "food"


def test_save_includes_noun_items(tmp_path, sample_content):
    save_lesson_content(sample_content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert len(loaded.noun_items) == 1
    assert loaded.noun_items[0].source.display_text == "water"


def test_save_includes_verb_items(tmp_path, sample_content):
    save_lesson_content(sample_content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert len(loaded.verb_items) == 1
    assert loaded.verb_items[0].target.extra.get("masu_form") == "飲みます"


def test_save_includes_sentences(tmp_path, sample_content):
    path = save_lesson_content(sample_content, output_dir=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["sentences"]) == 1
    assert data["sentences"][0]["grammar_id"] == "action_present_affirmative"


def test_save_creates_parent_directory_if_missing(tmp_path, sample_content):
    nested = tmp_path / "deep" / "nested"
    path = save_lesson_content(sample_content, output_dir=nested)
    assert path.exists()


def test_save_returns_correct_path(tmp_path, sample_content):
    path = save_lesson_content(sample_content, output_dir=tmp_path)
    assert path == tmp_path / "lesson_001" / "content.json"


def test_save_overwrites_existing_file(tmp_path, sample_content):
    save_lesson_content(sample_content, output_dir=tmp_path)
    sample_content.theme = "travel"
    save_lesson_content(sample_content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert loaded.theme == "travel"


def test_save_lesson_id_zero_padded_three_digits(tmp_path):
    content = LessonContent(lesson_id=5, theme="food", grammar_ids=[])
    path = save_lesson_content(content, output_dir=tmp_path)
    assert path.parent.name == "lesson_005"


def test_save_lesson_id_large_number(tmp_path):
    content = LessonContent(lesson_id=42, theme="travel", grammar_ids=[])
    path = save_lesson_content(content, output_dir=tmp_path)
    assert path.parent.name == "lesson_042"


def test_save_multiple_lessons_in_separate_dirs(tmp_path):
    for i in range(1, 4):
        save_lesson_content(
            LessonContent(lesson_id=i, theme="food", grammar_ids=[]),
            output_dir=tmp_path,
        )
    assert (tmp_path / "lesson_001" / "content.json").exists()
    assert (tmp_path / "lesson_002" / "content.json").exists()
    assert (tmp_path / "lesson_003" / "content.json").exists()


# ---------------------------------------------------------------------------
# load_lesson_content
# ---------------------------------------------------------------------------

def test_load_roundtrip(tmp_path, sample_content):
    save_lesson_content(sample_content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert loaded.lesson_id == 1
    assert loaded.theme == "food"


def test_load_noun_items_roundtrip(tmp_path, sample_content):
    save_lesson_content(sample_content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert len(loaded.noun_items) == 1
    assert loaded.noun_items[0].source.extra["english"] == "water"
    assert loaded.noun_items[0].target.extra["kanji"] == "水"


def test_load_verb_items_roundtrip(tmp_path, sample_content):
    save_lesson_content(sample_content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert loaded.verb_items[0].target.extra["polite_forms"]["past_neg"] == "飲みませんでした"


def test_load_sentences_roundtrip(tmp_path, sample_content):
    save_lesson_content(sample_content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert loaded.sentences[0].target.extra["japanese"] == "私は水を飲みます。"


def test_load_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_lesson_content(99, output_dir=tmp_path)


def test_load_empty_noun_items(tmp_path):
    content = LessonContent(lesson_id=1, theme="food", grammar_ids=["g1"])
    save_lesson_content(content, output_dir=tmp_path)
    loaded = load_lesson_content(1, output_dir=tmp_path)
    assert loaded.noun_items == []
    assert loaded.sentences == []
