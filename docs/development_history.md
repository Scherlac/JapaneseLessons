# Japanese Lessons — Project History

> This document captures completed work, spike results, bug encounters, and model
> evaluations. It is organized by project-scale chapters rather than as a single
> flat timeline so feature-level detail remains readable as the project grows.
>
> Current feature work: [../progress_report.md](../progress_report.md)  
> System-scale view: [project_scale.md](project_scale.md)  
> Current architecture: [architecture.md](architecture.md)

---

## Chapter 1 — Foundation And Project Shape

### Early March 2026 — Problem framing

- Existing Japanese study resources had low repetition and isolated focus.
- The project goal became: structured lessons with high repetition across vocabulary,
  grammar, and narrated output.

### Early March 2026 — Technology decisions established

| Area | Decision | Notes |
|------|----------|-------|
| TTS | `edge-tts` | Best balance of quality and implementation simplicity |
| Video pipeline | Pillow + moviepy | Kept composition code in Python while using FFmpeg underneath |
| Japanese fonts | Noto Sans JP with Yu Gothic fallback | Cross-platform direction decided early; Windows fallback remained practical default |
| LLM integration | OpenAI SDK + LM Studio | OpenAI-compatible endpoint preserved flexibility |

### Early March 2026 — Initial content schema

- Nouns: english, japanese, kanji, romaji
- Verbs: english, japanese, kanji, romaji, type, masu_form
- Initial theme files: `food` and `travel`
- Early grammar pairing experiments were stored in source vocab data during discovery

### 2026-03-15 — Package structure finalized

- Production code moved into `jlesson/`
- CLI entry point standardized to `jlesson`
- Video modules moved under `jlesson/video/`
- Exporters grouped under `jlesson/exporters/`
- Tests updated to import from the package layout

This created the current repository shape used by later pipeline work.

---

## Chapter 2 — LLM Generation And Validation

### Mid March 2026 — LM Studio integration constraints discovered

During spike work, several API realities became clear:

- `json_object` was rejected by LM Studio with HTTP 400
- `json_schema` worked reliably across tested models
- verbose reasoning polluted plain-text JSON responses
- older Mistral GGUF chat templates required folding system instructions into the user turn

### 2026-03-14 — Model evaluation results

| Model | JSON schema | Plain text | Japanese quality | Notes |
|---|---|---|---|---|
| `qwen/qwen3-14b` | ✅ 6.5s | ✅ 16s | ⭐⭐⭐ | Best Japanese; verbose outside schema mode |
| `qwen/qwen3.5-9b` | ✅ 4.5s | ✅ 22s | ⭐⭐⭐ | Good quality, very verbose plain text |
| `microsoft/phi-4-reasoning-plus` | ✅ 3.7s | ✅ 16s | ⭐⭐⭐ | `<think>` stripping required |
| `mistralai/ministral-3-14b-reasoning` | ✅ 6.7s | ✅ 17s | ⭐⭐⭐ | Correct Japanese + romaji |
| `mistral-7b-instruct-v0.3` | ✅ 5.5s | ✅ 9s | ⭐⭐ | No native system-role support |
| `meta-llama-3.1-8b-instruct` | ✅ 2.8s | ✅ 5s | ⭐ | Fast but weak Japanese payloads |
| `stable-code-instruct-3b` | ✅ 8.3s | ✅ 5s | ⭐ | Wrong domain for language work |
| `deepseek-math-7b-instruct` | ✅ 10.9s | ✅ 9s | ❌ | Japanese fields often empty |

Recommended outcome:

- prefer `qwen/qwen3-14b` for quality
- treat `json_schema` as the default structured-output mechanism on llama.cpp-backed systems

### March 2026 — Production hardening in LLM handling

Feature-level fixes and additions:

1. Added think-block stripping.
2. Replaced fragile flat-regex JSON extraction with brace-depth scanning.
3. Added whitespace normalization for noisy LLM string outputs.
4. Introduced file-based LLM response caching.
5. Added sentence review to score and rewrite unnatural generated sentences before downstream use.

These changes converted the LLM layer from spike-grade behavior into a more reliable
production-oriented subsystem.

---

## Chapter 3 — Compilation And Output Rendering

### Mid March 2026 — TTS and card-rendering spikes

#### spike_01 — TTS engine

- Validated `edge-tts` with `ja-JP-NanamiNeural`
- Discovered service rate limiting
- Added retry and pacing behavior during experimentation

#### spike_02 — Card renderer

- Validated Pillow at 1920×1080
- Established Japanese-first card layout conventions
- Confirmed fallback chain around Yu Gothic / MS Gothic on Windows

### Mid March 2026 — Video composition spikes

#### spike_03 / spike_04 — Video pipeline

- Confirmed end-to-end composition from cards + TTS audio to MP4
- Switched to FFmpeg stream-copy strategy for a large speedup
- Validated the lesson timing model used by later production rendering

#### spike_05 — Performance investigation

- Confirmed the previous FFmpeg path as a bottleneck before stream-copy optimization

### March 2026 — Production rendering architecture added

Feature-level additions:

- explicit compilation models for assets, touches, phases, and repetition steps
- profile system separating passive-video and active-flash-card behavior
- asset compiler for rendering cards and TTS per item
- touch compiler for profile-driven interleaving
- multi-audio clip support in the video builder
- profile-aware markdown lesson reporting

This was the point where rendering stopped being an ad-hoc dict pipeline and became
an explicit staged transformation.

---

## Chapter 4 — Lesson Pipeline And Delivery Flow

### 2026-03-15 — spike_08 curriculum workflow validation

- Validated grammar select → grammar generate → content validate → noun practice
- Confirmed the lesson workflow could run end to end with `qwen/qwen3-14b`
- Persisted representative output and curriculum data for inspection

### 2026-03-15 — spike_09 two-lesson integrated demo

First fully integrated demo combining:

- LLM generation
- TTS synthesis
- card rendering
- video output
- curriculum persistence

#### Bugs fixed during the first integrated demo

1. Nested JSON extraction bug in `_extract_json()`
2. Leading-space noise in LLM vocab fields
3. `PERSONS` tuple format mismatch
4. moviepy 2.x audio API breakage requiring `with_audio()` usage

### March 2026 — Production pipeline growth

Feature-level milestones:

1. Full lesson pipeline wired into the CLI
2. Lesson content persistence added before rendering
3. Verb practice step integrated into the pipeline
4. Seeded vocab shuffle introduced without touching global RNG state
5. Markdown lesson report added
6. Compilation pipeline stages wired into the lesson pipeline
7. `--profile` CLI option added
8. Sentence review step inserted between sentence generation and downstream practice stages

Net effect:

- the application moved from spike scripts to a stable packaged workflow
- content generation, compilation, reporting, and video rendering became one coherent path

---

## Chapter 5 — Quality, Testing, And Engineering Discipline

### 2026-05-30 — First large unit-test baseline

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

Unit path result at that point:

```text
pytest tests/ -m "not integration and not internet and not video"
→ 184 passed, 20 deselected in 6.65s
```

### March 2026 onward — Coverage growth through feature waves

Later milestones captured in status reporting and retained as historical fact:

- 274 total tests after cache and shuffle work
- 299 total tests after markdown report work
- 392 total tests after compilation pipeline work
- 414 total tests after pipeline integration work
- 437 total tests after sentence review work

### Durable engineering learnings

1. Spike-before-scale kept uncovering non-obvious constraints early.
2. Structured output enforcement was more reliable than post-hoc cleanup.
3. Rendering and compilation quality improved once intermediate data structures became explicit.
4. Documentation needed separation between active work, historical record, and architectural truth.

---

## Historical Notes Relevant To Future Work

These findings are likely to matter again in later feature waves:

- flat theme vocab files are convenient but weak as a long-term content platform
- Windows font handling worked for local delivery but remains a portability debt
- pipeline checkpointing was deferred while lesson builds were still relatively small
- retrieval and multilingual branching are natural next-scale concerns now that the lesson pipeline is stable