from pathlib import Path
from unittest.mock import patch

from jlesson.curriculum import create_curriculum, get_grammar_by_id
from jlesson.lesson_pipeline import GenerateSentencesStep, LessonConfig, LessonContext
from jlesson.models import GrammarItem
from jlesson.prompt_template import build_grammar_generate_prompt


def test_build_grammar_generate_prompt_includes_narrative():
    grammar = [GrammarItem(**get_grammar_by_id("action_present_affirmative"))]
    nouns = [
        {
            "english": "cat",
            "japanese": "ねこ",
            "kanji": "猫",
            "romaji": "neko",
        }
    ]
    verbs = [
        {
            "english": "to fly",
            "japanese": "とぶ",
            "kanji": "飛ぶ",
            "romaji": "tobu",
            "type": "う-verb",
            "masu_form": "飛びます",
        }
    ]

    from jlesson.item_generator import EngJapItemGenerator

    gen = EngJapItemGenerator()
    noun_items = [gen.convert_raw_noun(n) for n in nouns]
    verb_items = [gen.convert_raw_verb(v) for v in verbs]

    prompt = build_grammar_generate_prompt(
        grammar_specs=grammar,
        nouns=noun_items,
        verbs=verb_items,
        sentences_per_grammar=2,
        narrative="Kiki arrives in a seaside town and starts her delivery service.",
    )

    assert "NARRATIVE CONTEXT" in prompt
    assert "Kiki arrives in a seaside town" in prompt


def test_generate_sentences_passes_explicit_narrative_to_prompt(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        narrative="Introduce Kiki and her neighborhood.",
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")
    ctx.nouns = [
        {"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"}
    ]
    ctx.verbs = [
        {
            "english": "to fly",
            "japanese": "とぶ",
            "kanji": "飛ぶ",
            "romaji": "tobu",
            "type": "う-verb",
            "masu_form": "飛びます",
        }
    ]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]

    with patch.object(
        ctx.language_config.prompts,
        "build_grammar_generate_prompt",
        return_value="PROMPT",
    ) as mock_builder, patch(
        "jlesson.lesson_pipeline._ask_llm",
        return_value={"sentences": []},
    ):
        GenerateSentencesStep().execute(ctx)

    assert mock_builder.call_args.kwargs["narrative"] == "Introduce Kiki and her neighborhood."


def test_generate_sentences_uses_default_narrative_when_missing(tmp_path: Path):
    config = LessonConfig(
        theme="kikis delivery service",
        curriculum_path=tmp_path / "curriculum.json",
        verbose=False,
    )
    ctx = LessonContext(config=config)
    ctx.curriculum = create_curriculum("Test")
    ctx.nouns = [
        {"english": "cat", "japanese": "ねこ", "kanji": "猫", "romaji": "neko"}
    ]
    ctx.verbs = [
        {
            "english": "to fly",
            "japanese": "とぶ",
            "kanji": "飛ぶ",
            "romaji": "tobu",
            "type": "う-verb",
            "masu_form": "飛びます",
        }
    ]
    ctx.selected_grammar = [get_grammar_by_id("action_present_affirmative")]

    with patch.object(
        ctx.language_config.generator,
        "build_default_narrative",
        return_value="Auto narrative",
    ) as mock_default, patch.object(
        ctx.language_config.prompts,
        "build_grammar_generate_prompt",
        return_value="PROMPT",
    ) as mock_builder, patch(
        "jlesson.lesson_pipeline._ask_llm",
        return_value={"sentences": []},
    ):
        GenerateSentencesStep().execute(ctx)

    mock_default.assert_called_once()
    assert mock_builder.call_args.kwargs["narrative"] == "Auto narrative"
