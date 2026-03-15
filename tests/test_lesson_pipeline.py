"""Unit tests for jlesson.lesson_pipeline — pipeline steps and runner."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jlesson.curriculum import create_curriculum, get_grammar_by_id
from jlesson.lesson_pipeline import (
    GenerateSentencesStep,
    GrammarSelectStep,
    LessonConfig,
    LessonContext,
    NounPracticeStep,
    PersistContentStep,
    RegisterLessonStep,
    SelectVocabStep,
    StepInfo,
    VerbPracticeStep,
    _build_video_items,
    run_pipeline,
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
    {"english": "water", "japanese": "\u307f\u305a", "kanji": "\u6c34", "romaji": "mizu"},
    {"english": "bread", "japanese": "\u30d1\u30f3", "kanji": "\u30d1\u30f3", "romaji": "pan"},
    {"english": "rice", "japanese": "\u3054\u306f\u3093", "kanji": "\u3054\u98ef", "romaji": "gohan"},
    {"english": "tea", "japanese": "\u304a\u3061\u3083", "kanji": "\u304a\u8336", "romaji": "ocha"},
]

_VERBS = [
    {
        "english": "to eat",
        "japanese": "\u305f\u3079\u308b",
        "kanji": "\u98df\u3079\u308b",
        "romaji": "taberu",
        "type": "\u308b-verb",
        "masu_form": "\u98df\u3079\u307e\u3059",
    },
    {
        "english": "to drink",
        "japanese": "\u306e\u3080",
        "kanji": "\u98f2\u3080",
        "romaji": "nomu",
        "type": "\u3046-verb",
        "masu_form": "\u98f2\u307f\u307e\u3059",
    },
    {
        "english": "to buy",
        "japanese": "\u304b\u3046",
        "kanji": "\u8cb7\u3046",
        "romaji": "kau",
        "type": "\u3046-verb",
        "masu_form": "\u8cb7\u3044\u307e\u3059",
    },
    {
        "english": "to go",
        "japanese": "\u3044\u304f",
        "kanji": "\u884c\u304f",
        "romaji": "iku",
        "type": "\u3046-verb",
        "masu_form": "\u884c\u304d\u307e\u3059",
    },
]

_VOCAB = {"nouns": _NOUNS, "verbs": _VERBS}


# ---------------------------------------------------------------------------
# StepInfo
# ---------------------------------------------------------------------------


def test_step_info_label():
    info = StepInfo(index=3, total=9, name="generate_sentences", description="LLM")
    assert info.label == "[3/9]"


# ---------------------------------------------------------------------------
# SelectVocabStep
# ---------------------------------------------------------------------------


def test_select_vocab_populates_nouns_and_verbs(ctx):
    with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB):
        ctx = SelectVocabStep().execute(ctx)
    assert len(ctx.nouns) == 2
    assert len(ctx.verbs) == 2


def test_select_vocab_excludes_covered_nouns(config):
    c = LessonContext(config=config)
    c.curriculum = create_curriculum("Test")
    c.curriculum["covered_nouns"] = ["water", "bread"]
    with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB):
        c = SelectVocabStep().execute(c)
    fresh = {n["english"] for n in c.nouns}
    assert "rice" in fresh or "tea" in fresh


def test_select_vocab_with_seed_is_deterministic(config):
    config.seed = 42
    results = []
    for _ in range(2):
        c = LessonContext(config=config)
        c.curriculum = create_curriculum("T")
        with patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB):
            c = SelectVocabStep().execute(c)
        results.append([n["english"] for n in c.nouns])
    assert results[0] == results[1]


# ---------------------------------------------------------------------------
# GrammarSelectStep
# ---------------------------------------------------------------------------


def test_grammar_select_picks_valid_grammar(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    mock_result = {
        "selected_ids": ["action_present_affirmative"],
        "rationale": "Good start",
    }
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock_result):
        ctx = GrammarSelectStep().execute(ctx)
    assert len(ctx.selected_grammar) == 1
    assert ctx.selected_grammar[0]["id"] == "action_present_affirmative"


def test_grammar_select_falls_back_when_llm_empty(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    with patch("jlesson.lesson_pipeline._ask_llm", return_value={}):
        ctx = GrammarSelectStep().execute(ctx)
    assert len(ctx.selected_grammar) >= 1


def test_grammar_select_skips_unknown_ids(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    mock_result = {"selected_ids": ["nonexistent_grammar_id"]}
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock_result):
        ctx = GrammarSelectStep().execute(ctx)
    assert len(ctx.selected_grammar) == 0


# ---------------------------------------------------------------------------
# GenerateSentencesStep
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
                "japanese": "\u79c1\u306f\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "romaji": "watashi wa pan wo tabemasu",
                "person": "I",
            }
        ]
    }
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = GenerateSentencesStep().execute(ctx)
    assert len(ctx.sentences) == 1
    assert ctx.sentences[0]["english"] == "I eat bread."


def test_generate_sentences_adds_grammar_to_report(ctx):
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    mock = {
        "sentences": [
            {
                "grammar_id": "action_present_affirmative",
                "english": "I eat bread.",
                "japanese": "\u79c1\u306f\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "romaji": "watashi wa pan wo tabemasu",
                "person": "I",
            }
        ]
    }
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = GenerateSentencesStep().execute(ctx)
    md = ctx.report.render()
    assert "## Phase 3" in md
    assert "action_present_affirmative" in md


def test_generate_sentences_empty_llm_response(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    with patch("jlesson.lesson_pipeline._ask_llm", return_value={}):
        ctx = GenerateSentencesStep().execute(ctx)
    assert ctx.sentences == []


# ---------------------------------------------------------------------------
# NounPracticeStep
# ---------------------------------------------------------------------------


def test_noun_practice_stores_items(ctx):
    ctx.nouns = _NOUNS[:2]
    mock = {
        "noun_items": [
            {
                "english": "water",
                "japanese": "\u307f\u305a",
                "kanji": "\u6c34",
                "romaji": "mizu",
                "example_sentence_jp": "\u6c34\u3092\u98f2\u307f\u307e\u3059\u3002",
                "example_sentence_en": "I drink water.",
                "memory_tip": "tip",
            },
            {
                "english": "bread",
                "japanese": "\u30d1\u30f3",
                "kanji": "\u30d1\u30f3",
                "romaji": "pan",
                "example_sentence_jp": "\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "example_sentence_en": "I eat bread.",
                "memory_tip": "tip",
            },
        ]
    }
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = NounPracticeStep().execute(ctx)
    assert len(ctx.noun_items) == 2
    assert ctx.noun_items[0]["english"] == "water"


def test_noun_practice_adds_to_report(ctx):
    ctx.nouns = _NOUNS[:2]
    mock = {"noun_items": [dict(n) for n in _NOUNS[:2]]}
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = NounPracticeStep().execute(ctx)
    md = ctx.report.render()
    assert "## Vocabulary" in md
    assert "### Nouns" in md
    assert "## Phase 1" in md


def test_noun_practice_fills_missing_fields_from_source(ctx):
    ctx.nouns = _NOUNS[:2]
    mock = {"noun_items": [{"english": "water"}, {"english": "bread"}]}
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = NounPracticeStep().execute(ctx)
    assert ctx.noun_items[0]["japanese"] == "\u307f\u305a"
    assert ctx.noun_items[0]["romaji"] == "mizu"
    assert ctx.noun_items[1]["kanji"] == "\u30d1\u30f3"


def test_noun_practice_fallback_on_empty_llm(ctx):
    ctx.nouns = _NOUNS[:2]
    with patch("jlesson.lesson_pipeline._ask_llm", return_value={}):
        ctx = NounPracticeStep().execute(ctx)
    assert len(ctx.noun_items) == 2


# ---------------------------------------------------------------------------
# VerbPracticeStep
# ---------------------------------------------------------------------------


def test_verb_practice_stores_items(ctx):
    ctx.verbs = _VERBS[:2]
    mock = {
        "verb_items": [
            {
                "english": "to eat",
                "japanese": "\u305f\u3079\u308b",
                "kanji": "\u98df\u3079\u308b",
                "romaji": "taberu",
                "masu_form": "\u98df\u3079\u307e\u3059",
                "polite_forms": {},
                "memory_tip": "tip",
                "example_sentence_jp": "",
                "example_sentence_en": "",
            },
            {
                "english": "to drink",
                "japanese": "\u306e\u3080",
                "kanji": "\u98f2\u3080",
                "romaji": "nomu",
                "masu_form": "\u98f2\u307f\u307e\u3059",
                "polite_forms": {},
                "memory_tip": "tip",
                "example_sentence_jp": "",
                "example_sentence_en": "",
            },
        ]
    }
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = VerbPracticeStep().execute(ctx)
    assert len(ctx.verb_items) == 2
    assert ctx.verb_items[0]["masu_form"] == "\u98df\u3079\u307e\u3059"


def test_verb_practice_adds_to_report(ctx):
    ctx.verbs = _VERBS[:2]
    mock = {"verb_items": [dict(v) for v in _VERBS[:2]]}
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = VerbPracticeStep().execute(ctx)
    md = ctx.report.render()
    assert "### Verbs" in md
    assert "## Phase 2" in md


def test_verb_practice_fills_missing_fields_from_source(ctx):
    ctx.verbs = _VERBS[:2]
    mock = {"verb_items": [{"english": "to eat"}, {"english": "to drink"}]}
    with patch("jlesson.lesson_pipeline._ask_llm", return_value=mock):
        ctx = VerbPracticeStep().execute(ctx)
    assert ctx.verb_items[0]["masu_form"] == "\u98df\u3079\u307e\u3059"
    assert ctx.verb_items[1]["romaji"] == "nomu"


def test_verb_practice_fallback_on_empty_llm(ctx):
    ctx.verbs = _VERBS[:2]
    with patch("jlesson.lesson_pipeline._ask_llm", return_value={}):
        ctx = VerbPracticeStep().execute(ctx)
    assert len(ctx.verb_items) == 2


# ---------------------------------------------------------------------------
# RegisterLessonStep
# ---------------------------------------------------------------------------


def test_register_lesson_assigns_lesson_id(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = [dict(n) for n in _NOUNS[:2]]
    ctx.sentences = []
    ctx.verb_items = []
    ctx = RegisterLessonStep().execute(ctx)
    assert ctx.lesson_id == 1


def test_register_lesson_adds_header_to_report(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    ctx = RegisterLessonStep().execute(ctx)
    md = ctx.report.render()
    assert "# Lesson 1: Food" in md
    assert "action_present_affirmative" in md


def test_register_lesson_adds_completed_entry_to_curriculum(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    ctx = RegisterLessonStep().execute(ctx)
    assert len(ctx.curriculum["lessons"]) == 1
    assert ctx.curriculum["lessons"][0]["status"] == "completed"


def test_register_lesson_updates_covered_grammar(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    ctx = RegisterLessonStep().execute(ctx)
    assert "action_present_affirmative" in ctx.curriculum["covered_grammar_ids"]


def test_register_lesson_saves_curriculum_file(ctx, tmp_path):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    RegisterLessonStep().execute(ctx)
    assert (tmp_path / "curriculum.json").exists()


def test_register_lesson_sets_created_at(ctx):
    ctx.nouns = _NOUNS[:2]
    ctx.verbs = _VERBS[:2]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.sentences = []
    ctx.verb_items = []
    ctx = RegisterLessonStep().execute(ctx)
    assert ctx.created_at != ""
    assert ctx.created_at.endswith("Z")


# ---------------------------------------------------------------------------
# PersistContentStep
# ---------------------------------------------------------------------------


def test_persist_content_creates_file(ctx):
    ctx.lesson_id = 1
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = [
        {
            "english": "water",
            "japanese": "\u307f\u305a",
            "kanji": "\u6c34",
            "romaji": "mizu",
            "example_sentence_jp": "",
            "example_sentence_en": "",
            "memory_tip": "",
        },
    ]
    ctx.verb_items = []
    ctx.sentences = []
    ctx = PersistContentStep().execute(ctx)
    assert ctx.content_path is not None
    assert ctx.content_path.exists()


def test_persist_content_adds_artifact_to_report(ctx):
    ctx.lesson_id = 1
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]
    ctx.noun_items = []
    ctx.verb_items = []
    ctx.sentences = []
    ctx = PersistContentStep().execute(ctx)
    md = ctx.report.render()
    assert "Content JSON" in md


def test_persist_content_is_loadable(ctx, tmp_path):
    ctx.lesson_id = 7
    ctx.selected_grammar = [get_grammar_by_id("identity_present_affirmative")]
    ctx.noun_items = []
    ctx.verb_items = []
    ctx.sentences = []
    PersistContentStep().execute(ctx)
    from jlesson.lesson_store import load_lesson_content

    loaded = load_lesson_content(7, output_dir=tmp_path)
    assert loaded.lesson_id == 7
    assert loaded.theme == "food"


# ---------------------------------------------------------------------------
# _build_video_items
# ---------------------------------------------------------------------------


def test_build_video_items_noun_step_is_introduce():
    nouns = [{"english": "water", "japanese": "\u307f\u305a", "romaji": "mizu"}]
    items = _build_video_items(nouns, [])
    assert items[0]["step"] == "INTRODUCE"


def test_build_video_items_sentence_step_is_translate():
    sentences = [{"english": "I eat.", "japanese": "\u98df\u3079\u307e\u3059\u3002"}]
    items = _build_video_items([], sentences)
    assert items[0]["step"] == "TRANSLATE"


def test_build_video_items_counter_format():
    nouns = [{"english": "water", "japanese": "\u307f\u305a", "romaji": "mizu"}]
    sentences = [{"english": "I eat.", "japanese": "\u98df\u3079\u307e\u3059\u3002"}]
    items = _build_video_items(nouns, sentences)
    assert items[0]["counter"] == "1/2"
    assert items[1]["counter"] == "2/2"


def test_build_video_items_reveal_includes_romaji():
    nouns = [{"english": "water", "japanese": "\u307f\u305a", "romaji": "mizu"}]
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


def test_run_pipeline_no_video_completes(config):
    mock_grammar = {"selected_ids": ["action_present_affirmative"]}
    mock_sentences = {
        "sentences": [
            {
                "grammar_id": "action_present_affirmative",
                "english": "I eat bread.",
                "japanese": "\u79c1\u306f\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "romaji": "watashi wa pan wo tabemasu",
                "person": "I",
            }
        ]
    }
    mock_nouns = {
        "noun_items": [
            {
                "english": "water",
                "japanese": "\u307f\u305a",
                "kanji": "\u6c34",
                "romaji": "mizu",
                "example_sentence_jp": "\u6c34\u3092\u98f2\u307f\u307e\u3059\u3002",
                "example_sentence_en": "I drink water.",
                "memory_tip": "tip",
            },
            {
                "english": "bread",
                "japanese": "\u30d1\u30f3",
                "kanji": "\u30d1\u30f3",
                "romaji": "pan",
                "example_sentence_jp": "\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "example_sentence_en": "I eat bread.",
                "memory_tip": "tip",
            },
        ]
    }
    mock_verbs = {
        "verb_items": [
            {
                "english": "to eat",
                "japanese": "\u305f\u3079\u308b",
                "kanji": "\u98df\u3079\u308b",
                "romaji": "taberu",
                "masu_form": "\u98df\u3079\u307e\u3059",
                "polite_forms": {},
                "example_sentence_jp": "",
                "example_sentence_en": "",
                "memory_tip": "tip",
            },
            {
                "english": "to drink",
                "japanese": "\u306e\u3080",
                "kanji": "\u98f2\u3080",
                "romaji": "nomu",
                "masu_form": "\u98f2\u307f\u307e\u3059",
                "polite_forms": {},
                "example_sentence_jp": "",
                "example_sentence_en": "",
                "memory_tip": "tip",
            },
        ]
    }

    with (
        patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB),
        patch(
            "jlesson.lesson_pipeline._ask_llm",
            side_effect=[mock_grammar, mock_sentences, mock_nouns, mock_verbs],
        ),
    ):
        result = run_pipeline(config)

    assert result.lesson_id == 1
    assert result.content_path is not None
    assert result.content_path.exists()
    assert result.video_path is None
    assert result.report_path is not None
    assert result.report_path.exists()


def test_run_pipeline_persists_correct_theme(config, tmp_path):
    mock_grammar = {"selected_ids": ["action_present_affirmative"]}
    mock_sentences = {"sentences": []}
    mock_nouns = {"noun_items": []}
    mock_verbs = {"verb_items": []}

    with (
        patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB),
        patch(
            "jlesson.lesson_pipeline._ask_llm",
            side_effect=[mock_grammar, mock_sentences, mock_nouns, mock_verbs],
        ),
    ):
        result = run_pipeline(config)

    from jlesson.lesson_store import load_lesson_content

    loaded = load_lesson_content(result.lesson_id, output_dir=tmp_path)
    assert loaded.theme == "food"


def test_run_pipeline_curriculum_updated(config, tmp_path):
    mock_grammar = {"selected_ids": ["action_present_affirmative"]}
    mock_sentences = {"sentences": []}
    mock_nouns = {"noun_items": []}
    mock_verbs = {"verb_items": []}

    with (
        patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB),
        patch(
            "jlesson.lesson_pipeline._ask_llm",
            side_effect=[mock_grammar, mock_sentences, mock_nouns, mock_verbs],
        ),
    ):
        run_pipeline(config)

    import json as _json

    curriculum = _json.loads(
        (tmp_path / "curriculum.json").read_text(encoding="utf-8")
    )
    assert len(curriculum["lessons"]) == 1
    assert "action_present_affirmative" in curriculum["covered_grammar_ids"]


def test_run_pipeline_report_contains_all_sections(config):
    mock_grammar = {"selected_ids": ["action_present_affirmative"]}
    mock_sentences = {
        "sentences": [
            {
                "grammar_id": "action_present_affirmative",
                "english": "I eat bread.",
                "japanese": "\u79c1\u306f\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "romaji": "watashi wa pan wo tabemasu",
                "person": "I",
            }
        ]
    }
    mock_nouns = {
        "noun_items": [
            {
                "english": "water",
                "japanese": "\u307f\u305a",
                "kanji": "\u6c34",
                "romaji": "mizu",
                "example_sentence_jp": "",
                "example_sentence_en": "",
                "memory_tip": "",
            },
        ]
    }
    mock_verbs = {
        "verb_items": [
            {
                "english": "to eat",
                "japanese": "\u305f\u3079\u308b",
                "kanji": "\u98df\u3079\u308b",
                "romaji": "taberu",
                "masu_form": "\u98df\u3079\u307e\u3059",
                "polite_forms": {},
                "example_sentence_jp": "",
                "example_sentence_en": "",
                "memory_tip": "",
            },
        ]
    }

    with (
        patch("jlesson.lesson_pipeline._load_vocab", return_value=_VOCAB),
        patch(
            "jlesson.lesson_pipeline._ask_llm",
            side_effect=[mock_grammar, mock_sentences, mock_nouns, mock_verbs],
        ),
    ):
        result = run_pipeline(config)

    md = result.report_path.read_text(encoding="utf-8")
    assert "# Lesson 1: Food" in md
    assert "## Vocabulary" in md
    assert "## Phase 1" in md
    assert "## Phase 2" in md
    assert "## Phase 3" in md
    assert "## Summary" in md
    assert "## Pipeline Timetable" in md
