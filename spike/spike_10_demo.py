#!/usr/bin/env python3
"""
spike_10_demo.py — jlesson feature showcase (v2)

Demonstrates the full current feature set in five focused sections:

  Section 1  Seeded vocab shuffle    — reproducibility + global-state isolation
  Section 2  LLM response cache      — sha256 file cache; cold vs warm timing
  Section 3  Two-lesson curriculum   — run_pipeline() × 2 with grammar progression
  Section 4  Content inspection      — load persisted content.json, pretty-print
  Section 5  Curriculum summary      — grammar progression + coverage report

Requirements:
  - LM Studio on localhost:1234 with qwen/qwen3-14b loaded  (for --no-cache runs)
  - edge-tts, moviepy, ffmpeg                                (for --video runs)

Usage:
  python spike/spike_10_demo.py                 # cache on,  no video  (fast)
  python spike/spike_10_demo.py --no-cache      # live LLM, no video
  python spike/spike_10_demo.py --video         # cache on,  with video
  python spike/spike_10_demo.py --no-cache --video
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from jlesson.curriculum import (
    create_curriculum,
    save_curriculum,
    suggest_new_vocab,
    summary as curriculum_summary,
)
from jlesson.lesson_pipeline import LessonConfig, run_pipeline
from jlesson.lesson_store import load_lesson_content
from jlesson.llm_cache import ask_llm_cached, cache_size, clear_cache
from jlesson.prompt_template import build_grammar_select_prompt

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

DEMO_DIR        = ROOT / "output" / "demo_v2"
CURRICULUM_PATH = DEMO_DIR / "curriculum.json"

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _banner(title: str) -> None:
    bar = "=" * 64
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


def _section(n: int, title: str) -> None:
    print(f"\n{'─' * 64}")
    print(f"  Section {n}: {title}")
    print(f"{'─' * 64}")


def _ok(msg: str)   -> None: print(f"  ✓  {msg}")
def _info(msg: str) -> None: print(f"     {msg}")
def _kv(k: str, v)  -> None: print(f"     {k:<22} {v}")


# ---------------------------------------------------------------------------
# Section 1 — Seeded vocab shuffle
# ---------------------------------------------------------------------------

def demo_seeded_shuffle() -> None:
    _section(1, "Seeded vocab shuffle")

    food_path = ROOT / "vocab" / "food.json"
    if not food_path.exists():
        print("  [skip] vocab/food.json not found")
        return

    import json
    with open(food_path, encoding="utf-8") as f:
        vocab = json.load(f)

    nouns = vocab["nouns"]
    verbs = vocab["verbs"]

    # Same seed → same result
    n_a, v_a = suggest_new_vocab(nouns, verbs, covered_nouns=[], covered_verbs=[],
                                  num_nouns=4, num_verbs=3, seed=42)
    n_b, v_b = suggest_new_vocab(nouns, verbs, covered_nouns=[], covered_verbs=[],
                                  num_nouns=4, num_verbs=3, seed=42)
    same = [x["english"] for x in n_a] == [x["english"] for x in n_b]
    _ok(f"seed=42 is reproducible: {same}")
    _kv("nouns (seed=42)", [n["english"] for n in n_a])
    _kv("verbs (seed=42)", [v["english"] for v in v_a])

    # Different seeds → different order
    n_c, _ = suggest_new_vocab(nouns, verbs, covered_nouns=[], covered_verbs=[],
                                num_nouns=4, num_verbs=3, seed=99)
    different = [x["english"] for x in n_a] != [x["english"] for x in n_c]
    _ok(f"seed=99 gives different order: {different}")
    _kv("nouns (seed=99)", [n["english"] for n in n_c])

    # seed=None → original list order preserved
    n_d, _ = suggest_new_vocab(nouns, verbs, covered_nouns=[], covered_verbs=[],
                                num_nouns=4, num_verbs=3)
    _ok(f"seed=None preserves list order: {[n['english'] for n in n_d]}")

    # Local RNG: global state is untouched
    import random
    random.seed(7)
    ref = random.random()
    random.seed(7)
    suggest_new_vocab(nouns, verbs, covered_nouns=[], covered_verbs=[],
                      num_nouns=4, num_verbs=3, seed=42)
    after = random.random()
    _ok(f"global random state unaffected: {ref == after}")


# ---------------------------------------------------------------------------
# Section 2 — LLM response cache
# ---------------------------------------------------------------------------

def demo_cache(use_cache: bool) -> None:
    _section(2, "LLM response cache")

    cache_dir = DEMO_DIR / ".cache"

    if use_cache:
        # Build a small but real prompt so the cache key is meaningful
        import json
        food_path = ROOT / "vocab" / "food.json"
        if food_path.exists():
            with open(food_path, encoding="utf-8") as f:
                vocab = json.load(f)
            sample_nouns = vocab["nouns"][:3]
            sample_verbs = vocab["verbs"][:2]
        else:
            sample_nouns = [{"english": "water", "japanese": "水", "romaji": "mizu"}]
            sample_verbs = [{"english": "to eat", "japanese": "食べる", "romaji": "taberu",
                             "masu_form": "食べます", "type": "る-verb"}]

        from jlesson.curriculum import get_next_grammar
        prompt = build_grammar_select_prompt(
            get_next_grammar([]), sample_nouns, sample_verbs, lesson_number=1,
            covered_grammar_ids=[],
        )

        # --- Cold miss ---
        clear_cache(cache_dir=cache_dir)
        _info(f"cache dir : {cache_dir.relative_to(ROOT)}")
        _info(f"entries before: {cache_size(cache_dir=cache_dir)}")

        t0 = time.perf_counter()
        ask_llm_cached(prompt, cache_dir=cache_dir)
        cold_ms = (time.perf_counter() - t0) * 1000
        _ok(f"cold miss  — LLM call   : {cold_ms:>7.0f} ms  (entries now: {cache_size(cache_dir=cache_dir)})")

        # --- Warm hit ---
        t0 = time.perf_counter()
        ask_llm_cached(prompt, cache_dir=cache_dir)
        warm_ms = (time.perf_counter() - t0) * 1000
        _ok(f"warm hit   — disk read  : {warm_ms:>7.1f} ms  ({cold_ms / max(warm_ms, 0.01):.0f}× faster)")

        _kv("cache key", "sha256(prompt_text).hexdigest()[:16] + …")
        _info("LLM_CACHE_DIR env var overrides default output/.cache/")
    else:
        _info("(cache demo skipped — running with --no-cache)")
        _info("Pass without --no-cache to see cold/warm timing comparison.")


# ---------------------------------------------------------------------------
# Section 3 — Two-lesson curriculum via run_pipeline()
# ---------------------------------------------------------------------------

def demo_pipeline(use_cache: bool, render_video: bool, theme1: str = "food", theme2: str = "travel") -> tuple[int, int]:
    """Run two lessons and return (lesson_id_1, lesson_id_2)."""
    _section(3, "Two-lesson curriculum via run_pipeline()")

    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    # Fresh curriculum for each demo run
    cur = create_curriculum("Demo v2")
    save_curriculum(cur, CURRICULUM_PATH)

    lesson_ids = []
    themes = [theme1, theme2]

    for i, theme in enumerate(themes, 1):
        print(f"\n  ── Lesson {i}: {theme.upper()} ──")

        t0 = time.perf_counter()
        ctx = run_pipeline(LessonConfig(
            theme=theme,
            curriculum_path=CURRICULUM_PATH,
            output_dir=DEMO_DIR,
            num_nouns=3,
            num_verbs=2,
            sentences_per_grammar=2,
            seed=42,
            use_cache=use_cache,
            render_video=render_video,
        ))
        elapsed = time.perf_counter() - t0

        lesson_ids.append(ctx.lesson_id)
        _ok(f"lesson #{ctx.lesson_id} complete  ({elapsed:.1f}s)")
        _kv("nouns", [n["english"] for n in ctx.nouns])
        _kv("verbs", [v["english"] for v in ctx.verbs])
        _kv("grammar", [g["id"] for g in ctx.selected_grammar])
        _kv("sentences", len(ctx.sentences))
        _kv("content saved", str(ctx.content_path.relative_to(ROOT)))
        if ctx.video_path:
            size_kb = ctx.video_path.stat().st_size // 1024
            _kv("video", f"{ctx.video_path.name}  ({size_kb} KB)")

    return tuple(lesson_ids)


# ---------------------------------------------------------------------------
# Section 4 — Content inspection
# ---------------------------------------------------------------------------

def demo_content_inspection(lesson_id: int) -> None:
    _section(4, "Content inspection (lesson_store)")

    try:
        content = load_lesson_content(lesson_id, output_dir=DEMO_DIR)
    except FileNotFoundError as exc:
        print(f"  [skip] {exc}")
        return

    _ok(f"loaded content.json for lesson #{content.lesson_id}")
    _kv("theme", content.theme)
    _kv("grammar_ids", content.grammar_ids)
    _kv("noun_items", len(content.noun_items))
    _kv("verb_items", len(content.verb_items))
    _kv("sentences", len(content.sentences))
    _kv("created_at", content.created_at)

    print("\n  Sample nouns:")
    for item in content.noun_items[:2]:
        tip = item.memory_tip or "—"
        print(f"    {item.english:<14} → {item.japanese}  ({item.romaji})")
        print(f"    {'':14}   tip: {tip[:60]}")

    print("\n  Sample sentences:")
    for sent in content.sentences[:3]:
        print(f"    EN: {sent.english}")
        print(f"    JP: {sent.japanese}")
        print()


# ---------------------------------------------------------------------------
# Section 5 — Curriculum summary
# ---------------------------------------------------------------------------

def demo_curriculum_summary() -> None:
    _section(5, "Curriculum summary")

    from jlesson.curriculum import load_curriculum
    try:
        cur = load_curriculum(CURRICULUM_PATH)
    except FileNotFoundError:
        print("  [skip] no curriculum file — run section 3 first")
        return

    print()
    print(curriculum_summary(cur))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="jlesson feature showcase")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable LLM cache (always call LLM live).")
    parser.add_argument("--video", action="store_true",
                        help="Enable video rendering (requires edge-tts + ffmpeg).")
    parser.add_argument("--section", type=int, default=0,
                        help="Run a single section only (1-5).")
    parser.add_argument("--theme1", default="food",
                        help="Theme for lesson 1 (default: food).")
    parser.add_argument("--theme2", default="travel",
                        help="Theme for lesson 2 (default: travel).")
    args = parser.parse_args()

    use_cache    = not args.no_cache
    render_video = args.video
    only         = args.section

    _banner("jlesson — feature showcase  (spike_10_demo.py)")
    _kv("cache",        "on (file-based sha256)" if use_cache else "off (live LLM)")
    _kv("video render", "on" if render_video else "off  (--video to enable)")
    _kv("output dir",   str(DEMO_DIR.relative_to(ROOT)))

    if only in (0, 1):
        demo_seeded_shuffle()

    if only in (0, 2):
        demo_cache(use_cache)

    lesson_id_1, lesson_id_2 = 1, 2
    if only in (0, 3):
        ids = demo_pipeline(use_cache, render_video, args.theme1, args.theme2)
        if ids:
            lesson_id_1, lesson_id_2 = ids

    if only in (0, 4):
        demo_content_inspection(lesson_id_1)

    if only in (0, 5):
        demo_curriculum_summary()

    _banner("Demo complete")


if __name__ == "__main__":
    main()
