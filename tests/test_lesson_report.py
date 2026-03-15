"""Unit tests for jlesson.lesson_report — ReportBuilder."""

from pathlib import Path

import pytest

from jlesson.lesson_report import ReportBuilder, save_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def builder() -> ReportBuilder:
    return ReportBuilder()


# ---------------------------------------------------------------------------
# add() and render() basics
# ---------------------------------------------------------------------------


def test_empty_builder_renders_single_newline(builder):
    assert builder.render() == "\n"


def test_single_section(builder):
    builder.add("header", "# Title\n")
    md = builder.render()
    assert md.startswith("# Title\n")


def test_sections_ordered_by_section_order(builder):
    builder.add("summary", "## Summary\n")
    builder.add("header", "# Header\n")
    md = builder.render()
    assert md.index("# Header") < md.index("## Summary")


def test_multiple_blocks_in_same_section(builder):
    builder.add("vocabulary", "### Nouns\n")
    builder.add("vocabulary", "### Verbs\n")
    md = builder.render()
    assert md.index("### Nouns") < md.index("### Verbs")


# ---------------------------------------------------------------------------
# record_time / timetable
# ---------------------------------------------------------------------------


def test_timetable_included(builder):
    builder.record_time("select_vocab", 0.1)
    builder.record_time("grammar_select", 5.2)
    md = builder.render()
    assert "## Pipeline Timetable" in md
    assert "| select_vocab | 0.1s |" in md
    assert "| **Total** | **5.3s** |" in md


def test_timetable_absent_when_no_times(builder):
    md = builder.render()
    assert "## Pipeline Timetable" not in md


# ---------------------------------------------------------------------------
# add_artifact / artifacts section
# ---------------------------------------------------------------------------


def test_artifacts_included(builder):
    builder.add_artifact("Video", Path("/out/video.mp4"))
    builder.add_artifact("Content JSON", Path("/out/content.json"))
    md = builder.render()
    assert "## Artifacts" in md
    assert "Video" in md
    assert "content.json" in md


def test_artifacts_absent_when_none(builder):
    md = builder.render()
    assert "## Artifacts" not in md


# ---------------------------------------------------------------------------
# Full report integration (matching the old generate_report output)
# ---------------------------------------------------------------------------


def _build_full_report() -> str:
    """Simulate what the pipeline steps would produce."""
    rb = ReportBuilder()

    # RegisterLessonStep sets the header
    rb.add(
        "header",
        "\n".join(
            [
                "# Lesson 1: Food",
                "",
                "> Generated: 2026-03-15T12:00:00Z",
                "> Grammar: action_present_affirmative, identity_present_affirmative",
                "",
            ]
        ),
    )

    # NounPracticeStep: vocabulary nouns table
    rb.add(
        "vocabulary",
        "\n".join(
            [
                "## Vocabulary",
                "",
                "### Nouns",
                "",
                "| # | English | Japanese | Romaji |",
                "|---|---------|----------|--------|",
                "| 1 | bread | \u30d1\u30f3 | pan |",
                "| 2 | water | \u307f\u305a | mizu |",
                "",
            ]
        ),
    )

    # NounPracticeStep: noun practice section
    rb.add(
        "noun_practice",
        "\n".join(
            [
                "## Phase 1 \u2014 Noun Practice",
                "",
                "### 1. bread",
                "",
                "- **Japanese:** \u30d1\u30f3",
                "- **Romaji:** pan",
                "- **Example:** \u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "  *I eat bread.*",
                "- **Memory tip:** Sounds like English 'pan'.",
                "",
                "### 2. water",
                "",
                "- **Japanese:** \u307f\u305a",
                "- **Romaji:** mizu",
                "- **Example:** \u6c34\u3092\u98f2\u307f\u307e\u3059\u3002",
                "  *I drink water.*",
                "- **Memory tip:** Think of a mist of water.",
                "",
            ]
        ),
    )

    # VerbPracticeStep: vocabulary verbs table
    rb.add(
        "vocabulary",
        "\n".join(
            [
                "### Verbs",
                "",
                "| # | English | Japanese | Romaji | Polite form |",
                "|---|---------|----------|--------|-------------|",
                "| 1 | to eat | \u305f\u3079\u308b | taberu | \u98df\u3079\u307e\u3059 |",
                "",
            ]
        ),
    )

    # VerbPracticeStep: verb practice section
    rb.add(
        "verb_practice",
        "\n".join(
            [
                "## Phase 2 \u2014 Verb Practice",
                "",
                "### 1. to eat",
                "",
                "- **Japanese:** \u305f\u3079\u308b",
                "- **Romaji:** taberu",
                "- **Polite form:** \u98df\u3079\u307e\u3059",
                "  - negative: \u98df\u3079\u307e\u305b\u3093",
                "  - past: \u98df\u3079\u307e\u3057\u305f",
                "- **Example:** \u79c1\u306f\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002",
                "  *I eat bread.*",
                "- **Memory tip:** ta-BEAR-u: a bear eating.",
                "",
            ]
        ),
    )

    # GenerateSentencesStep: grammar practice section
    rb.add(
        "grammar_practice",
        "\n".join(
            [
                "## Phase 3 \u2014 Grammar Practice",
                "",
                "### action_present_affirmative",
                "",
                "| # | Person | English | Japanese | Romaji |",
                "|---|--------|---------|----------|--------|",
                "| 1 | I | I eat bread. | \u79c1\u306f\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002 "
                "| watashi wa pan o tabemasu |",
                "| 2 | You | You drink water. | \u3042\u306a\u305f\u306f\u6c34\u3092\u98f2\u307f\u307e\u3059\u3002 "
                "| anata wa mizu o nomimasu |",
                "",
                "### identity_present_affirmative",
                "",
                "| # | Person | English | Japanese | Romaji |",
                "|---|--------|---------|----------|--------|",
                "| 1 | I | I am a student. | \u79c1\u306f\u5b66\u751f\u3067\u3059\u3002 "
                "| watashi wa gakusei desu |",
                "",
            ]
        ),
    )

    # SaveReportStep: summary section
    rb.add(
        "summary",
        "\n".join(
            [
                "## Summary",
                "",
                "| Phase | Items | Repetitions | Touches |",
                "|-------|-------|-------------|---------|",
                "| Nouns | 2 | 5 | 10 |",
                "| Verbs | 1 | 5 | 5 |",
                "| Grammar | 3 | 3 | 9 |",
                "| **Total** | **6** | | **24** |",
                "",
            ]
        ),
    )

    return rb.render()


class TestFullReport:
    """Integration tests verifying the assembled report matches expected output."""

    @pytest.fixture(autouse=True)
    def _build(self):
        self.md = _build_full_report()

    # Header
    def test_starts_with_lesson_header(self):
        assert self.md.startswith("# Lesson 1: Food\n")

    def test_includes_created_at(self):
        assert "2026-03-15T12:00:00Z" in self.md

    def test_includes_grammar_ids(self):
        assert "action_present_affirmative" in self.md
        assert "identity_present_affirmative" in self.md

    # Vocabulary
    def test_vocabulary_noun_table(self):
        assert "| 1 | bread | \u30d1\u30f3 | pan |" in self.md

    def test_vocabulary_verb_table(self):
        assert "| 1 | to eat | \u305f\u3079\u308b | taberu | \u98df\u3079\u307e\u3059 |" in self.md

    # Noun practice
    def test_noun_practice_heading(self):
        assert "## Phase 1 \u2014 Noun Practice" in self.md

    def test_noun_practice_items(self):
        assert "### 1. bread" in self.md
        assert "### 2. water" in self.md

    def test_noun_example_and_tip(self):
        assert "\u30d1\u30f3\u3092\u98df\u3079\u307e\u3059\u3002" in self.md
        assert "Sounds like English 'pan'." in self.md

    # Verb practice
    def test_verb_practice_heading(self):
        assert "## Phase 2 \u2014 Verb Practice" in self.md

    def test_verb_polite_forms(self):
        assert "negative: \u98df\u3079\u307e\u305b\u3093" in self.md
        assert "past: \u98df\u3079\u307e\u3057\u305f" in self.md

    # Grammar practice
    def test_grammar_grouped_by_id(self):
        assert "### action_present_affirmative" in self.md
        assert "### identity_present_affirmative" in self.md

    def test_grammar_sentence_table(self):
        assert "| 1 | I | I eat bread." in self.md
        assert "| 2 | You | You drink water." in self.md

    # Summary
    def test_summary_counts(self):
        assert "| Nouns | 2 | 5 | 10 |" in self.md
        assert "| Verbs | 1 | 5 | 5 |" in self.md
        assert "| Grammar | 3 | 3 | 9 |" in self.md
        assert "| **Total** | **6** | | **24** |" in self.md

    # Section ordering
    def test_vocabulary_before_practice(self):
        assert self.md.index("## Vocabulary") < self.md.index("## Phase 1")

    def test_practice_before_grammar(self):
        assert self.md.index("## Phase 2") < self.md.index("## Phase 3")

    def test_grammar_before_summary(self):
        assert self.md.index("## Phase 3") < self.md.index("## Summary")

    # Trailing newline
    def test_ends_with_single_newline(self):
        assert self.md.endswith("\n")
        assert not self.md.endswith("\n\n")


# ---------------------------------------------------------------------------
# Artifacts + timetable in full report
# ---------------------------------------------------------------------------


def test_full_report_with_artifacts_and_timetable():
    rb = ReportBuilder()
    rb.add("header", "# Lesson 1: Test\n")
    rb.add_artifact("Video", Path("/output/video.mp4"))
    rb.record_time("select_vocab", 0.1)
    rb.record_time("grammar_select", 5.2)
    md = rb.render()
    assert "## Artifacts" in md
    assert "video.mp4" in md
    assert "## Pipeline Timetable" in md
    assert "| **Total** | **5.3s** |" in md
    # Artifacts before timetable
    assert md.index("## Artifacts") < md.index("## Pipeline Timetable")


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_creates_file(tmp_path):
    md = "# Test\n"
    path = save_report(md, tmp_path / "sub" / "report.md")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == md
