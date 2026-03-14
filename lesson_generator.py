"""
Deterministic lesson generator.

Produces structured lesson items from vocabulary data and configuration.
No LLM required — items are built using vocabulary and conjugation rules.

Each item is a dict ready for the video pipeline (TTS + card rendering).

Usage:
    from lesson_generator import generate_lesson_items, render_lesson_markdown
    items = generate_lesson_items(nouns, verbs)
"""

from __future__ import annotations

import random
from typing import Optional

from llm_client import ask_llm_json


# ── Polite-form conjugation (Japanese) ───────────────────────────────────


def conjugate_polite(masu_form: str, tense: str, polarity: str) -> str:
    """
    Conjugate a polite Japanese verb/adjective form.

    Args:
        masu_form: Base polite form, e.g. "飲みます" or "好きです"
        tense: "present" or "past"
        polarity: "affirmative" or "negative"

    Returns:
        Conjugated form, e.g. "飲みません" for present/negative.
    """
    if masu_form.endswith("です"):
        stem = masu_form[:-2]
        forms = {
            ("present", "affirmative"): f"{stem}です",
            ("present", "negative"): f"{stem}ではありません",
            ("past", "affirmative"): f"{stem}でした",
            ("past", "negative"): f"{stem}ではありませんでした",
        }
    else:
        stem = masu_form[:-2]  # strip ます
        forms = {
            ("present", "affirmative"): f"{stem}ます",
            ("present", "negative"): f"{stem}ません",
            ("past", "affirmative"): f"{stem}ました",
            ("past", "negative"): f"{stem}ませんでした",
        }
    return forms.get((tense, polarity), masu_form)


# ── Romaji conjugation ───────────────────────────────────────────────────

_U_VERB_MASU_MAP: dict[str, str] = {
    "u": "imasu",
    "ku": "kimasu",
    "gu": "gimasu",
    "su": "shimasu",
    "tsu": "chimasu",
    "nu": "nimasu",
    "bu": "bimasu",
    "mu": "mimasu",
    "ru": "rimasu",
}


def _to_masu_romaji(romaji: str, verb_type: str) -> str:
    """Convert dictionary-form romaji to masu-form romaji."""
    if verb_type == "る-verb":
        return romaji[:-2] + "masu"
    if verb_type == "う-verb":
        for ending in sorted(_U_VERB_MASU_MAP, key=len, reverse=True):
            if romaji.endswith(ending):
                return romaji[: -len(ending)] + _U_VERB_MASU_MAP[ending]
        return romaji + "masu"
    if verb_type == "irregular":
        if romaji.endswith("suru"):
            return romaji[:-4] + "shimasu"
        if romaji.endswith("kuru"):
            return romaji[:-4] + "kimasu"
        return romaji + "masu"
    if verb_type == "な-adj":
        return romaji + " desu"
    return romaji


def conjugate_romaji(romaji: str, verb_type: str, tense: str, polarity: str) -> str:
    """Get romaji for a conjugated polite form."""
    base = _to_masu_romaji(romaji, verb_type)

    if verb_type == "な-adj":
        stem = base.replace(" desu", "")
        forms = {
            ("present", "affirmative"): f"{stem} desu",
            ("present", "negative"): f"{stem} dewa arimasen",
            ("past", "affirmative"): f"{stem} deshita",
            ("past", "negative"): f"{stem} dewa arimasen deshita",
        }
    else:
        stem = base.replace("masu", "")
        forms = {
            ("present", "affirmative"): f"{stem}masu",
            ("present", "negative"): f"{stem}masen",
            ("past", "affirmative"): f"{stem}mashita",
            ("past", "negative"): f"{stem}masen deshita",
        }
    return forms.get((tense, polarity), base)


# ── English conjugation ──────────────────────────────────────────────────

_IRREGULAR_PAST: dict[str, str] = {
    "eat": "ate",
    "drink": "drank",
    "buy": "bought",
    "make": "made",
    "cut": "cut",
    "give": "gave",
    "go": "went",
    "come": "came",
    "do": "did",
    "have": "had",
    "see": "saw",
    "take": "took",
    "get": "got",
    "write": "wrote",
    "read": "read",
    "speak": "spoke",
    "think": "thought",
    "know": "knew",
    "run": "ran",
    "bring": "brought",
    "catch": "caught",
    "find": "found",
    "hear": "heard",
    "hold": "held",
    "keep": "kept",
    "leave": "left",
    "lose": "lost",
    "meet": "met",
    "pay": "paid",
    "put": "put",
    "say": "said",
    "sell": "sold",
    "send": "sent",
    "sit": "sat",
    "sleep": "slept",
    "stand": "stood",
    "teach": "taught",
    "tell": "told",
    "understand": "understood",
    "wear": "wore",
}


def _strip_to(verb_english: str) -> str:
    """Strip 'to ' prefix from English verb."""
    return verb_english[3:] if verb_english.startswith("to ") else verb_english


def _past_tense(verb: str) -> str:
    """Simple English past tense."""
    if verb in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[verb]
    if verb.endswith("e"):
        return verb + "d"
    if verb.endswith("y") and len(verb) >= 2 and verb[-2] not in "aeiou":
        return verb[:-1] + "ied"
    return verb + "ed"


def _third_person_s(verb: str) -> str:
    """Add third-person singular -s/-es."""
    if verb in ("go", "do"):
        return verb + "es"
    if verb.endswith(("sh", "ch", "x", "s", "z", "o")):
        return verb + "es"
    if verb.endswith("y") and len(verb) >= 2 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    return verb + "s"


def conjugate_english(verb_english: str, person: str, tense: str, polarity: str) -> str:
    """Conjugate an English verb for person/tense/polarity."""
    verb = _strip_to(verb_english)

    if tense == "present":
        if polarity == "affirmative":
            return _third_person_s(verb) if person == "He/She" else verb
        else:
            aux = "doesn't" if person == "He/She" else "don't"
            return f"{aux} {verb}"
    else:  # past
        if polarity == "affirmative":
            return _past_tense(verb)
        else:
            return f"didn't {verb}"


# ── Persons ──────────────────────────────────────────────────────────────

PERSONS: list[tuple[str, str, str]] = [
    ("I", "私", "watashi"),
    ("You", "あなた", "anata"),
    ("He/She", "彼", "kare"),
]


# ── Item builders ────────────────────────────────────────────────────────


def _noun_cycle(noun: dict, start_index: int, total: int) -> list[dict]:
    """Generate 5 repetition touches for one noun."""
    en = noun["english"]
    kj = noun["kanji"]
    jp = noun["japanese"]
    rm = noun["romaji"]
    ann = f"{jp} · {rm}"

    steps = [
        ("INTRODUCE", en, kj, ann, jp, "ja-JP-NanamiNeural"),
        ("RECALL", kj, en, ann, en, "en-US-AriaNeural"),
        ("REINFORCE", en, kj, ann, jp, "ja-JP-NanamiNeural"),
        ("SELF-CHECK", jp, kj, rm, jp, "ja-JP-NanamiNeural"),
        ("LOCK-IN", en, kj, ann, jp, "ja-JP-NanamiNeural"),
    ]

    items = []
    idx = start_index
    for step, prompt, reveal, annotation, tts_text, tts_voice in steps:
        idx += 1
        items.append({
            "phase": "nouns",
            "step": step,
            "index": idx,
            "total": total,
            "counter": f"{idx}/{total}",
            "prompt": prompt,
            "reveal": reveal,
            "annotation": annotation,
            "tts_text": tts_text,
            "tts_voice": tts_voice,
        })
    return items


def _verb_cycle(verb: dict, start_index: int, total: int) -> list[dict]:
    """Generate 5 repetition touches for one verb."""
    en = verb["english"]
    masu = verb["masu_form"]
    jp = verb["japanese"]
    rm = verb["romaji"]
    ann = f"{jp} · {rm}"

    steps = [
        ("INTRODUCE", en, masu, ann, masu, "ja-JP-NanamiNeural"),
        ("RECALL", masu, en, ann, en, "en-US-AriaNeural"),
        ("REINFORCE", en, masu, ann, masu, "ja-JP-NanamiNeural"),
        ("SELF-CHECK", jp, masu, rm, masu, "ja-JP-NanamiNeural"),
        ("LOCK-IN", en, masu, ann, masu, "ja-JP-NanamiNeural"),
    ]

    items = []
    idx = start_index
    for step, prompt, reveal, annotation, tts_text, tts_voice in steps:
        idx += 1
        items.append({
            "phase": "verbs",
            "step": step,
            "index": idx,
            "total": total,
            "counter": f"{idx}/{total}",
            "prompt": prompt,
            "reveal": reveal,
            "annotation": annotation,
            "tts_text": tts_text,
            "tts_voice": tts_voice,
        })
    return items


def _grammar_cycle(
    verb: dict,
    noun: dict,
    person_en: str,
    person_jp: str,
    person_rm: str,
    tense: str,
    polarity: str,
    start_index: int,
    total: int,
) -> list[dict]:
    """Generate 3 repetition touches for one grammar sentence."""
    # Japanese sentence
    particle = "が" if verb["type"] == "な-adj" else "を"
    conj_jp = conjugate_polite(verb["masu_form"], tense, polarity)
    jp_sentence = f"{person_jp}は{noun['kanji']}{particle}{conj_jp}。"

    # Romaji
    particle_rm = "ga" if verb["type"] == "な-adj" else "o"
    conj_rm = conjugate_romaji(verb["romaji"], verb["type"], tense, polarity)
    rm_sentence = f"{person_rm} wa {noun['romaji']} {particle_rm} {conj_rm}."

    # English sentence
    verb_en = conjugate_english(verb["english"], person_en, tense, polarity)
    en_sentence = f"{person_en} {verb_en} {noun['english']}."

    context = f"{person_en} / {tense} / {polarity}"

    steps = [
        ("TRANSLATE", en_sentence, jp_sentence, rm_sentence, jp_sentence, "ja-JP-NanamiNeural"),
        ("COMPREHEND", jp_sentence, en_sentence, rm_sentence, en_sentence, "en-US-AriaNeural"),
        ("REINFORCE", en_sentence, jp_sentence, rm_sentence, jp_sentence, "ja-JP-NanamiNeural"),
    ]

    items = []
    idx = start_index
    for step, prompt, reveal, annotation, tts_text, tts_voice in steps:
        idx += 1
        items.append({
            "phase": "grammar",
            "step": step,
            "index": idx,
            "total": total,
            "counter": f"{idx}/{total}",
            "prompt": prompt,
            "reveal": reveal,
            "annotation": annotation,
            "context": context,
            "tts_text": tts_text,
            "tts_voice": tts_voice,
        })
    return items


def _llm_grammar_cycle(
    verb: dict,
    noun: dict,
    person_en: str,
    person_jp: str,
    person_rm: str,
    tense: str,
    polarity: str,
    start_index: int,
    total: int,
) -> list[dict]:
    """Generate 3 repetition touches for one LLM-enhanced grammar sentence."""
    # Use LLM to generate a natural sentence
    prompt = f"""
Generate a natural Japanese sentence using the following vocabulary and grammar pattern.

Vocabulary:
- Verb: {verb['english']} ({verb['japanese']}, {verb['romaji']})
- Noun: {noun['english']} ({noun['kanji']}, {noun['romaji']})
- Person: {person_en} ({person_jp}, {person_rm})

Grammar requirements:
- Tense: {tense}
- Polarity: {polarity}
- Use polite form (ます-form)
- Make it a natural, contextual sentence (not just "I eat fish")

Return a JSON object with:
{{
  "english": "Natural English sentence",
  "japanese": "自然な日本語の文",
  "romaji": "Nihongo na bun",
  "context": "Brief explanation of grammar point or context"
}}

Make the sentence natural and varied - avoid formulaic patterns.
""".strip()

    try:
        response = ask_llm_json(prompt)
        en_sentence = response["english"]
        jp_sentence = response["japanese"]
        rm_sentence = response["romaji"]
        context = response.get("context", f"{person_en} / {tense} / {polarity}")
    except Exception as e:
        # Fallback to deterministic if LLM fails
        print(f"LLM generation failed ({e}), falling back to deterministic")
        return _grammar_cycle(
            verb, noun, person_en, person_jp, person_rm,
            tense, polarity, start_index, total
        )

    # Use Japanese for TTS reveal, English for comprehension
    steps = [
        ("TRANSLATE", en_sentence, jp_sentence, rm_sentence, jp_sentence, "ja-JP-NanamiNeural"),
        ("COMPREHEND", jp_sentence, en_sentence, rm_sentence, en_sentence, "en-US-AriaNeural"),
        ("REINFORCE", en_sentence, jp_sentence, rm_sentence, jp_sentence, "ja-JP-NanamiNeural"),
    ]

    items = []
    idx = start_index
    for step, prompt, reveal, annotation, tts_text, tts_voice in steps:
        idx += 1
        items.append({
            "phase": "grammar",
            "step": step,
            "index": idx,
            "total": total,
            "counter": f"{idx}/{total}",
            "prompt": prompt,
            "reveal": reveal,
            "annotation": annotation,
            "context": context,
            "tts_text": tts_text,
            "tts_voice": tts_voice,
        })
    return items


# ── Main generator ───────────────────────────────────────────────────────


def generate_lesson_items(
    nouns: list[dict],
    verbs: list[dict],
    *,
    persons: list[tuple[str, str, str]] | None = None,
    tenses: tuple[str, ...] = ("present",),
    polarities: tuple[str, ...] = ("affirmative",),
    grammar_pairs: list[tuple[dict, dict]] | None = None,
    num_grammar_pairs: int = 3,
    use_llm: bool = False,
) -> list[dict]:
    """
    Generate a complete lesson as a list of structured item dicts.

    Each item is ready for the video pipeline (TTS + card rendering).

    Args:
        nouns: Selected noun dicts from vocab JSON.
        verbs: Selected verb dicts from vocab JSON.
        persons: List of (english, japanese, romaji) person tuples.
        tenses: Tenses to cover in grammar phase.
        polarities: Polarities to cover in grammar phase.
        grammar_pairs: Explicit (verb, noun) pairs for grammar sentences.
                       Auto-paired by index if None.
        num_grammar_pairs: Number of auto-generated verb-noun pairs (default 3).
        use_llm: If True, use LLM to generate natural grammar sentences.
                 If False, use deterministic conjugation (default).

    Returns:
        List of item dicts with: phase, step, index, total, counter,
        prompt, reveal, annotation, tts_text, tts_voice.
    """
    persons = persons or PERSONS

    # Auto-pair verbs with nouns for grammar
    if grammar_pairs is None:
        action_verbs = [v for v in verbs if v["type"] != "な-adj"]
        n = min(num_grammar_pairs, len(action_verbs), len(nouns))
        grammar_pairs = [(action_verbs[i], nouns[i]) for i in range(n)]

    # Calculate totals up front so every item knows the lesson size
    noun_count = len(nouns) * 5
    verb_count = len(verbs) * 5
    grammar_count = (
        len(grammar_pairs) * len(persons) * len(tenses) * len(polarities) * 3
    )
    total = noun_count + verb_count + grammar_count

    items: list[dict] = []

    # Phase 1: Nouns
    for noun in nouns:
        items.extend(_noun_cycle(noun, len(items), total))

    # Phase 2: Verbs
    for verb in verbs:
        items.extend(_verb_cycle(verb, len(items), total))

    # Phase 3: Grammar
    for verb, noun in grammar_pairs:
        for person_en, person_jp, person_rm in persons:
            for tense in tenses:
                for polarity in polarities:
                    if use_llm:
                        items.extend(
                            _llm_grammar_cycle(
                                verb, noun, person_en, person_jp, person_rm,
                                tense, polarity, len(items), total,
                            )
                        )
                    else:
                        items.extend(
                            _grammar_cycle(
                                verb, noun, person_en, person_jp, person_rm,
                                tense, polarity, len(items), total,
                            )
                        )

    return items


# ── Markdown renderer ────────────────────────────────────────────────────


def render_lesson_markdown(items: list[dict], theme: str) -> str:
    """Render lesson items as human-readable Markdown for review."""
    phases: dict[str, list[dict]] = {"nouns": [], "verbs": [], "grammar": []}
    for item in items:
        phases[item["phase"]].append(item)

    counts = {k: len(v) for k, v in phases.items()}
    total = sum(counts.values())

    lines = [
        f"# Japanese Lesson: {theme.title()}",
        "",
        f"**Total items:** {total} "
        f"({counts['nouns']} nouns + {counts['verbs']} verbs + {counts['grammar']} grammar)",
        "",
        "---",
        "",
    ]

    # Phase 1: Nouns
    lines.append("## Phase 1 — Nouns\n")
    current_word = None
    for item in phases["nouns"]:
        if item["step"] == "INTRODUCE":
            if current_word is not None:
                lines.append("")
            current_word = item["prompt"]
            lines.append(f"### {current_word}\n")
        lines.append(
            f"{item['index']}. **[{item['step']}]** "
            f"{item['prompt']} → {item['reveal']} ({item['annotation']})"
        )

    lines.append("\n---\n")

    # Phase 2: Verbs
    lines.append("## Phase 2 — Verbs\n")
    current_word = None
    for item in phases["verbs"]:
        if item["step"] == "INTRODUCE":
            if current_word is not None:
                lines.append("")
            current_word = item["prompt"]
            lines.append(f"### {current_word}\n")
        lines.append(
            f"{item['index']}. **[{item['step']}]** "
            f"{item['prompt']} → {item['reveal']} ({item['annotation']})"
        )

    lines.append("\n---\n")

    # Phase 3: Grammar
    lines.append("## Phase 3 — Grammar\n")
    current_context = None
    for item in phases["grammar"]:
        ctx = item.get("context", "")
        if ctx != current_context:
            if current_context is not None:
                lines.append("")
            current_context = ctx
            lines.append(f"### {ctx}\n")
        lines.append(
            f"{item['index']}. **[{item['step']}]** "
            f"{item['prompt']} → {item['reveal']}"
        )
        lines.append(f"   *{item['annotation']}*")

    lines.append("")
    return "\n".join(lines)
