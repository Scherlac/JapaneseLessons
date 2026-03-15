"""
Spike 08 — Curriculum-Driven LLM Lesson Planning

Tests the full end-to-end curriculum workflow:
  1. Load food vocab (existing)
  2. Create/load curriculum from curriculum/curriculum.json
  3. Show unlocked grammar steps (prerequisite graph)
  4. Grammar select  — LLM picks the grammar point for next lesson
  5. Grammar generate — LLM writes example sentences
  6. Content validate — LLM cross-checks the sentences
  7. Add lesson to curriculum + print summary

Run with LM Studio running at http://localhost:1234:
    conda run -n base python spike/spike_08_curriculum.py
"""

import json
import sys
import time
from pathlib import Path

# Ensure project root is on the path when run from spike/
sys.path.insert(0, str(Path(__file__).parent.parent))

from curriculum import (
    GRAMMAR_PROGRESSION,
    add_lesson,
    complete_lesson,
    create_curriculum,
    get_next_grammar,
    load_curriculum,
    save_curriculum,
    suggest_new_vocab,
    summary,
)
from llm_client import ask_llm_json_free
from prompt_template import (
    build_content_validate_prompt,
    build_grammar_generate_prompt,
    build_grammar_select_prompt,
    build_noun_practice_prompt,
    build_verb_practice_prompt,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

VOCAB_DIR = Path(__file__).parent.parent / "vocab"
CURRICULUM_PATH = Path(__file__).parent.parent / "curriculum" / "curriculum.json"
OUTPUT_PATH = Path(__file__).parent / "output" / "spike_08_curriculum.json"


def _hr(label: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {label}")
    print('═' * 60)


def _check_lm_studio() -> bool:
    try:
        import requests
        r = requests.get("http://localhost:1234/v1/models", timeout=4)
        return r.status_code == 200
    except Exception:
        return False


# ── Step helpers ──────────────────────────────────────────────────────────────

def step_show_grammar_table() -> None:
    _hr("Grammar Progression Table")
    for g in GRAMMAR_PROGRESSION:
        req = ", ".join(g["requires"]) if g["requires"] else "—"
        print(
            f"  [{g['level']}] {g['id']:<35}  "
            f"{g['structure']:<18}  requires: {req}"
        )


def step_load_vocab(theme: str = "food") -> dict:
    _hr(f"Loading vocab: {theme}")
    path = VOCAB_DIR / f"{theme}.json"
    with open(path, encoding="utf-8") as f:
        vocab = json.load(f)
    print(f"  Nouns: {len(vocab['nouns'])}")
    print(f"  Verbs: {len(vocab['verbs'])}")
    return vocab


def step_load_or_create_curriculum() -> dict:
    _hr("Curriculum")
    if CURRICULUM_PATH.exists():
        cur = load_curriculum(CURRICULUM_PATH)
        print(f"  Loaded from {CURRICULUM_PATH}")
    else:
        cur = create_curriculum("Japanese Beginner")
        print("  Created fresh curriculum")
    print(summary(cur))
    return cur


def step_show_unlocked(cur: dict) -> list[dict]:
    _hr("Unlocked Grammar Steps")
    unlocked = get_next_grammar(cur["covered_grammar_ids"])
    if not unlocked:
        print("  No unlocked steps — curriculum is complete!")
        return []
    for g in unlocked:
        print(
            f"  [{g['level']}] {g['id']}\n"
            f"         {g['structure']} — {g['description']}\n"
            f"         e.g. {g['example_en']} → {g['example_jp']}"
        )
    return unlocked


def step_grammar_select(
    cur: dict, unlocked: list[dict], nouns: list[dict], verbs: list[dict]
) -> list[str]:
    _hr("Step 1 — Grammar Selection (LLM picks what to teach)")
    lesson_number = len(cur["lessons"]) + 1
    prompt = build_grammar_select_prompt(
        unlocked_grammar=unlocked,
        available_nouns=nouns,
        available_verbs=verbs,
        lesson_number=lesson_number,
        covered_grammar_ids=cur["covered_grammar_ids"],
    )
    print(f"  Prompt length: {len(prompt)} chars")
    t0 = time.perf_counter()
    result = ask_llm_json_free(prompt)
    elapsed = time.perf_counter() - t0

    selected = result.get("selected_ids", [])
    rationale = result.get("rationale", "—")
    print(f"  Selected:  {selected}  ({elapsed:.1f}s)")
    print(f"  Rationale: {rationale}")
    return selected


def step_grammar_generate(
    selected_ids: list[str],
    unlocked: list[dict],
    nouns: list[dict],
    verbs: list[dict],
) -> list[dict]:
    _hr("Step 2 — Grammar Generation (LLM writes example sentences)")
    id_set = set(selected_ids)
    grammar_specs = [g for g in unlocked if g["id"] in id_set]
    if not grammar_specs:
        print("  No matching grammar specs found — skipping")
        return []

    prompt = build_grammar_generate_prompt(
        grammar_specs=grammar_specs,
        nouns=nouns,
        verbs=verbs,
        sentences_per_grammar=3,
    )
    print(f"  Prompt length: {len(prompt)} chars")
    t0 = time.perf_counter()
    result = ask_llm_json_free(prompt)
    elapsed = time.perf_counter() - t0

    sentences = result.get("sentences", [])
    print(f"  Generated {len(sentences)} sentences  ({elapsed:.1f}s)")
    for s in sentences:
        print(
            f"    [{s.get('grammar_id','?')}] {s.get('english','')}\n"
            f"      JP: {s.get('japanese','')}\n"
            f"      RM: {s.get('romaji','')}"
        )
    return sentences


def step_validate(sentences: list[dict]) -> dict:
    _hr("Step 3 — Content Validation (LLM cross-checks accuracy)")
    if not sentences:
        print("  No sentences to validate")
        return {}

    prompt = build_content_validate_prompt(sentences)
    print(f"  Prompt length: {len(prompt)} chars")
    t0 = time.perf_counter()
    result = ask_llm_json_free(prompt)
    elapsed = time.perf_counter() - t0

    score = result.get("score", "?")
    corrections = result.get("corrections", [])
    summary_text = result.get("summary", "—")
    print(f"  Score:   {score}/10  ({elapsed:.1f}s)")
    print(f"  Summary: {summary_text}")
    if corrections:
        print(f"  Corrections ({len(corrections)}):")
        for c in corrections:
            print(
                f"    [{c.get('severity','?')}] index {c.get('index','?')}: "
                f"{c.get('explanation','')}"
            )
            print(f"      Was: {c.get('original_japanese','')}")
            print(f"      Fix: {c.get('corrected_japanese','')}")
    else:
        print("  No corrections needed ✅")
    return result


def step_noun_practice(nouns: list[dict], lesson_number: int) -> None:
    _hr("Bonus — Noun Practice Content (LLM enriches introductions)")
    prompt = build_noun_practice_prompt(nouns[:3], lesson_number=lesson_number)
    print(f"  Prompt length: {len(prompt)} chars")
    t0 = time.perf_counter()
    result = ask_llm_json_free(prompt)
    elapsed = time.perf_counter() - t0

    items = result.get("noun_items", [])
    print(f"  Got {len(items)} noun items  ({elapsed:.1f}s)")
    for item in items:
        word = item.get("english", "?")
        jp = item.get("kanji", item.get("japanese", "?"))
        tip = item.get("memory_tip", "—")
        ex = item.get("example_sentence_jp", "—")
        print(f"    {word} / {jp}  tip: {tip}")
        print(f"      Example: {ex}")


def step_add_lesson(
    cur: dict,
    vocab: dict,
    nouns: list[dict],
    verbs: list[dict],
    selected_ids: list[str],
    sentences: list[dict],
) -> None:
    _hr("Adding Lesson to Curriculum")
    lesson_number = len(cur["lessons"]) + 1
    lesson = add_lesson(
        cur,
        title=f"{vocab['theme'].title()} — Lesson {lesson_number}",
        theme=vocab["theme"],
        nouns=nouns,
        verbs=verbs,
        grammar_ids=selected_ids,
        items_count=len(sentences),
        status="draft",
    )
    print(f"  Added lesson #{lesson['id']}: {lesson['title']}")

    # Mark complete so covered trackers update
    complete_lesson(cur, lesson["id"])
    print("  Marked as completed — covered trackers updated")

    save_curriculum(cur, CURRICULUM_PATH)
    print(f"  Saved to {CURRICULUM_PATH}")
    print()
    print(summary(cur))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Spike 08 — Curriculum-Driven LLM Lesson Planning")
    print(f"LM Studio: ", end="")
    if not _check_lm_studio():
        print("❌ not reachable at http://localhost:1234 — aborting")
        sys.exit(1)
    print("✅ connected")

    results: dict = {}

    # ── Show grammar table (no LLM) ──────────────────────────────────────────
    step_show_grammar_table()

    # ── Load data ────────────────────────────────────────────────────────────
    vocab = step_load_vocab("food")
    cur = step_load_or_create_curriculum()
    lesson_number = len(cur["lessons"]) + 1

    # ── Select vocab for this lesson ─────────────────────────────────────────
    nouns, verbs = suggest_new_vocab(
        all_nouns=vocab["nouns"],
        all_verbs=vocab["verbs"],
        covered_nouns=cur["covered_nouns"],
        covered_verbs=cur["covered_verbs"],
        num_nouns=4,
        num_verbs=3,
    )
    _hr("Vocab Selected for This Lesson")
    print(f"  Nouns: {[n['english'] for n in nouns]}")
    print(f"  Verbs: {[v['english'] for v in verbs]}")

    # ── Unlocked grammar ─────────────────────────────────────────────────────
    unlocked = step_show_unlocked(cur)
    if not unlocked:
        print("Nothing to do — all grammar steps are covered.")
        sys.exit(0)

    # ── LLM steps ────────────────────────────────────────────────────────────
    selected_ids = step_grammar_select(cur, unlocked, nouns, verbs)
    results["grammar_select"] = {"selected_ids": selected_ids}

    sentences = step_grammar_generate(selected_ids, unlocked, nouns, verbs)
    results["grammar_generate"] = {"sentences": sentences}

    validation = step_validate(sentences)
    results["validation"] = validation

    step_noun_practice(nouns, lesson_number)

    # ── Save lesson ───────────────────────────────────────────────────────────
    if selected_ids:
        step_add_lesson(cur, vocab, nouns, verbs, selected_ids, sentences)

    # ── Save full spike results ───────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nResults saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
