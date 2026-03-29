# Decision: Japanese Font & Text Rendering

**Status:** Open  
**Date:** 2026-03-14  
**Context:** Video cards must display Japanese text (kanji, hiragana, katakana) and English text clearly at 1080p. Font choice directly impacts readability and perceived quality.

---

## Requirements

| Requirement | Priority |
|---|---|
| Kanji + Hiragana + Katakana rendering | **Must have** |
| English / Latin character rendering | **Must have** |
| Clear at 1080p video resolution | **Must have** |
| Free / open-source license | **Must have** |
| Distinct visual weight: large prompt vs. small annotation | Should have |
| Monospace option for alignment (romaji) | Nice to have |

---

## Options

### Option A: Noto Sans JP (Google)

| Aspect | Detail |
|---|---|
| **Source** | [Google Fonts](https://fonts.google.com/noto/specimen/Noto+Sans+JP) |
| **Coverage** | Full CJK (kanji, hiragana, katakana) + Latin + symbols |
| **Weights** | Thin, Light, Regular, Medium, Bold, Black (100–900) |
| **License** | OFL (SIL Open Font License) — free for any use |
| **Style** | Clean sans-serif; neutral; excellent screen readability |
| **File size** | ~5 MB per weight (variable font ~16 MB) |
| **Pros** | Industry standard for CJK; designed by Google/Adobe; excellent hinting |
| **Cons** | Very common — no distinctive character |

### Option B: Noto Serif JP (Google)

| Aspect | Detail |
|---|---|
| **Source** | [Google Fonts](https://fonts.google.com/noto/specimen/Noto+Serif+JP) |
| **Coverage** | Same as Noto Sans JP |
| **Weights** | ExtraLight, Light, Regular, Medium, SemiBold, Bold, Black |
| **License** | OFL |
| **Style** | Elegant serif; more traditional/formal feel |
| **Pros** | Good for mixing with sans-serif English; feels more "Japanese textbook" |
| **Cons** | Slightly harder to read at small sizes on screen |

### Option C: M PLUS Rounded 1c

| Aspect | Detail |
|---|---|
| **Source** | [Google Fonts](https://fonts.google.com/specimen/M+PLUS+Rounded+1c) |
| **Coverage** | Full CJK + Latin |
| **Weights** | Thin, Light, Regular, Medium, Bold, ExtraBold, Black |
| **License** | OFL |
| **Style** | Rounded sans-serif; friendly, approachable |
| **Pros** | Warm, casual feel — great for learning materials; very readable |
| **Cons** | Rounded style may look less serious |

### Option D: Zen Maru Gothic

| Aspect | Detail |
|---|---|
| **Source** | [Google Fonts](https://fonts.google.com/specimen/Zen+Maru+Gothic) |
| **Coverage** | Full CJK + Latin |
| **Weights** | Light, Regular, Medium, Bold, Black |
| **License** | OFL |
| **Style** | Soft rounded gothic; modern and clean |
| **Pros** | Modern aesthetic; good balance between friendly and professional |
| **Cons** | Less widely known; fewer resources for debugging |

### Option E: System Fonts (MS Gothic / Yu Gothic)

| Aspect | Detail |
|---|---|
| **Source** | Pre-installed on Windows |
| **Coverage** | Full CJK + Latin |
| **Weights** | Regular, Bold (Yu Gothic has Light/Regular/Bold) |
| **License** | Microsoft license — bundled with Windows |
| **Style** | Yu Gothic: modern sans-serif; MS Gothic: monospace-like |
| **Pros** | Zero download; guaranteed available on Windows |
| **Cons** | Not portable to Linux/Mac; Yu Gothic not freely distributable; limited weights |

---

## Font Pairing Strategy

For the video cards we need **two** visual roles:

| Role | Used for | Ideal style |
|---|---|---|
| **Primary Japanese** | Kanji, kana display (large, centered) | Bold, clear, large size (80–120pt) |
| **Secondary / Annotation** | Romaji, English translation, labels | Regular weight, smaller (30–48pt) |

**Suggested pairings:**

| Pairing | Japanese (Primary) | English/Romaji (Secondary) | Feel |
|---|---|---|---|
| A | Noto Sans JP Bold | Noto Sans Regular | Clean, neutral |
| B | M PLUS Rounded 1c Bold | Noto Sans Regular | Friendly, approachable |
| C | Noto Serif JP Bold | Noto Sans JP Regular | Traditional + modern |
| D | Zen Maru Gothic Bold | Noto Sans JP Light | Soft, modern |

---

## Rendering Approach with Pillow

```python
from PIL import Image, ImageDraw, ImageFont

# Load fonts
jp_font = ImageFont.truetype("fonts/NotoSansJP-Bold.ttf", size=96)
en_font = ImageFont.truetype("fonts/NotoSans-Regular.ttf", size=40)
label_font = ImageFont.truetype("fonts/NotoSans-Medium.ttf", size=28)

# Create card
img = Image.new("RGB", (1920, 1080), "#1a1a2e")
draw = ImageDraw.Draw(img)

# Japanese text (centered)
draw.text((960, 400), "水", font=jp_font, anchor="mm", fill="#ffffff")

# Romaji annotation
draw.text((960, 520), "mizu", font=en_font, anchor="mm", fill="#aaaaaa")

# English translation
draw.text((960, 620), "water", font=en_font, anchor="mm", fill="#4fc3f7")

img.save("card.png")
```

---

## Font Acquisition

| Method | Command / Action |
|---|---|
| Download from Google Fonts | Manual: download .ttf, place in `fonts/` folder |
| `fontools` / `gfonts` | `pip install gfonts && gfonts get "Noto Sans JP"` |
| wget/curl | `curl -L -o NotoSansJP.zip "https://fonts.google.com/download?family=Noto+Sans+JP"` |
| System fonts | Already at `C:\Windows\Fonts\` — use `Yu Gothic` |

**Recommendation:** Download Noto Sans JP (and optionally M PLUS Rounded 1c) into a `fonts/` directory in the project. Add `fonts/` to `.gitignore` (font files are large).

---

## Comparison Matrix

| Criterion | Noto Sans JP | Noto Serif JP | M PLUS Rounded | Zen Maru Gothic | System fonts |
|---|---|---|---|---|---|
| Readability at 1080p | ★★★★★ | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| CJK coverage | Full | Full | Full | Full | Full |
| Learning-friendly feel | ★★★★☆ | ★★★☆☆ | ★★★★★ | ★★★★★ | ★★★☆☆ |
| Weight variety | 6 | 7 | 7 | 5 | 2–3 |
| Portability | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ★☆☆☆☆ |
| License | OFL | OFL | OFL | OFL | Restricted |

---

## Recommendation

**Option A: Noto Sans JP** ★ Recommended as primary choice

- Best all-around: clear, neutral, full CJK, excellent hinting, 6 weights.
- Industry standard — guaranteed correct rendering of all kanji.
- Pair with Noto Sans (Latin) for English text.

**Alternative: Option C (M PLUS Rounded 1c)** for a warmer, more approachable style if the video targets casual learners.

---

## Decision

> **TBD** — To be confirmed by project owner.
