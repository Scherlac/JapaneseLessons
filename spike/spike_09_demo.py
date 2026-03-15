#!/usr/bin/env python3
"""
spike_09_demo.py -- Two-lesson curriculum demo with rendered videos (LLM-driven).

Generates two progressive lessons using the curriculum + LLM pipeline:

  Lesson 1 (food)   -- Level-1 grammar (action_present_aff + identity_present_aff)
  Lesson 2 (travel) -- Level-2 grammar (unlocked after completing Lesson 1)

Each lesson is rendered as an MP4 with TTS-narrated visual flash cards.

Output:
  output/demo/lesson_01_food.mp4
  output/demo/lesson_02_travel.mp4
  output/demo/curriculum_demo.json

Requirements:
  - LM Studio on localhost:1234 with qwen/qwen3-14b loaded
  - edge-tts:  pip install edge-tts
  - ffmpeg:    conda install -c conda-forge ffmpeg
  - Pillow + moviepy (already installed)

Run:
  python spike/spike_09_demo.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from jlesson.curriculum import (
    add_lesson,
    complete_lesson,
    create_curriculum,
    get_grammar_by_id,
    get_next_grammar,
    save_curriculum,
    suggest_new_vocab,
)
from jlesson.llm_client import ask_llm_json_free
from jlesson.prompt_template import (
    build_grammar_generate_prompt,
    build_grammar_select_prompt,
    build_noun_practice_prompt,
)
from jlesson.vocab_generator import generate_vocab

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CURRICULUM_PATH = ROOT / "output" / "demo" / "curriculum_demo.json"
LESSON_THEMES   = ["food", "travel"]

NUM_NOUNS            = 3   # keep demo short (~2 min video per lesson)
NUM_VERBS            = 2
SENTENCES_PER_GRAMMAR = 3
PERSONS: list[tuple[str, str, str]] = [
    ("I",     "私",   "watashi"),
    ("you",   "あなた", "anata"),
    ("she",   "彼女",  "kanojo"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_vocab(theme: str) -> dict:
    """Load vocab for theme, generating it via LLM if the file doesn't exist."""
    path = ROOT / "vocab" / f"{theme}.json"
    if not path.exists():
        print(f"  [vocab] {theme}.json not found — generating via LLM...")
        return generate_vocab(
            theme=theme,
            num_nouns=NUM_NOUNS * 3,   # generate more than we need
            num_verbs=NUM_VERBS * 3,
            output_dir=ROOT / "vocab",
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def _build_video_items(noun_items: list, sentences: list) -> list:
    """Convert LLM output dicts into video-pipeline item dicts."""
    items = []
    total = len(noun_items) + len(sentences)

    for i, noun in enumerate(noun_items, 1):
        jp     = noun.get("japanese", "")
        romaji = noun.get("romaji", "")
        reveal = f"{jp}  ({romaji})" if romaji else jp
        items.append({
            "phase":     "Nouns",
            "step":      "INTRODUCE",
            "counter":   f"{i}/{total}",
            "prompt":    noun.get("english", ""),
            "reveal":    reveal,
            "tts_text":  jp,
            "tts_voice": "ja-JP-NanamiNeural",
        })

    offset = len(noun_items)
    for i, sent in enumerate(sentences, 1):
        items.append({
            "phase":     "Grammar",
            "step":      "TRANSLATE",
            "counter":   f"{offset + i}/{total}",
            "prompt":    sent.get("english", ""),
            "reveal":    sent.get("japanese", ""),
            "tts_text":  sent.get("japanese", ""),
            "tts_voice": "ja-JP-NanamiNeural",
        })

    return items


# ---------------------------------------------------------------------------
# Video pipeline
# ---------------------------------------------------------------------------

async def _render_video_async(
    items: list,
    video_path: Path,
    cards_dir: Path,
    audio_dir: Path,
) -> None:
    from tts_engine import create_engine
    from video_cards import CardRenderer
    from video_builder import VideoBuilder

    cards_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    card_renderer = CardRenderer()
    video_builder = VideoBuilder()
    total = len(items)

    # TTS audio
    print(f"  TTS audio ({total} items)...")
    audio_paths = []
    for i, item in enumerate(items):
        voice_key = "japanese_female"
        tts_voice = item.get("tts_voice", "")
        if "Aria"  in tts_voice: voice_key = "english_female"
        if "Keita" in tts_voice: voice_key = "japanese_male"

        engine     = create_engine(voice_key, rate="-20%")
        audio_path = audio_dir / f"audio_{i+1:03d}.mp3"

        for attempt in range(3):
            try:
                await engine.generate_audio(item["tts_text"], audio_path)
                break
            except Exception as exc:
                if attempt < 2:
                    print(f"    TTS retry {attempt+1}: {exc}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

        audio_paths.append(audio_path)
        await asyncio.sleep(1.0)   # rate-limit Edge TTS

    # Cards
    print(f"  Rendering cards ({total} items)...")
    for i, item in enumerate(items):
        progress = (i + 1) / total
        if item["step"] == "INTRODUCE":
            card = card_renderer.render_introduce_card(
                english=item["prompt"], japanese=item["reveal"],
                kana="", romaji="",
                step_label=item["counter"], progress=progress,
            )
        else:
            card = card_renderer.render_translate_card(
                english=item["prompt"], japanese=item["reveal"],
                romaji="", context=item["phase"].lower(),
                step_label=item["counter"], progress=progress,
            )
        card_renderer.save_card(card, cards_dir / f"{i+1:03d}.png")

    # Assemble video
    print(f"  Building video -> {video_path.name}...")
    clips = [
        video_builder.create_clip(cards_dir / f"{i+1:03d}.png", audio_paths[i])
        for i in range(total)
    ]
    video_builder.build_video(clips, video_path, method="ffmpeg")
    size_kb = video_path.stat().st_size // 1024
    print(f"  OK  {video_path}  ({size_kb} KB)")


def _render_video(items: list, video_path: Path, cards_dir: Path, audio_dir: Path) -> None:
    asyncio.run(_render_video_async(items, video_path, cards_dir, audio_dir))


# ---------------------------------------------------------------------------
# Lesson runner
# ---------------------------------------------------------------------------

def run_lesson(
    curriculum: dict,
    theme: str,
    lesson_number: int,
    output_dir: Path,
) -> None:
    _header(f"LESSON {lesson_number}: {theme.upper()}")

    vocab     = _load_vocab(theme)
    all_nouns = vocab["nouns"]
    all_verbs = vocab["verbs"]

    # Fresh vocab suggestion
    nouns, verbs = suggest_new_vocab(
        all_nouns, all_verbs,
        covered_nouns=curriculum["covered_nouns"],
        covered_verbs=curriculum["covered_verbs"],
        num_nouns=NUM_NOUNS,
        num_verbs=NUM_VERBS,
    )
    print(f"\n  Vocab nouns : {[n['english'] for n in nouns]}")
    print(f"  Vocab verbs : {[v['english'] for v in verbs]}")

    # Grammar select via LLM
    unlocked = get_next_grammar(curriculum["covered_grammar_ids"])
    print(f"\n  Unlocked grammar ({len(unlocked)}): {[g['id'] for g in unlocked]}")

    print("\n  [LLM] Grammar select...")
    t0 = time.time()
    sel_result   = ask_llm_json_free(build_grammar_select_prompt(
        unlocked, nouns, verbs, lesson_number,
        covered_grammar_ids=curriculum["covered_grammar_ids"],
    ))
    selected_ids = sel_result.get("selected_ids") or [g["id"] for g in unlocked[:2]]
    print(f"  Selected : {selected_ids}  ({time.time()-t0:.1f}s)")
    print(f"  Rationale: {str(sel_result.get('rationale', ''))[:120]}")

    # Grammar generate via LLM
    grammar_specs = []
    for gid in selected_ids:
        try:
            grammar_specs.append(get_grammar_by_id(gid))
        except KeyError:
            print(f"  Warning: unknown grammar id {gid!r}, skipping")

    print("\n  [LLM] Generate sentences...")
    t0 = time.time()
    gen_result = ask_llm_json_free(build_grammar_generate_prompt(
        grammar_specs, nouns, verbs, PERSONS, SENTENCES_PER_GRAMMAR
    ))
    sentences = gen_result.get("sentences", [])
    print(f"  Generated: {len(sentences)} sentences  ({time.time()-t0:.1f}s)")

    # Noun practice via LLM
    print("\n  [LLM] Noun practice...")
    t0 = time.time()
    noun_result = ask_llm_json_free(build_noun_practice_prompt(nouns, lesson_number))
    noun_items  = noun_result.get("noun_items", [])
    # Ensure required fields present even if LLM omits them
    for n_item, n_src in zip(noun_items, nouns):
        n_item.setdefault("english",  n_src["english"])
        n_item.setdefault("japanese", n_src["japanese"])
        n_item.setdefault("romaji",   n_src["romaji"])
    if not noun_items:
        noun_items = [
            {"english": n["english"], "japanese": n["japanese"], "romaji": n["romaji"]}
            for n in nouns
        ]
    print(f"  Got: {len(noun_items)} noun items  ({time.time()-t0:.1f}s)")

    # Register lesson
    lesson = add_lesson(
        curriculum,
        title=f"Lesson {lesson_number}: {theme.title()}",
        theme=theme,
        nouns=nouns,
        verbs=verbs,
        grammar_ids=selected_ids,
        items_count=len(noun_items) + len(sentences),
    )
    complete_lesson(curriculum, lesson["id"])

    # Render video
    items      = _build_video_items(noun_items, sentences)
    lesson_dir = output_dir / f"lesson_{lesson_number:02d}"
    video_path = output_dir / f"lesson_{lesson_number:02d}_{theme}.mp4"
    print(f"\n  Rendering video ({len(items)} cards)...")
    _render_video(items, video_path, lesson_dir / "cards", lesson_dir / "audio")

    save_curriculum(curriculum, CURRICULUM_PATH)
    print(f"  Curriculum saved -> {CURRICULUM_PATH}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _header("CURRICULUM DEMO -- 2 Lessons with Rendered Videos")
    print(f"  Themes  : {LESSON_THEMES}")
    print(f"  Nouns   : {NUM_NOUNS} per lesson  |  Verbs: {NUM_VERBS}")
    print(f"  Grammar : {SENTENCES_PER_GRAMMAR} sentences per grammar point")

    output_dir = ROOT / "output" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    curriculum = create_curriculum("Demo Curriculum")
    save_curriculum(curriculum, CURRICULUM_PATH)
    print(f"\n  Fresh curriculum -> {CURRICULUM_PATH}")

    t_total = time.time()
    for i, theme in enumerate(LESSON_THEMES, 1):
        run_lesson(curriculum, theme, lesson_number=i, output_dir=output_dir)

    _header("DEMO COMPLETE")
    elapsed = time.time() - t_total
    print(f"\n  Lessons : {len(curriculum['lessons'])}")
    print(f"  Grammar : {curriculum['covered_grammar_ids']}")
    print(f"  Elapsed : {elapsed:.0f}s")
    print(f"\n  Videos:")
    for i, theme in enumerate(LESSON_THEMES, 1):
        p = output_dir / f"lesson_{i:02d}_{theme}.mp4"
        tag = f"{p.stat().st_size // 1024} KB" if p.exists() else "NOT FOUND"
        print(f"    {p.relative_to(ROOT)}  ({tag})")


if __name__ == "__main__":
    main()
