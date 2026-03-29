# Decision: Video Composition Pipeline

**Status:** Open  
**Date:** 2026-03-14  
**Context:** We need to compose text cards + audio clips into a learning video (.mp4). The pipeline must handle hundreds of short clips per lesson.

---

## Requirements

| Requirement | Priority |
|---|---|
| Compose image sequence + audio into .mp4 | **Must have** |
| Per-clip timing control (variable durations) | **Must have** |
| Text overlay / image-based frames | **Must have** |
| Progress bar / visual indicators | Should have |
| Transition effects between clips | Nice to have |
| Fast encoding (< 5 min for ~10 min video) | Should have |
| Cross-platform (Windows primary) | **Must have** |

---

## Options

### Option A: moviepy (already installed)

| Aspect | Detail |
|---|---|
| **Package** | `pip install moviepy` (v2.1.2 — already in env) |
| **Approach** | Python API: create `ImageClip` + `AudioFileClip`, concatenate, export |
| **Strengths** | Pythonic API; good for sequencing clips; supports text overlay, compositing, transitions |
| **Weaknesses** | Relies on ffmpeg binary; can be slow for long videos; memory-heavy for many clips |
| **ffmpeg dependency** | Required — moviepy calls ffmpeg under the hood |
| **Text rendering** | Built-in `TextClip` (requires ImageMagick) or use Pillow images as `ImageClip` |
| **Maturity** | v2.x is a maintained rewrite; widely used |

```python
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

card = ImageClip("card_001.png", duration=3.0)
audio = AudioFileClip("audio_001.mp3")
clip = card.with_audio(audio).with_duration(audio.duration + 2.0)
# ... concatenate all clips
```

### Option B: ffmpeg directly (via subprocess)

| Aspect | Detail |
|---|---|
| **Package** | No Python package — call `ffmpeg` via `subprocess` |
| **Approach** | Build ffmpeg concat/filter commands programmatically |
| **Strengths** | Maximum control; fastest encoding; no Python memory overhead |
| **Weaknesses** | Complex filter graph syntax; harder to debug; brittle string building |
| **Maturity** | ffmpeg is rock-solid; the subprocess wrapper is custom code |

```python
# Concat demuxer approach
# 1. Write a concat file listing each segment
# 2. ffmpeg -f concat -i list.txt -c copy output.mp4
```

### Option C: ffmpeg-python (Pythonic ffmpeg wrapper)

| Aspect | Detail |
|---|---|
| **Package** | `pip install ffmpeg-python` |
| **Approach** | Fluent Python API that generates ffmpeg commands |
| **Strengths** | Clean API; avoids manual command building; generates efficient ffmpeg pipelines |
| **Weaknesses** | Thin wrapper — still need to understand ffmpeg concepts; less intuitive for clip-by-clip composition |
| **Maturity** | Popular (4k+ GitHub stars) but maintenance has slowed |

### Option D: Manim (math animation engine)

| Aspect | Detail |
|---|---|
| **Package** | `pip install manim` |
| **Approach** | Programmatic animations with scenes, text objects, transitions |
| **Strengths** | Beautiful text animations; LaTeX support; designed for educational content |
| **Weaknesses** | Overkill for flashcard-style videos; heavy dependency (LaTeX, Cairo, etc.); steep learning curve |
| **Maturity** | Community edition actively maintained |

### Option E: Pillow + ffmpeg (image-per-frame + stitch)

| Aspect | Detail |
|---|---|
| **Package** | `Pillow` (already installed) + `ffmpeg` binary |
| **Approach** | Render each card as PNG with Pillow → feed image sequence to ffmpeg with audio |
| **Strengths** | Full control over card design; Pillow excels at text rendering with Japanese fonts; minimal deps |
| **Weaknesses** | Must handle timing/audio sync manually; two-stage process |
| **Maturity** | Both tools are rock-solid |

```python
# Stage 1: Pillow renders cards
from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGB", (1920, 1080), "#1a1a2e")
draw = ImageDraw.Draw(img)
draw.text((960, 400), "水", font=jp_font, anchor="mm", fill="white")
img.save("cards/001.png")

# Stage 2: moviepy or ffmpeg assembles
```

---

## Comparison Matrix

| Criterion | moviepy | ffmpeg subprocess | ffmpeg-python | Manim | Pillow + ffmpeg |
|---|---|---|---|---|---|
| Already installed | ✅ | Needs ffmpeg binary | Needs install | Needs install | ✅ (Pillow) + ffmpeg |
| Ease of use | ★★★★☆ | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★★★★☆ |
| Card design control | ★★★☆☆ | ★☆☆☆☆ | ★☆☆☆☆ | ★★★★★ | ★★★★★ |
| Japanese text | Via Pillow ImageClip | Via input images | Via input images | Via LaTeX/Pango | ★★★★★ Native |
| Encoding speed | ★★★☆☆ | ★★★★★ | ★★★★★ | ★★☆☆☆ | ★★★★☆ |
| Audio sync | Built-in | Manual | Manual | Built-in | Manual via moviepy |
| Extra dependencies | ffmpeg | ffmpeg | ffmpeg | ffmpeg, LaTeX, Cairo | ffmpeg |

---

## Recommendation

**Option E (hybrid): Pillow for card rendering + moviepy for assembly** ★ Recommended

This combines the best of both:

1. **Pillow** renders each text card as a PNG — full control over layout, Japanese fonts, progress bars, colors.
2. **moviepy** (already installed) loads each PNG as an `ImageClip`, attaches audio, concatenates, and exports to .mp4.

This avoids moviepy's `TextClip` (which needs ImageMagick) while keeping its convenient audio-sync and concatenation API.

**Only missing piece:** ffmpeg binary (required by moviepy for encoding).

---

## ffmpeg Installation Options

| Method | Command | Notes |
|---|---|---|
| conda | `conda install -c conda-forge ffmpeg` | Recommended — stays in env |
| winget | `winget install ffmpeg` | System-wide |
| scoop | `scoop install ffmpeg` | System-wide |
| Manual | Download from ffmpeg.org | Add to PATH manually |

---

## Decision

> **TBD** — To be confirmed by project owner.
