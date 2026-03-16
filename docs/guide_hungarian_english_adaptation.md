# Guide: Adapting the Lesson Generator for Hungarian Kids Learning English

**Audience:** Non-developer with agile experience, using GitHub Copilot in VS Code to make changes.

---

## 📋 Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Your Setup Checklist](#your-setup-checklist)
3. [How to Talk to GitHub Copilot](#how-to-talk-to-github-copilot)
4. [The Adaptation Plan (Your Backlog)](#the-adaptation-plan-your-backlog)
5. [Sprint 1 — Vocabulary Files](#sprint-1--vocabulary-files)
6. [Sprint 2 — Grammar Curriculum](#sprint-2--grammar-curriculum)
7. [Sprint 3 — LLM Prompts](#sprint-3--llm-prompts)
8. [Sprint 4 — Text-to-Speech Voices](#sprint-4--text-to-speech-voices)
9. [Sprint 5 — Video Cards & Fonts](#sprint-5--video-cards--fonts)
10. [Sprint 6 — Testing & Polish](#sprint-6--testing--polish)
11. [Day-to-Day Workflow](#day-to-day-workflow)
12. [Troubleshooting](#troubleshooting)
13. [Key Files Reference](#key-files-reference)

---

## What This Project Does

This tool automatically creates language lessons as videos. Each lesson has three parts:

1. **Nouns** — Learn 6–12 things (like "dog", "water", "bread")
2. **Verbs** — Learn 6–10 actions (like "to eat", "to run")
3. **Grammar sentences** — Practice sentences that combine the nouns and verbs using grammar rules

The tool then:
- Asks an AI (LLM) to generate the lesson content
- Creates audio files using text-to-speech
- Creates visual cards (PNG images) with the words
- Assembles everything into an MP4 video

**Currently it teaches Japanese to English speakers. You will change it to teach English to Hungarian speakers.**

---

## Your Setup Checklist

Before you start, make sure these are working:

- [ ] **VS Code** is installed with the **GitHub Copilot** extension
- [ ] **Copilot Chat** panel is visible (click the chat icon in the sidebar, or press `Ctrl+Shift+I`)
- [ ] **Python** is installed (the project uses Python 3.12)
- [ ] **Conda environment** is activated — open a terminal in VS Code (`Ctrl+``) and type:
  ```
  conda activate py312
  ```
- [ ] **LM Studio** is running on the network (this is the AI that generates lesson content)
- [ ] **The project runs** — test with:
  ```
  jlesson vocab list
  ```
  If this shows a list of themes, everything works.

---

## How to Talk to GitHub Copilot

GitHub Copilot is your AI programming assistant. You tell it what to do **in plain English**, and it writes the code. Here's how to use it effectively:

### Opening Copilot Chat
- Press **Ctrl+Shift+I** to open the chat panel
- Or click the **Copilot icon** in the VS Code sidebar

### Golden Rules

1. **Always open the relevant file first.** Before asking Copilot to change something, click on the file in the Explorer panel so it's visible. Copilot works best when it can see the file you're talking about.

2. **Be specific.** Instead of "change the language", say:
   > "In this file, replace all Japanese-related field names with English-Hungarian equivalents. Change `japanese` to `hungarian`, `kanji` to remove it, `romaji` to `pronunciation`."

3. **Work in small steps.** Don't ask for everything at once. Ask for one change, check it works, then ask for the next.

4. **Reference the existing docs.** This project has detailed documentation. Point Copilot to it:
   > "Read the file docs/decision_llm_integration.md and then help me change the LLM prompts for English lessons."

5. **Ask Copilot to explain before changing.** When unsure:
   > "Explain what this file does before I change anything."

### Useful Copilot Commands

| What you want | What to type in Copilot Chat |
|---|---|
| Understand a file | "Explain what `jlesson/curriculum.py` does in simple terms" |
| Make a change | "In `vocab/food.json`, replace every Japanese entry with Hungarian translations" |
| Run tests | "Run the tests to check if anything is broken" |
| See what a command does | "What does `jlesson lesson next --theme food` do step by step?" |
| Fix an error | Copy-paste the error and ask "What does this error mean and how do I fix it?" |
| Create a new file | "Create a new vocabulary file `vocab/colors.json` with 10 color nouns and 5 verbs about colors, using English and Hungarian" |

### Using @workspace

When you type `@workspace` before your question, Copilot searches the entire project:
> "@workspace where are the Japanese-specific text-to-speech voice settings?"

This is very powerful — use it whenever you don't know where something is.

---

## The Adaptation Plan (Your Backlog)

Think of this as your Product Backlog. Each "Sprint" is a group of related changes. **Do them in order** — later sprints depend on earlier ones.

| Sprint | What Changes | Risk | Files Affected |
|--------|-------------|------|---------------|
| 1 — Vocabulary | Replace Japanese vocab with Hungarian-English vocab | Low | `vocab/*.json`, `jlesson/vocab_generator.py`, `jlesson/models.py` |
| 2 — Grammar | Replace Japanese grammar progression with English | Medium | `jlesson/curriculum.py`, `curriculum/curriculum.json` |
| 3 — Prompts | Change LLM instructions from Japanese to English-for-Hungarians | Medium | `jlesson/prompt_template.py` |
| 4 — Audio | Switch TTS voices (remove Japanese, add Hungarian narration) | Low | `jlesson/video/tts_engine.py` |
| 5 — Cards | Update visual card rendering (fonts, layout) | Low | `jlesson/video/cards.py`, `jlesson/config.py` |
| 6 — Testing | Run all tests, fix failures, generate a test lesson | Low | `tests/*.py` |

---

## Sprint 1 — Vocabulary Files

**Goal:** Replace Japanese vocabulary with Hungarian-English vocabulary.

### Step 1.1 — Understand the current format

Open `vocab/food.json` in VS Code and look at it. You'll see entries like:
```json
{
  "english": "water",
  "japanese": "みず",
  "kanji": "水",
  "romaji": "mizu"
}
```

You want to change this to:
```json
{
  "english": "water",
  "hungarian": "víz",
  "pronunciation": "ˈwɔːtər"
}
```

### Step 1.2 — Ask Copilot to update the data model

Open `jlesson/models.py` and tell Copilot:

> "In this file, find the NounItem and VerbItem classes. Replace the Japanese fields (`japanese`, `kanji`, `romaji`) with Hungarian-English fields: `hungarian` (the Hungarian translation) and `pronunciation` (English pronunciation guide). For VerbItem, also remove `type` and `masu_form` (these are Japanese-specific) and add `past_tense` (English past tense form). Keep the `english` field as-is."

### Step 1.3 — Update all vocabulary files

For each file in the `vocab/` folder, open it and tell Copilot:

> "Rewrite this vocabulary file. Keep the theme and the English words, but replace all Japanese data with Hungarian translations and English pronunciation guides. Remove `kanji` and `romaji` fields. Add `hungarian` and `pronunciation` fields."

**Tip:** You can also ask Copilot to create brand new vocabulary files:
> "Create a new file `vocab/colors.json` with 10 color nouns (english + hungarian + pronunciation) and 5 color-related verbs for Hungarian children learning English."

### Step 1.4 — Update the vocabulary generator

Open `jlesson/vocab_generator.py` and tell Copilot:

> "This file generates vocabulary via LLM. Update it so it generates English-Hungarian vocabulary instead of English-Japanese. The LLM prompt should ask for nouns with fields: english, hungarian, pronunciation. Verbs should have: english, hungarian, pronunciation, past_tense. Update the validation function too."

### Step 1.5 — Verify

Run in the terminal:
```
jlesson vocab list
```
Then try generating a new theme:
```
jlesson vocab create toys
```

---

## Sprint 2 — Grammar Curriculum

**Goal:** Replace Japanese grammar progression with English grammar for beginners.

### Step 2.1 — Understand the current grammar system

Tell Copilot:
> "@workspace explain the grammar progression system. What grammar points exist and how are they organized?"

The current system has 15 Japanese grammar points (like "present affirmative verb form", "past negative", etc.) organized in levels with prerequisites.

### Step 2.2 — Design your English grammar progression

Here's a suggested progression for Hungarian kids learning English:

| Level | Grammar Points | Example |
|-------|---------------|---------|
| 1 | `present_simple_affirmative`, `identity_is_am_are` | "I eat bread", "She is a teacher" |
| 2 | `present_simple_negative`, `present_simple_question`, `past_simple_affirmative` | "I don't eat fish", "Do you like cats?", "I ate bread" |
| 3 | `past_simple_negative`, `past_simple_question`, `can_ability` | "I didn't eat", "Did you run?", "I can swim" |
| 4 | `present_continuous`, `there_is_are`, `have_got` | "I am eating", "There is a cat", "I have got a dog" |
| 5 | `past_continuous`, `will_future`, `going_to_future` | "I was eating", "I will eat", "I am going to eat" |
| 6 | `first_conditional`, `must_should`, `comparisons` | "If it rains, I will stay", "You must study", "bigger than" |

### Step 2.3 — Ask Copilot to rewrite the grammar table

Open `jlesson/curriculum.py` and tell Copilot:

> "Replace the GRAMMAR_PROGRESSION list and PERSONS_BEGINNER with an English grammar progression for Hungarian kids. Use these grammar points: [paste the table above]. Each grammar point needs: id, label, level, pattern (an English sentence pattern), example sentence, and prerequisites (which earlier grammar points must be learned first). Also replace PERSONS_BEGINNER with English pronouns: I, You, He, She, We, They."

### Step 2.4 — Reset the curriculum

Open `curriculum/curriculum.json` and tell Copilot:

> "Reset this curriculum file to a fresh start with no lessons completed. Set covered_grammar_ids, covered_nouns, and covered_verbs to empty lists."

---

## Sprint 3 — LLM Prompts

**Goal:** Change the AI instructions so it generates English lessons for Hungarian learners.

### Step 3.1 — Understand the prompts

Open `jlesson/prompt_template.py` and tell Copilot:
> "Explain each function in this file and what it generates."

This file contains the instructions sent to the AI. Currently they say things like "Generate Japanese sentences with romaji..."

### Step 3.2 — Rewrite prompts

Tell Copilot:

> "Rewrite all prompt functions in this file. Instead of generating Japanese lessons for English speakers, they should generate English lessons for Hungarian-speaking children (ages 8-12). Key changes:
> - The target language is now English (not Japanese)
> - The native language is now Hungarian (not English)
> - Remove all references to kanji, romaji, hiragana
> - Instead of Japanese example sentences, generate English example sentences with Hungarian translations
> - Memory tips should explain English concepts in ways a Hungarian child would understand
> - Grammar patterns should use English grammar (not Japanese particles/conjugation)"

### Step 3.3 — Test a prompt

Run:
```
jlesson lesson prompt food
```
This will print the prompt **without** calling the AI. Read it to check it makes sense.

---

## Sprint 4 — Text-to-Speech Voices

**Goal:** Change audio voices from Japanese to English + Hungarian.

### Step 4.1 — Update voice settings

Open `jlesson/video/tts_engine.py` and tell Copilot:

> "This file uses Microsoft Edge TTS voices. Currently it has Japanese voices (ja-JP). Change it to:
> - English voice (keep the existing en-US-AriaNeural or use en-GB-SoniaNeural for British English)
> - Hungarian voice: hu-HU-NoemiNeural (for Hungarian narration/explanations)
> - Remove all Japanese voice references (ja-JP-NanamiNeural, ja-JP-KeitaNeural)
> - Update the VOICES dictionary: keep an English female, English male, and add Hungarian female"

### Step 4.2 — Test audio

After making changes, run a lesson with:
```
jlesson lesson next --theme food --no-video
```
Check the `output/` folder for audio files and listen to them.

---

## Sprint 5 — Video Cards & Fonts

**Goal:** Update the visual cards for English-Hungarian content.

### Step 5.1 — Update card rendering

Open `jlesson/video/cards.py` and tell Copilot:

> "This card renderer creates visual cards with Japanese and English text. Update it for English-Hungarian:
> - Where it shows Japanese text, show the Hungarian translation instead
> - Where it shows romaji, show pronunciation guide instead
> - Remove kanji rendering
> - Keep the English text as the main/large text (since English is the target language)
> - Font: use Segoe UI for both English and Hungarian (both use Latin alphabet)"

### Step 5.2 — Update any font configurations

Open `jlesson/config.py` and tell Copilot:
> "Update font settings — remove any Japanese font references (Yu Gothic, YuGothB.ttc). Use Segoe UI for all text since English and Hungarian both use the Latin alphabet."

---

## Sprint 6 — Testing & Polish

### Step 6.1 — Run the tests

```
pytest tests/ -m "not integration and not internet and not video" -v
```

Many tests will fail because the data structures changed. That's expected.

### Step 6.2 — Fix failing tests

For each failing test, open the test file and tell Copilot:

> "This test is failing because we changed the data model from Japanese to Hungarian-English. Update the test data and assertions to match the new NounItem and VerbItem fields (hungarian, pronunciation instead of japanese, kanji, romaji)."

### Step 6.3 — Generate your first Hungarian-English lesson!

```
jlesson lesson next --theme food
```

Check the output in the `output/` folder:
- `content.json` — does it have Hungarian translations and English content?
- `report.md` — does the report look right?
- Audio files — do they sound correct?
- Video — does it play correctly?

---

## Day-to-Day Workflow

### Before making changes
1. Open VS Code terminal (`Ctrl+``)
2. Make sure you're in the right folder: `cd c:\01_dev\japanese`
3. Activate your environment: `conda activate py312`

### Making a change
1. **Open the file** you want to change in VS Code
2. **Open Copilot Chat** (Ctrl+Shift+I)
3. **Tell Copilot what to change** — be specific, reference the file
4. **Review the suggestion** — Copilot will show you what it wants to change
5. **Click "Apply"** or "Accept" to make the change
6. **Save the file** (Ctrl+S)

### After making changes
1. **Run tests** to check nothing is broken:
   ```
   pytest tests/ -m "not integration and not internet and not video" -v
   ```
2. **Save your work to Git:**
   ```
   git add -A
   git commit -m "Brief description of what you changed"
   git push
   ```

### When something breaks
1. **Don't panic** — Git saves all your previous work
2. **Copy the error message** from the terminal
3. **Paste it into Copilot Chat** and ask: "What does this error mean and how do I fix it?"
4. **If you want to undo everything** back to the last commit:
   ```
   git checkout .
   ```
   (This discards all changes since your last `git commit`)

### Reading the project documentation

This project has detailed docs about every design decision. When Copilot asks you to make choices, or when you're unsure about an approach, these documents are helpful:

| Document | What it explains |
|----------|-----------------|
| `docs/decision_llm_integration.md` | How the AI (LLM) connection works |
| `docs/decision_video_pipeline.md` | How videos are assembled |
| `docs/decision_tts_engine.md` | How text-to-speech audio works |
| `docs/decision_persistence.md` | How lesson data is saved |
| `docs/decision_fonts_rendering.md` | How text is rendered on cards |
| `docs/decision_pipeline_orchestration.md` | How the lesson generation pipeline works |
| `docs/decision_caching.md` | How LLM response caching works |
| `docs/development_history.md` | Full history of how the project was built |
| `progress_report.md` | Current status, roadmap, technical debt |

To use them with Copilot:
> "Read docs/decision_tts_engine.md and then help me change the voices for Hungarian-English"

---

## Troubleshooting

### "I don't know which file to change"
Ask Copilot: `@workspace where is the code that handles [describe what you're looking for]?`

### "The tests all fail after my changes"
This is normal when changing data structures. Work through them one test file at a time. Ask Copilot to fix each test file.

### "The AI generates wrong content"
The AI instructions are in `jlesson/prompt_template.py`. Open it and refine the prompts. Tell Copilot:
> "The AI is generating [describe the problem]. Update the prompt to be more specific about [what you want]."

### "Audio sounds wrong or uses the wrong language"
Check `jlesson/video/tts_engine.py`. The voice names follow a pattern: `{language}-{region}-{name}Neural`. For example `hu-HU-NoemiNeural` = Hungarian-Hungary-Noemi.

### "I get a Python error I don't understand"
Copy the **entire error message** (including the "Traceback" part) and paste it into Copilot Chat.

### "I want to undo my last change"
- **Undo in VS Code:** Ctrl+Z
- **Undo all changes since last commit:** `git checkout .`
- **See what you changed:** `git diff`
- **See a list of changed files:** `git status`

### "jlesson command not found"
Run: `pip install -e .[all]` — this reinstalls the tool after any changes.

---

## Key Files Reference

Here's a quick reference of every important file and what it does:

### Core Logic (what you'll change most)
| File | What it does |
|------|-------------|
| `jlesson/models.py` | Defines the data structures (NounItem, VerbItem, Sentence, etc.) |
| `jlesson/curriculum.py` | Grammar progression rules and lesson tracking |
| `jlesson/prompt_template.py` | Instructions sent to the AI for generating content |
| `jlesson/vocab_generator.py` | Generates vocabulary files via AI |

### Audio & Video (change voices and visual style)
| File | What it does |
|------|-------------|
| `jlesson/video/tts_engine.py` | Text-to-speech voice settings |
| `jlesson/video/cards.py` | Visual card rendering (text, fonts, layout) |
| `jlesson/video/builder.py` | Assembles cards + audio into MP4 video |
| `jlesson/config.py` | General configuration (fonts, paths) |

### Pipeline (probably no changes needed)
| File | What it does |
|------|-------------|
| `jlesson/lesson_pipeline.py` | Orchestrates the lesson generation process |
| `jlesson/llm_client.py` | Connects to the AI (LM Studio) |
| `jlesson/llm_cache.py` | Caches AI responses to save time |
| `jlesson/lesson_store.py` | Saves lesson output to disk |
| `jlesson/profiles.py` | Different lesson styles (passive video, flashcards) |

### Data
| File | What it does |
|------|-------------|
| `vocab/*.json` | Vocabulary for each theme (food, travel, etc.) |
| `curriculum/curriculum.json` | Tracks which lessons are completed |
| `output/` | Generated lessons (content, audio, cards, video) |

### Tests
| File | What it does |
|------|-------------|
| `tests/test_*.py` | One test file per module — run to check your changes |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────┐
│              DAILY COMMANDS                          │
├─────────────────────────────────────────────────────┤
│  conda activate py312          → activate Python    │
│  jlesson vocab list            → see vocab themes   │
│  jlesson curriculum show       → see progress       │
│  jlesson lesson next --theme X → generate lesson    │
│  jlesson lesson prompt X       → preview prompt     │
│  pytest tests/ -v              → run tests          │
├─────────────────────────────────────────────────────┤
│              GIT COMMANDS                           │
├─────────────────────────────────────────────────────┤
│  git status                    → see changes        │
│  git add -A                    → stage all changes  │
│  git commit -m "message"       → save changes       │
│  git push                      → upload to GitHub   │
│  git checkout .                → undo all changes   │
├─────────────────────────────────────────────────────┤
│              COPILOT TIPS                           │
├─────────────────────────────────────────────────────┤
│  Open file first → then ask in chat                 │
│  @workspace → search whole project                  │
│  Ctrl+Shift+I → open Copilot chat                   │
│  Be specific: say exactly what to change            │
│  Small steps: one change at a time                  │
│  Paste errors into chat for help                    │
└─────────────────────────────────────────────────────┘
```

---

*This guide was created to help adapt the Japanese Lesson Generator into an English lesson tool for Hungarian children. The project documentation in `docs/` has detailed technical background for every design decision made during development.*
