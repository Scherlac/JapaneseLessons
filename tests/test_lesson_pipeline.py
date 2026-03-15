"""Unit tests for jlesson.lesson_pipeline — pipeline stages and runner."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jlesson.curriculum import create_curriculum, get_grammar_by_id
from jlesson.lesson_pipeline import (
    LessonConfig,
    LessonContext,
    _build_video_items,
    run_pipeline,
    stage_generate_sentences,
    stage_grammar_select,
    stage_noun_practice,
    stage_persist_content,
    stage_register_lesson,
    stage_select_vocab,
    stage_verb_practice,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def config(tmp_path: Path) -> LessonConfig:
    return LessonConfig(
        theme="food",
        curriculum_path=tmp_path / "curriculum.json",
        output_dir=tmp_path,
        num_nouns=2,
        num_verbs=2,
        sentences_per_grammar=2,
        render_video=False,
        verbose=False,
    )


@pytest.fixture()
def ctx(config: LessonConfig) -> LessonContext:
    c = LessonContext(config=config)
    c.curriculum = create_curriculum("Test")
    return c


_NOUNS = [
    {"english": "water",  "japanese": "みず",  "kanji": "水",    "romaji": "mizu"},
    {"english": "bread",  "japanese": "パン",  "kanji": "パン",  "romaji": "pan"},
    {"english": "rice",   "japanese": "ごはん", "kanji": "ご飯", "romaji": "gohan"},
    {"english": "tea",    "japanese": "おちゃ", "kanji": "お茶", "romaji": "ocha"},
]

_VERBS = [
    {"english": "to eat",   "japanese": "たべる", "kanji": "食べる", "romaji": "taberu",
     "type": "る-verb", "masu_form": "食べます"},
    {"english": "to drink", "japanese": "のむ",   "kanji": "飲む",   "romaji": "nomu",
     "type": "う-verb", "masu_form": "飲みます"},
    {"english": "to buy",   "japanese": "かう",   "kanji": "買う",   "romaji": "kau",
     "type": "う-verb", "masu_form": "買います"},
    {"english": "to go",    "japanese": "いく",   "kanji": "行く",   "romaji": "iku",
     "type": "う-verb", "masu_form": "行きます"},
]

_VOCAB = {"nouns": _NOUNS, "verbs": _VERBS}


# ---------------------------------------------------------------------------
# stage_select_vocab
# ---------------------------------------------------------------------------

def test_select_vocab_populates_nouns_and_verbs(ctx):
    with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB):
        ctx = stage_select_vocab(ctx)
    assert len(ctx.nouns) == 2
    assert len(ctx.verbs) == 2


def test_select_vocab_excludes_covered_nouns(config, tmp_path):
    c = LessonContext(config=config)
    c.curriculum = create_curriculum("Test")
    c.curriculum["covered_nouns"] = ["water", "bread"]
    with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB):
        c = stage_select_vocab(c)
    # Fresh nouns should come first; covered ones filled in if needed
    fresh = {n["english"] for n in c.nouns}
    assert "rice" in fresh or "tea" in fresh


def test_select_vocab_with_seed_is_deterministic(config, tmp_path):
    config.seed = 42
    results = []
    for _ in range(2):
        c = LessonContext(config=config)
        c.curriculum = create_curriculum("T")
        with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB):
            c = stage_select_vocab(c)
        results.append([n["english"] for n in c.nouns])
    assert results[0] == results[1]


# ---------------------------------------------------------------------------
# stage_grammar_select
# ---------------------------------------------------------------------------

def test_grammar_select_picks_valid_grammar(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    mock_result = {"selected_ids": ["action_present_affirmative"], "rationale": "Good start"}
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value=mock_result):
        ctx = stage_grammar_select(ctx)
    assert len(ctx.selected_grammar) == 1
    assert ctx.selected_grammar[0]["id"] == "action_present_affirmative"


def test_grammar_select_falls_back_when_llm_empty(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value={}):
        ctx = stage_grammar_select(ctx)
    assert len(ctx.selected_grammar) >= 1


def test_grammar_select_skips_unknown_ids(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    mock_result = {"selected_ids": ["nonexistent_grammar_id"]}
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value=mock_result):
        ctx = stage_grammar_select(ctx)
    assert len(ctx.selected_grammar) == 0


# ---------------------------------------------------------------------------
# stage_generate_sentences
# ---------------------------------------------------------------------------

def test_generate_sentences_stores_sentences(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    mock = {
        "sentences": [
            {
                "grammar_id": "action_present_affirmative",
                "english": "I eat bread.",
                "japanese": "私はパンを食べます。",
                "romaji": "watashi wa pan wo tabemasu",
                "person": "I",
            }
        ]
    }
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value=mock):
        ctx = stage_generate_sentences(ctx)
    assert len(ctx.sentences) == 1
    assert ctx.sentences[0]["english"] == "I eat bread."


def test_generate_sentences_empty_llm_response(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value={}):
        ctx = stage_generate_sentences(ctx)
    assert ctx.sentences == []


# ---------------------------------------------------------------------------
# stage_noun_practice
# ---------------------------------------------------------------------------

def test_noun_practice_stores_items(ctx):
    ctx.nouns = _NOUNS[:2]
    mock = {
        "noun_items": [
            {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu",
             "example_sentence_jp": "水を飲みます。", "example_sentence_en": "I drink water.",
             "memory_tip": "tip"},
            {"english": "bread", "japanese": "パン", "kanji": "パン", "romaji": "pan",
             "example_sentence_jp": "パンを食べます。", "example_sentence_en": "I eat bread.",
             "memory_tip": "tip"},
        ]
    }
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value=mock):
        ctx = stage_noun_practice(ctx)
    assert len(ctx.noun_items) == 2
    assert ctx.noun_items[0]["english"] == "water"


def test_noun_practice_fills_missing_fields_from_source(ctx):
    ctx.nouns = _NOUNS[:2]
    # LLM omits japanese/kanji/romaji fields
    mock = {"noun_items": [{"english": "water"}, {"english": "bread"}]}
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value=mock):
        ctx = stage_noun_practice(ctx)
    assert ctx.noun_items[0]["japanese"] == "みず"
    assert ctx.noun_items[0]["romaji"] == "mizu"
    assert ctx.noun_items[1]["kanji"] == "パン"


def test_noun_practice_fallback_on_empty_llm(ctx):
    ctx.nouns = _NOUNS[:2]
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value={}):
        ctx = stage_noun_practice(ctx)
    assert len(ctx.noun_items) == 2


# ---------------------------------------------------------------------------
# stage_verb_practice
# ---------------------------------------------------------------------------

def test_verb_practice_stores_items(ctx):
    ctx.verbs = _VERBS[:2]
    mock = {
        "verb_items": [
            {"english": "to eat",   "japanese": "たべる", "kanji": "食べる", "romaji": "taberu",
             "masu_form": "食べます", "polite_forms": {}, "memory_tip": "tip",
             "example_sentence_jp": "", "example_sentence_en": ""},
            {"english": "to drink", "japanese": "のむ",   "kanji": "飲む",   "romaji": "nomu",
             "masu_form": "飲みます", "polite_forms": {}, "memory_tip": "tip",
             "example_sentence_jp": "", "example_sentence_en": ""},
        ]
    }
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value=mock):
        ctx = stage_verb_practice(ctx)
    assert len(ctx.verb_items) == 2
    assert ctx.verb_items[0]["masu_form"] == "食べます"


def test_verb_practice_fills_missing_fields_from_source(ctx):
    ctx.verbs = _VERBS[:2]
    mock = {"verb_items": [{"english": "to eat"}, {"english": "to drink"}]}
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value=mock):
        ctx = stage_verb_practice(ctx)
    assert ctx.verb_items[0]["masu_form"] == "食べます"
    assert ctx.verb_items[1]["romaji"] == "nomu"


def test_verb_practice_fallback_on_empty_llm(ctx):
    ctx.verbs = _VERBS[:2]
    with patch("jlesson.lesson_pipeline.ask_llm_json_free", return_value={}):
        ctx = stage_verb_practice(ctx)
    assert len(ctx.verb_items) == 2


# ---------------------------------------------------------------------------
# stage_register_lesson
# ---------------------------------------------------------------------------

def test_register_lesson_assigns_lesson_id(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = [dict(n) for n in _NOUNS[:2]]
    ctx.sentences = []
    ctx.verb_items = []
    ctx = stage_register_lesson(ctx)
    assert ctx.lesson_id == 1


def test_register_lesson_adds_completed_entry_to_curriculum(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    ctx = stage_register_lesson(ctx)
    assert len(ctx.curriculum["lessons"]) == 1
    assert ctx.curriculum["lessons"][0]["status"] == "completed"


def test_register_lesson_updates_covered_grammar(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    ctx = stage_register_lesson(ctx)
    assert "action_present_affirmative" in ctx.curriculum["covered_grammar_ids"]


def test_register_lesson_saves_curriculum_file(ctx, tmp_path):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    stage_register_lesson(ctx)
    assert (tmp_path / "curriculum.json").exists()


# ---------------------------------------------------------------------------
# stage_persist_content
# ---------------------------------------------------------------------------

def test_persist_content_creates_file(ctx, tmp_path):
    ctx.lesson_id = 1
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = [
        {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu",
         "example_sentence_jp": "", "example_sentence_en": "", "memory_tip": ""},
    ]
    ctx.verb_items = []
    ctx.sentences = []
    ctx = stage_persist_content(ctx)
    assert ctx.content_path is not None
    assert ctx.content_path.exists()


def test_persist_content_is_loadable(ctx, tmp_path):
    ctx.lesson_id = 7
    ctx.selected_grammar = [get_grammar_by_id("identity_present_affirmative")]
    ctx.noun_items = []
    ctx.verb_items = []
    ctx.sentences = []
    stage_persist_content(ctx)
    from jlesson.lesson_store import load_lesson_content
    loaded = load_lesson_content(7, output_dir=tmp_path)
    assert loaded.lesson_id == 7
    assert loaded.theme == "food"


# ---------------------------------------------------------------------------
# _build_video_items
# ---------------------------------------------------------------------------

def test_build_video_items_noun_step_is_introduce():
    nouns = [{"english": "water", "japanese": "みず", "romaji": "mizu"}]
    items = _build_video_items(nouns, [])
    assert items[0]["step"] == "INTRODUCE"


def test_build_video_items_sentence_step_is_translate():
    sentences = [{"english": "I eat.", "japanese": "食べます。"}]
    items = _build_video_items([], sentences)
    assert items[0]["step"] == "TRANSLATE"


def test_build_video_items_counter_format():
    nouns = [{"english": "water", "japanese": "みず", "romaji": "mizu"}]
    sentences = [{"english": "I eat.", "japanese": "食べます。"}]
    items = _build_video_items(nouns, sentences)
    assert items[0]["counter"] == "1/2"
    assert items[1]["counter"] == "2/2"


def test_build_video_items_reveal_includes_romaji():
    nouns = [{"english": "water", "japanese": "みず", "romaji": "mizu"}]
    items = _build_video_items(nouns, [])
    assert "mizu" in items[0]["reveal"]


def test_build_video_items_empty_inputs():
    assert _build_video_items([], []) == []


def test_build_video_items_total_count():
    nouns = [{"english": "w", "japanese": "j", "romaji": "r"}] * 3
    sents = [{"english": "e", "japanese": "j"}] * 2
    assert len(_build_video_items(nouns, sents)) == 5


# ---------------------------------------------------------------------------
# run_pipeline (integration — mocked LLM and vocab, no video)
# ---------------------------------------------------------------------------

def test_run_pipeline_no_video_completes(config, tmp_path):
    mock_grammar = {"selected_ids": ["action_present_affirmative"]}
    mock_sentences = {
        "sentences": [{
            "grammar_id": "action_present_affirmative",
            "english": "I eat bread.",
            "japanese": "私はパンを食べます。",
            "romaji": "watashi wa pan wo tabemasu",
            "person": "I",
        }]
    }
    mock_nouns = {
        "noun_items": [
            {"english": "water", "japanese": "みず", "kanji": "水", "romaji": "mizu",
             "example_sentence_jp": "水を飲みます。", "example_sentence_en": "I drink water.",
             "memory_tip": "tip"},
            {"english": "bread", "japanese": "パン", "kanji": "パン", "romaji": "pan",
             "example_sentence_jp": "パンを食べます。", "example_sentence_en": "I eat bread.",
             "memory_tip": "tip"},
        ]
    }
    mock_verbs = {
        "verb_items": [
            {"english": "to eat", "japanese": "たべる", "kanji": "食べる", "romaji": "taberu",
             "masu_form": "食べます", "polite_forms": {}, "example_sentence_jp": "",
             "example_sentence_en": "", "memory_tip": "tip"},
            {"english": "to drink", "japanese": "のむ", "kanji": "飲む", "romaji": "nomu",
             "masu_form": "飲みます", "polite_forms": {}, "example_sentence_jp": "",
             "example_sentence_en": "", "memory_tip": "tip"},
        ]
    }

    with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB), \
         patch("jlesson.lesson_pipeline.ask_llm_json_free",
               side_effect=[mock_grammar, mock_sentences, mock_nouns, mock_verbs]):
        result = run_pipeline(config)

    assert result.lesson_id == 1
    assert result.content_path is not None
    assert result.content_path.exists()
    assert result.video_path is None  # video rendering was skipped


def test_run_pipeline_persists_correct_theme(config, tmp_path):
    mock_grammar = {"selected_ids": ["action_present_affirmative"]}
    mock_sentences = {"sentences": []}
    mock_nouns = {"noun_items": []}
    mock_verbs = {"verb_items": []}

    with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB), \
         patch("jlesson.lesson_pipeline.ask_llm_json_free",
               side_effect=[mock_grammar, mock_sentences, mock_nouns, mock_verbs]):
        result = run_pipeline(config)

    from jlesson.lesson_store import load_lesson_content
    loaded = load_lesson_content(result.lesson_id, output_dir=tmp_path)
    assert loaded.theme == "food"


def test_run_pipeline_curriculum_updated(config, tmp_path):
    mock_grammar = {"selected_ids": ["action_present_affirmative"]}
    mock_sentences = {"sentences": []}
    mock_nouns = {"noun_items": []}
    mock_verbs = {"verb_items": []}

    with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB), \
         patch("jlesson.lesson_pipeline.ask_llm_json_free",
               side_effect=[mock_grammar, mock_sentences, mock_nouns, mock_verbs]):
        run_pipeline(config)

    import json as _json
    curriculum = _json.loads((tmp_path / "curriculum.json").read_text(encoding="utf-8"))
    assert len(curriculum["lessons"]) == 1
    assert "action_present_affirmative" in curriculum["covered_grammar_ids"]
