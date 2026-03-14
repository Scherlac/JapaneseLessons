# Decision: Text-to-Speech Engine

**Status:** Open  
**Date:** 2026-03-14  
**Context:** We need a TTS engine to generate audio narration for Japanese learning videos. Audio quality is critical — learners rely on correct pronunciation.

---

## Requirements

| Requirement | Priority |
|---|---|
| Japanese voice quality (natural pitch, mora timing) | **Must have** |
| English voice quality | **Must have** |
| Supports both Japanese and English in same pipeline | **Must have** |
| Free / no API key for development | Should have |
| Controllable speech rate (slow for learners) | Should have |
| Offline capability | Nice to have |
| SSML or prosody control | Nice to have |
| Low latency / fast generation | Nice to have |

---

## Options

### Option A: edge-tts (Microsoft Edge TTS)

| Aspect | Detail |
|---|---|
| **Package** | `pip install edge-tts` (v7.2.7) |
| **How it works** | Uses Microsoft Edge's online TTS service (same as Edge browser Read Aloud) |
| **Japanese voices** | `ja-JP-NanamiNeural` (female), `ja-JP-KeitaNeural` (male) — neural, high-quality |
| **English voices** | 10+ neural voices (en-US, en-GB, etc.) |
| **Audio quality** | ★★★★★ Neural voices, natural prosody, excellent Japanese pitch accent |
| **Cost** | Free, no API key |
| **Rate/pitch control** | Yes — `--rate`, `--pitch`, `--volume` flags |
| **Subtitle output** | Built-in `.srt` subtitle generation with word-level timing |
| **Offline** | No — requires internet |
| **Python API** | Async (`asyncio`-based), simple |
| **Maturity** | Actively maintained, 7.2.7 released Dec 2025 |
| **Risk** | Undocumented Microsoft API — could break if Microsoft changes endpoint. No SLA. |

```python
# Example usage
import edge_tts, asyncio

async def generate():
    tts = edge_tts.Communicate("水を飲みます", voice="ja-JP-NanamiNeural", rate="-20%")
    await tts.save("output.mp3")

asyncio.run(generate())
```

### Option B: Google Cloud Text-to-Speech

| Aspect | Detail |
|---|---|
| **Package** | `pip install google-cloud-texttospeech` (v2.34.0) |
| **How it works** | Official Google Cloud API |
| **Japanese voices** | WaveNet and Neural2 Japanese voices — studio quality |
| **English voices** | Extensive WaveNet, Neural2, Studio voices |
| **Audio quality** | ★★★★★ WaveNet/Neural2 are industry-leading |
| **Cost** | Free tier: 1M chars/month (WaveNet), 4M chars/month (standard). Then $16/1M chars (WaveNet) |
| **Rate/pitch control** | Full SSML support, speaking rate, pitch, emphasis |
| **Offline** | No |
| **Python API** | Official, well-documented, synchronous |
| **Maturity** | Production-grade Google product |
| **Risk** | Requires GCP project + billing enabled + API key setup. Paid beyond free tier. |

### Option C: Azure Cognitive Services Speech

| Aspect | Detail |
|---|---|
| **Package** | `pip install azure-cognitiveservices-speech` (v1.48.2) |
| **How it works** | Official Azure Speech SDK |
| **Japanese voices** | Same neural voices as edge-tts (NanamiNeural, KeitaNeural) plus more |
| **English voices** | 100+ neural voices |
| **Audio quality** | ★★★★★ Same engine as edge-tts but with SSML and fine control |
| **Cost** | Free tier: 500K chars/month. Then $16/1M chars (neural) |
| **Rate/pitch control** | Full SSML support |
| **Offline** | Partial — embedded speech SDK available |
| **Python API** | Official SDK, synchronous, event-driven |
| **Maturity** | Production-grade Microsoft product |
| **Risk** | Requires Azure account + subscription key. More complex setup. |

### Option D: Coqui TTS (local neural TTS)

| Aspect | Detail |
|---|---|
| **Package** | `pip install TTS` (v0.22.0) |
| **How it works** | Local deep learning models (VITS, XTTS, Bark, Tortoise) |
| **Japanese voices** | Fairseq VITS model for Japanese (`tts_models/jpn/fairseq/vits`), XTTS v2 supports Japanese |
| **English voices** | Many models (LJSpeech, VCTK multi-speaker, XTTS) |
| **Audio quality** | ★★★☆☆ to ★★★★☆ — XTTS v2 is good but not as natural as cloud neural for Japanese |
| **Cost** | Free, fully open-source (MPL-2.0) |
| **Rate/pitch control** | Limited — depends on model |
| **Offline** | Yes — fully offline after model download |
| **Python API** | `tts.tts_to_file(text, language="ja", ...)` |
| **Maturity** | Coqui.ai company shut down; community-maintained |
| **Risk** | Large model downloads (1-2 GB per model). Python < 3.12 only. Japanese quality trails behind cloud services. |

### Option E: gTTS (Google Translate TTS)

| Aspect | Detail |
|---|---|
| **Package** | `pip install gTTS` (v2.5.4) |
| **How it works** | Undocumented Google Translate speech API |
| **Japanese voices** | One voice — standard Google Translate quality |
| **English voices** | One voice per language |
| **Audio quality** | ★★☆☆☆ Flat, robotic compared to neural voices. No pitch accent. |
| **Cost** | Free, no API key |
| **Rate/pitch control** | No — fixed rate, no SSML |
| **Offline** | No |
| **Python API** | Very simple: `gTTS("text", lang="ja").save("out.mp3")` |
| **Maturity** | Stable but depends on undocumented Google API |
| **Risk** | **Audio quality too low for language learning.** Pronunciation issues for Japanese. |

### Option F: pyttsx3 (offline, system voices)

| Aspect | Detail |
|---|---|
| **Package** | `pip install pyttsx3` (v2.99) |
| **How it works** | Wraps OS speech engines (SAPI5 on Windows, espeak on Linux) |
| **Japanese voices** | Only if system has a Japanese SAPI5 voice installed (Windows) |
| **English voices** | System voices (David, Zira on Windows) |
| **Audio quality** | ★☆☆☆☆ to ★★☆☆☆ — SAPI5 is robotic; espeak in Japanese is unusable |
| **Cost** | Free, fully offline |
| **Rate/pitch control** | Yes — rate, volume, voice selection |
| **Offline** | Yes |
| **Python API** | Synchronous, simple |
| **Maturity** | Maintained |
| **Risk** | **Japanese quality is unacceptable for language learning.** |

---

## Comparison Matrix

| Criterion | edge-tts | Google Cloud | Azure Speech | Coqui TTS | gTTS | pyttsx3 |
|---|---|---|---|---|---|---|
| Japanese quality | ★★★★★ | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★☆☆☆ | ★☆☆☆☆ |
| English quality | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | ★★☆☆☆ | ★★☆☆☆ |
| Setup complexity | Trivial | High | High | Medium | Trivial | Trivial |
| Cost | Free | Free tier / paid | Free tier / paid | Free | Free | Free |
| Rate control | Yes | Full SSML | Full SSML | Limited | No | Yes |
| Offline | No | No | Partial | Yes | No | Yes |
| Subtitle timing | Built-in | No | Word-level events | No | No | No |
| Risk level | Medium | Low | Low | High | Medium | High |

---

## Recommendation

**Primary: Option A — edge-tts** ★ Recommended

- Best quality-to-effort ratio. Neural Japanese voices identical to Azure Speech but with zero setup.
- Built-in subtitle/timing output is a bonus for video synchronization.
- Rate control via `--rate=-20%` enables slower speech for learners.
- Risk (undocumented API) is acceptable for an educational side project.

**Fallback: Option B — Google Cloud TTS**

- If edge-tts breaks, Google Cloud TTS is the most reliable paid alternative.
- Requires GCP setup but free tier (1M chars/month) covers many lessons.

**Not recommended:** gTTS and pyttsx3 — audio quality is insufficient for Japanese language learning where correct pitch accent and mora timing matter.

---

## Decision

> **TBD** — To be confirmed by project owner.
