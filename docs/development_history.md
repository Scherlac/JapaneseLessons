# Japanese Lessons — Development History

> This document captures the chronological history of research findings, spike results,
> bug encounters, and model evaluations. It is a record for reference, **not** a
> statement of current architecture or status. See `progress_report.md` for the living
> description of the project.

---

## Phase 1 — Research & Foundation (Early March 2026)

### Problem Statement
- Existing Japanese study resources have low repetition counts and isolated focus.
- Goal: build a CLI tool that generates structured lessons with high-repetition (5+
  touches per item) across three phases: Nouns → Verbs → Grammar.

### Technology Decisions Made

All decisions documented in `docs/`:

| Decision | Winner | Alternatives Considered |
|----------|--------|------------------------|
| TTS engine | **edge-tts** | gTTS, pyttsx3, Coqui TTS, Google Cloud TTS, Azure TTS |
| Video pipeline | **Pillow + moviepy** | OpenCV, FFmpeg direct, manim, Remotion |
| Japanese fonts | **Noto Sans JP** (Yu Gothic Bold fallback) | MS Gothic, IPAexGothic, Arial Unicode MS, system default |
| LLM integration | **OpenAI SDK + LM Studio** | Ollama, OpenAI API, Anthropic, LangChain |

### Core Data Schema Established
- **Nouns**: `english`, `japanese` (kana), `kanji`, `romaji`
- **Verbs**: + `type` (`る-verb` / `う-verb` / `irregular` / `な-adj`), `masu_form`
- Initial vocab files: `vocab/food.json` (12 nouns, 10 verbs), `vocab/travel.json` (12 nouns, 10 verbs)
- `food.json` also contains `grammar_pairs` (explicit pairings: eat+fish, drink+water, cook+meat)

---

## Phase 2 — Spike Implementations (Mid March 2026)

All spikes live in `spike/`. They were kept as-is after being extractedto production modules.

### spike_01 — TTS Engine
- Validated `edge-tts` with `ja-JP-NanamiNeural` voice at `-20%` rate
- Discovered rate limiting from Microsoft Edge TTS service → added 1-second delays between requests + retry with exponential backoff
- Full pipeline handles up to 87 audio items

### spike_02 — Card Renderer
- Validated Pillow at 1920×1080 with Yu Gothic Bold for Japanese text
- Established card layout: label + counter, English (large), blank pause gap, Japanese reveal, progress bar
- Font fallback chain: `YuGothB.ttc` → `msgothic.ttc`

### spike_03 / spike_04 — Video Pipeline
- `spike_03`: individual clip creation with moviepy
- `spike_04`: full pipeline: cards + TTS audio → concatenated MP4
- **Performance fix**: switched to FFmpeg stream copying → **12.5× faster** video generation
- Confirmed timing model: 1.5s prompt + 2.0s pause + ~1.5s TTS + 1.5s hold ≈ 7.5s per item

### spike_05 — Performance
- Profiling of the full pipeline; confirmed FFmpeg path as the bottleneck before stream-copy fix

### spike_06 — LLM Provider Benchmark
- Multi-provider benchmark: Ollama (not running, skipped), LM Studio, OpenAI
- Added host reachability pre-check; 15-second per-provider budget; 10-second per-request timeout
- LM Studio hit 15s budget on first run (model was slow to load cold)

### spike_07 — LM Studio Deep Evaluation (3 Runs)

**Run 1** — initial connectivity check:
- Discovered: `json_object` response_format rejected with HTTP 400
- Discovered: plain text works but verbose thinking output pollutes JSON

**Run 2** — switched to `json_schema`:
- Added `qwen/qwen3.5-9b` (new locally available model)
- `mistral-7b-instruct-v0.3` still failing (HTTP 400 on system message)
- 6/8 models passing

**Run 3** — all models:
- Added `build_messages()` helper to fold system content into user turn for old Mistral GGUFs
- Added `extract_json()` to fish JSON out of verbose reasoning output
- **Final result: 8/8 models pass `json_schema` structured output**

#### LM Studio Model Evaluation Table (2026-03-14)

| Model | JSON schema | Plain text | Japanese quality | Notes |
|---|---|---|---|---|
| `qwen/qwen3-14b` | ✅ 6.5s | ✅ 16s | ⭐⭐⭐ | Best Japanese; thinking model, verbose plain text |
| `qwen/qwen3.5-9b` | ✅ 4.5s | ✅ 22s | ⭐⭐⭐ | Good Japanese; extremely verbose plain text |
| `microsoft/phi-4-reasoning-plus` | ✅ 3.7s | ✅ 16s | ⭐⭐⭐ | Correct Japanese; `<think>` stripping needed |
| `mistralai/ministral-3-14b-reasoning` | ✅ 6.7s | ✅ 17s | ⭐⭐⭐ | Correct Japanese + romaji |
| `mistral-7b-instruct-v0.3` | ✅ 5.5s | ✅ 9s | ⭐⭐ | No system role — merge into user turn |
| `meta-llama-3.1-8b-instruct` | ✅ 2.8s | ✅ 5s | ⭐ | Fastest; Japanese field empty in schema mode |
| `stable-code-instruct-3b` | ✅ 8.3s | ✅ 5s | ⭐ | Romaji field contains Japanese — code model |
| `deepseek-math-7b-instruct` | ✅ 10.9s | ✅ 9s | ❌ | Japanese/romaji empty — math model |

**Recommended**: `qwen/qwen3-14b` (best quality) or `qwen/qwen3.5-9b` (slightly faster JSON).  
**Avoid**: `deepseek-math`, `stable-code` — wrong domain.
**Key insight**: `json_schema` with llama.cpp grammar sampling works on **all** models regardless of thinking/verbose tendencies — token constraint enforces structure before reasoning can pollute output.

### spike_08 — Curriculum Workflow Validation
- Full end-to-end test: grammar select → grammar generate → content validate → noun practice
- Model: `qwen/qwen3-14b`
- Grammar select: 12.1s | Grammar generate: 21.4s | Validation: **10/10** in 2.6s | Noun practice: 11.5s
- Output: `spike/output/spike_08_curriculum.json`, `curriculum/curriculum.json` (Lesson 1 created)

### spike_09 — Two-Lesson Demo (2026-03-15)

First fully integrated demo: LLM pipeline + TTS + video render.

**Bugs encountered and fixed during first run:**

1. **`_extract_json()` nested JSON** — flat-object regex `r'\{[^{}]+\}'` could not match nested dicts like `{"nouns":[...]}`. Fixed: replaced with a brace-depth scanner `_find_json_objects()`.

2. **Vocab string whitespace** — LLM returned `' irregular'` (leading space) causing schema validation failure. Fixed: added strip pass over all string values in `vocab_generator.generate_vocab()`.

3. **`PERSONS` format mismatch** — `config.py` had `["I", "you", "she"]` (plain strings) but `build_grammar_generate_prompt` expects `list[tuple[str,str,str]]`. Fixed: changed to `[("I","私","watashi"), ...]`.

4. **moviepy 2.x audio API** — `CompositeVideoClip([img, audio])` raised `AttributeError: 'AudioFileClip' has no attribute 'layer_index'`. Fixed: changed to `img_clip.with_audio(audio_clip)`.

**Demo result (2026-03-15, `qwen/qwen3-14b`, 192s total):**
- Lesson 1 (food): 6 sentences, 3 noun items → `output/demo/lesson_01_food.mp4` (482 KB)
- Lesson 2 (travel): 6 sentences, 3 noun items → `output/demo/lesson_02_travel.mp4` (571 KB)
- Curriculum saved → `output/demo/curriculum_demo.json`

---

## Phase 3 — Unit Test Suite (2026-05-30)

| Test file | Tests | Markers |
|-----------|-------|---------|
| `test_llm_client.py` | 34 | 14 `integration` |
| `test_video_cards.py` | 29 | — |
| `test_tts_engine.py` | 26 | 4 `internet` |
| `test_video_builder.py` | 15 | 2 `video` |
| `test_curriculum.py` | 42 | — |
| `test_vocab_generator.py` | 18 | — |
| `test_prompt_template.py` | 37 | — |
| **Total** | **204** | **20 non-unit deselected** |

```
pytest tests/ -m "not integration and not internet and not video"
→ 184 passed, 20 deselected in 6.65s
```

---

## LLM Integration — Technical Notes

### json_schema vs json_object
LM Studio uses llama.cpp grammar-based sampling. `json_object` returns HTTP 400. Must use
`json_schema` with a schema definition. This enforces valid JSON at the token level.

### Thinking model handling
Models: `qwen3-14b`, `qwen3.5-9b`, `phi-4-reasoning-plus`, `ministral-3-14b-reasoning`
- Send `/no_think` as system message to suppress reasoning blocks
- `_strip_think()` in `llm_client.py` strips residual `<think>...</think>` blocks
- `_extract_json()` scans from end of text (reasoning models place answer last)

### Mistral v0.x GGUF chat template
`mistral-7b-instruct-v0.3` GGUF has no system-role token in its `[INST]` template.
Sending a system message causes HTTP 400. Solution: prepend system content to user turn.
Handled automatically by `LLMClient._build_messages()`.

### ask_llm_json_free() vs ask_llm_json()
- `ask_llm_json()` (via `generate_json(json_mode=True)`) uses `json_schema` with the fixed
  `_TRANSLATION_SCHEMA` — for structured translation responses only.
- `ask_llm_json_free()` uses `generate_text(json_mode=False)` + `_extract_json()` — for
  free-form JSON where the response shape varies (vocab dicts, sentence arrays, validation reports).

---

## Key Learnings

- **`json_schema` is the right tool** for constrained JSON on llama.cpp backends — bypasses all verbose reasoning noise.
- **Spike before scaling** — each spike discovered at least one non-obvious constraint (rate limits, API quirks, movie py API breakage, font path issues).
- **Grammar sampling requires known schema** — for variable-shape JSON (`ask_llm_json_free`), plain text + extraction is more flexible than rigid `json_schema`.
- **moviepy 2.x broke the audio API** — `with_audio()` replaced composite clip pattern; always pin major dependencies in `pyproject.toml`.
- **LLM output is noisy** — string whitespace trimming, nested JSON extraction, and think-block stripping are all necessary in production LLM parsing.
