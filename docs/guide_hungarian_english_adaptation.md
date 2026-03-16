# Guide: Adding Hungarian-English Lessons to the Lesson Generator

**Audience:** Non-developer with agile experience, using GitHub Copilot in VS Code to make changes.

**Key principle:** We are **adding** Hungarian-English as a new language option. The existing Japanese lessons stay untouched and keep working. You're building a second lane on the highway, not ripping up the road.

---

## 📋 Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [The Big Picture — What "Adding a Language" Means](#the-big-picture)
3. [Your Setup Checklist](#your-setup-checklist)
4. [How to Talk to GitHub Copilot](#how-to-talk-to-github-copilot)
5. [The Adaptation Plan (Your Backlog)](#the-adaptation-plan-your-backlog)
6. [Sprint 1 — Language Config System](#sprint-1--language-config-system)
7. [Sprint 2 — Hungarian Vocabulary](#sprint-2--hungarian-vocabulary)
8. [Sprint 3 — English Grammar Curriculum](#sprint-3--english-grammar-curriculum)
9. [Sprint 4 — Hungarian-English LLM Prompts](#sprint-4--hungarian-english-llm-prompts)
10. [Sprint 5 — Voices & Cards for Hungarian](#sprint-5--voices--cards-for-hungarian)
11. [Sprint 6 — Wire Up the CLI](#sprint-6--wire-up-the-cli)
12. [Sprint 7 — Testing & First Lesson](#sprint-7--testing--first-lesson)
13. [Day-to-Day Workflow](#day-to-day-workflow)
14. [Troubleshooting](#troubleshooting)
15. [Key Files Reference](#key-files-reference)
16. [Quick Reference Card](#quick-reference-card)

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

**Currently it teaches Japanese to English speakers. You will add a second mode that teaches English to Hungarian-speaking children — without breaking the Japanese mode.**

---

## The Big Picture

### Why "add" instead of "replace"?

- The Japanese lessons already work and are tested — we don't want to break them
- The codebase has 400+ tests that verify the Japanese pipeline — breaking them means weeks of repair
- By adding a new option, you can develop and test the Hungarian mode independently
- Later, even more languages could be added the same way

### How it will work when you're done

```
# Japanese lessons still work exactly as before (default)
jlesson lesson next --theme food

# Hungarian-English lessons use the new --language flag
jlesson lesson next --theme food --language hun-eng
jlesson vocab create toys --language hun-eng
jlesson curriculum show --language hun-eng
```

### What are we actually building?

The project currently has language-specific logic **hardcoded** throughout many files (Japanese field names like `kanji`, `romaji`, Japanese grammar rules, Japanese voices, Japanese fonts). Instead of editing all those files to replace Japanese with Hungarian, we will:

1. **Create a "Language Config" system** — a central place that defines everything about a language (vocabulary fields, grammar rules, voices, fonts, prompts)
2. **Extract** the existing Japanese settings into one config
3. **Create** a second config for Hungarian-English
4. **Add a `--language` flag** to the CLI so you can choose which one to use

Think of it like a recipe book: the kitchen (pipeline) stays the same, but you can follow different recipes (language configs).

---

## Your Setup Checklist

Before you start, make sure these are working:

- [ ] **VS Code** is installed with the **GitHub Copilot** extension
- [ ] **Copilot Chat** panel is visible (click the chat icon in the sidebar, or press `Ctrl+Shift+I`)
- [ ] **Python** is installed (the project uses Python 3.12)
- [ ] **Conda environment** is activated — open a terminal in VS Code (`` Ctrl+` ``) and type:
  ```
  conda activate py312
  ```
- [ ] **LM Studio** is running on the network (this is the AI that generates lesson content)
- [ ] **The existing project runs** — test with:
  ```
  jlesson vocab list
  ```
  If this shows a list of themes, everything works.
- [ ] **Tests pass** — run once before you change anything to have a clean baseline:
  ```
  pytest tests/ -m "not integration and not internet and not video" -v
  ```

---

## How to Talk to GitHub Copilot

GitHub Copilot is your AI programming assistant. You tell it what to do **in plain English**, and it writes the code. Here's how to use it effectively:

### Opening Copilot Chat
- Press **Ctrl+Shift+I** to open the chat panel
- Or click the **Copilot icon** in the VS Code sidebar

### Golden Rules

1. **Always open the relevant file first.** Before asking Copilot to change something, click on the file in the Explorer panel so it's visible. Copilot works best when it can see the file you're talking about.

2. **Be specific.** Instead of "add Hungarian support", say:
   > "In this file, add a new HungarianNounItem class alongside the existing NounItem. It should have fields: english (str), hungarian (str), pronunciation (str)."

3. **Emphasize: keep existing code.** Always tell Copilot:
   > "Keep all existing Japanese code working. Add new code alongside it, don't replace."

4. **Work in small steps.** Don't ask for everything at once. Ask for one change, check it works, then ask for the next.

5. **Reference the existing docs.** This project has detailed documentation. Point Copilot to it:
   > "Read the file docs/decision_llm_integration.md and the file docs/guide_hungarian_english_adaptation.md, then help me create the language config for Hungarian."

6. **Ask Copilot to explain before changing.** When unsure:
   > "Explain what this file does before I change anything."

### Useful Copilot Prompts

| What you want | What to type in Copilot Chat |
|---|---|
| Understand a file | "Explain what `jlesson/curriculum.py` does in simple terms" |
| Add new code | "Add a HUN_TO_ENG_GRAMMAR_PROGRESSION list alongside the existing ENG_TO_JAP_GRAMMAR_PROGRESSION. Keep the Japanese one unchanged." |
| Run tests | "Run the tests to check if anything is broken" |
| Check your work | "Run just the Japanese tests to make sure I didn't break anything" |
| Fix an error | Copy-paste the error and ask "What does this error mean and how do I fix it?" |
| Create a new file | "Create a new vocabulary file `vocab/hungarian/colors.json` with 10 color nouns with fields english, hungarian, pronunciation" |
| Find something | "@workspace where are the Japanese-specific text-to-speech voice settings?" |

### The @workspace Command

When you type `@workspace` before your question, Copilot searches the entire project:
> "@workspace where is the code that handles grammar progression?"

This is very powerful — use it whenever you don't know where something is.

### Important Safety Prompt

Whenever you ask Copilot to make a change, **include this reminder:**
> "Important: keep all existing Japanese functionality working. Don't remove or rename any existing code. Add new code alongside it."

---

## The Adaptation Plan (Your Backlog)

Think of this as your Product Backlog. Each "Sprint" is a group of related changes. **Do them in order** — later sprints depend on earlier ones.

| Sprint | What Changes | Risk | Approach |
|--------|-------------|------|----------|
| 1 — Language Config | Create a central language configuration system | Medium | New file: `jlesson/language_config.py` |
| 2 — Vocabulary | Create Hungarian-English vocabulary files | Low | New folder: `vocab/hungarian/` + new vocab models |
| 3 — Grammar | Create English grammar progression for Hungarian learners | Medium | New constants alongside Japanese ones in `curriculum.py` |
| 4 — Prompts | Create Hungarian-English prompt templates | Medium | New prompt functions alongside Japanese ones |
| 5 — Voices & Cards | Add Hungarian TTS voices and card rendering | Low | Add to existing dicts in `tts_engine.py` and `cards.py` |
| 6 — CLI | Add `--language` flag to all commands | Medium | Modify `cli.py` to thread language choice through pipeline |
| 7 — Testing | Write Hungarian tests + verify Japanese still works | Low | New test files + run existing tests |

### Safety Rule for Every Sprint

After **every sprint**, run the existing tests:
```
pytest tests/ -m "not integration and not internet and not video" -v
```
**All existing tests must still pass.** If any fail, you broke something — fix it before continuing.

---

## Sprint 1 — Language Config System

**Goal:** Create a central "language configuration" object that holds all language-specific settings. This is the foundation for everything else.

### Why this first?

Right now, Japanese-specific settings are scattered across 8+ files. Instead of hunting through all of them, we create ONE place that says "here's everything about a language." Then the rest of the code can ask this config object instead of having hardcoded Japanese assumptions.

### Step 1.1 — Create the language config file

Tell Copilot:

> "Create a new file `jlesson/language_config.py`. It should define a `LanguageConfig` dataclass with these fields:
> - `code`: str — short identifier like 'eng-jap' or 'hun-eng'. The format is **native-target**: the first part is the learner's native language, the second is the language being learned. So 'hun-eng' means "Hungarian speaker learning English".
> - `display_name`: str — human-readable name like 'English-Japanese' or 'Hungarian-English'
> - `target_language`: str — the language being learned (e.g., 'Japanese' or 'English')
> - `native_language`: str — the learner's native language (e.g., 'English' or 'Hungarian')
> - `vocab_noun_fields`: list of required field names for noun vocabulary items
> - `vocab_verb_fields`: list of required field names for verb vocabulary items
> - `vocab_verb_types`: list of valid verb type classifications
> - `voices`: dict mapping voice roles to Edge TTS voice names
> - `target_font_path`: str — path to font for target language text
> - `native_font_path`: str — path to font for native language text
> - `grammar_progression`: list — the grammar points for this language (can be set later)
> - `persons`: list — pronouns used in sentence generation
> - `vocab_dir`: str — path to vocab folder. For Japanese this is `'vocab'` (the existing root folder), for Hungarian this is `'vocab/hungarian'`
> - `curriculum_file`: str — path to curriculum JSON for this language
>
> Then create two instances:
> `ENG_JAP_CONFIG` — filled in with the current Japanese settings (look at the existing code in models.py, curriculum.py, tts_engine.py, cards.py for the values)
> `HUN_ENG_CONFIG` — filled in with Hungarian-English settings
>
> Add a `get_language_config(code: str) -> LanguageConfig` function that returns the right config.
>
> Read the existing files to get the correct Japanese values. Don't guess — use what's already in the code."

### Step 1.2 — Verify the file was created correctly

Tell Copilot:
> "Open `jlesson/language_config.py` and verify that ENG_JAP_CONFIG matches the actual settings currently used in the codebase. Compare the voice names with `jlesson/video/tts_engine.py`, the font path with `jlesson/video/cards.py`, and the vocab fields with `jlesson/models.py`."

### Step 1.3 — Run tests (safety check)

```
pytest tests/ -m "not integration and not internet and not video" -v
```
This sprint only added a new file, so all existing tests should still pass.

**Git checkpoint:**
```
git add -A
git commit -m "Sprint 1: Add language config system"
git push
```

---

## Sprint 2 — Hungarian Vocabulary

**Goal:** Create Hungarian-English vocabulary files alongside the existing Japanese ones.

### Step 2.1 — Organize vocabulary by language

The existing vocab files (food.json, travel.json, etc.) contain Japanese data. We'll keep them and create a parallel set for Hungarian.

Tell Copilot:

> "Create a new folder structure for vocabulary organized by language. Move the current vocab/*.json files logic so that:
> - Japanese vocab stays at `vocab/` (to avoid breaking existing code)  
> - Hungarian vocab goes in a new folder `vocab/hungarian/`
> 
> Create these Hungarian vocabulary files in `vocab/hungarian/`:
> - `food.json` — 10 food nouns + 6 food verbs, each with fields: english, hungarian, pronunciation
> - `animals.json` — 10 animal nouns + 5 verbs, same fields
> - `family.json` — 8 family member nouns + 5 verbs about family activities
> - `colors.json` — 10 color nouns + 4 verbs about colors/appearance
>
> Each noun should look like: `{"english": "dog", "hungarian": "kutya", "pronunciation": "dɒɡ"}`
> Each verb should look like: `{"english": "to eat", "hungarian": "enni", "pronunciation": "tuː iːt", "past_tense": "ate"}`
>
> Make sure the Hungarian translations are accurate."

### Step 2.2 — Add Hungarian data models

Open `jlesson/models.py` and tell Copilot:

> "Add new Pydantic model classes for Hungarian-English alongside the existing Japanese ones. Keep all Japanese classes unchanged. Add:
> - `HungarianNounItem` with fields: english (str), hungarian (str), pronunciation (str)
> - `HungarianVerbItem` with fields: english (str), hungarian (str), pronunciation (str), past_tense (str)
> - `HungarianSentence` with fields: grammar_id (str), english (str), hungarian (str), person (str), notes (str)
>
> Don't touch NounItem, VerbItem, or Sentence — those are the Japanese classes and must stay exactly as they are."

### Step 2.3 — Update the vocabulary generator for Hungarian

Open `jlesson/vocab_generator.py` and tell Copilot:

> "Add Hungarian vocabulary generation support alongside the existing Japanese support. Keep all Japanese code unchanged. Add:
> - `_REQUIRED_HUN_NOUN_FIELDS` = {'english', 'hungarian', 'pronunciation'}
> - `_REQUIRED_HUN_VERB_FIELDS` = {'english', 'hungarian', 'pronunciation', 'past_tense'}
> - A `validate_hungarian_vocab_schema()` function similar to the existing `validate_vocab_schema()`, but checking Hungarian fields
> - A `build_hungarian_vocab_prompt()` function that asks the LLM to generate English-Hungarian vocabulary for children
>
> The existing `validate_vocab_schema()` and prompt functions must not be changed."

### Step 2.4 — Verify

```
jlesson vocab list
```
Japanese vocab should still show up. Then check that the new Hungarian files exist:
```
dir vocab\hungarian\
```

**Git checkpoint:**
```
git add -A
git commit -m "Sprint 2: Add Hungarian vocabulary files and models"
git push
```

---

## Sprint 3 — English Grammar Curriculum

**Goal:** Create an English grammar progression for Hungarian kids, alongside the existing Japanese grammar.

### Step 3.1 — Understand the current grammar system

Tell Copilot:
> "@workspace explain the grammar progression system in `jlesson/curriculum.py`. What is GRAMMAR_PROGRESSION and how is it structured? We will rename it to ENG_TO_JAP_GRAMMAR_PROGRESSION."

### Step 3.2 — Add English grammar progression

Open `jlesson/curriculum.py` and tell Copilot:

> "Rename the existing `GRAMMAR_PROGRESSION` to `ENG_TO_JAP_GRAMMAR_PROGRESSION`, then add a new `HUN_TO_ENG_GRAMMAR_PROGRESSION` list alongside it. Update all references to the old name so existing code keeps working.
>
> **Keep all existing Japanese grammar logic exactly as it is.**
>
> The new Hungarian-to-English grammar progression for Hungarian kids should have these grammar points organized by level:
>
> **Level 1** (beginner):
> - `present_simple_affirmative` — pattern: 'Subject + verb + object', example: 'I eat bread.'
> - `identity_is_am_are` — pattern: 'Subject + is/am/are + noun/adjective', example: 'She is a teacher.'
>
> **Level 2** (requires Level 1):
> - `present_simple_negative` — pattern: 'Subject + do/does not + verb', example: 'I do not eat fish.'
> - `present_simple_question` — pattern: 'Do/Does + subject + verb?', example: 'Do you like cats?'
> - `past_simple_affirmative` — pattern: 'Subject + past verb + object', example: 'I ate bread yesterday.'
>
> **Level 3** (requires Level 2):
> - `past_simple_negative` — pattern: 'Subject + did not + verb', example: 'I did not eat fish.'
> - `past_simple_question` — pattern: 'Did + subject + verb?', example: 'Did you run today?'
> - `can_ability` — pattern: 'Subject + can + verb', example: 'I can swim fast.'
>
> **Level 4** (requires Level 3):
> - `present_continuous` — pattern: 'Subject + is/am/are + verb-ing', example: 'I am eating now.'
> - `there_is_are` — pattern: 'There is/are + noun', example: 'There is a cat on the table.'
> - `have_got` — pattern: 'Subject + have/has got + noun', example: 'I have got a dog.'
>
> **Level 5** (requires Level 4):
> - `past_continuous` — pattern: 'Subject + was/were + verb-ing', example: 'I was eating when you called.'
> - `will_future` — pattern: 'Subject + will + verb', example: 'I will eat later.'
> - `going_to_future` — pattern: 'Subject + is/am/are going to + verb', example: 'I am going to eat lunch.'
>
> **Level 6** (requires Level 5):
> - `first_conditional` — pattern: 'If + present, subject + will + verb', example: 'If it rains, I will stay home.'
> - `must_should` — pattern: 'Subject + must/should + verb', example: 'You must study every day.'
> - `comparisons` — pattern: 'noun + is + adjective-er + than + noun', example: 'The dog is bigger than the cat.'
>
> Each grammar point needs: id, label, level, pattern, example, prerequisites (list of IDs from earlier levels).
>
> The naming convention is **direction-based**: `ENG_TO_JAP` = English speaker learning Japanese, `HUN_TO_ENG` = Hungarian speaker learning English. This makes it instantly clear what each progression teaches."

### Step 3.3 — Create a Hungarian curriculum file

Tell Copilot:

> "Create a new file `curriculum/curriculum_hungarian.json` with fresh/empty state:
> ```json
> {
>   "language": "hungarian",
>   "lessons": [],
>   "covered_grammar_ids": [],
>   "covered_nouns": [],
>   "covered_verbs": []
> }
> ```
>
> Don't change the existing `curriculum/curriculum.json` — that's for Japanese."

### Step 3.4 — Run tests

```
pytest tests/ -m "not integration and not internet and not video" -v
```
All existing tests must still pass.

**Git checkpoint:**
```
git add -A
git commit -m "Sprint 3: Add English grammar progression for Hungarian"
git push
```

---

## Sprint 4 — Hungarian-English LLM Prompts

**Goal:** Create prompt templates that tell the AI how to generate English lessons for Hungarian kids.

### Step 4.1 — Understand the current prompts

Open `jlesson/prompt_template.py` and tell Copilot:
> "Explain each function in this file. Which ones generate Japanese-specific content?"

There are about 8 prompt-building functions. All of them are Japanese-specific.

### Step 4.2 — Add Hungarian prompt functions

This is the biggest sprint. Tell Copilot:

> "Add new Hungarian-English prompt functions alongside the existing Japanese ones. **Keep all existing functions unchanged.** Prefix each new function with `hungarian_`.
>
> Create these functions:
>
> 1. `hungarian_build_lesson_prompt()` — main lesson prompt that asks the LLM to generate English lesson content for Hungarian-speaking children (ages 8-12). The target language is English, explanations should be in Hungarian. No kanji or romaji — instead use simple English pronunciation guides.
>
> 2. `hungarian_build_vocab_prompt()` — asks the LLM to generate vocabulary with fields: english, hungarian, pronunciation. For verbs also: past_tense.
>
> 3. `hungarian_build_noun_practice_prompt()` — asks the LLM to create memory tips that help Hungarian kids remember English nouns. Tips should reference Hungarian words or concepts the child would know.
>
> 4. `hungarian_build_verb_practice_prompt()` — similar but for verbs. Should explain English past tense and irregular forms in kid-friendly ways.
>
> 5. `hungarian_build_grammar_select_prompt()` — asks the LLM to pick appropriate grammar points from the Hungarian grammar progression.
>
> 6. `hungarian_build_grammar_generate_prompt()` — asks the LLM to generate English practice sentences using the selected grammar patterns, with Hungarian translations.
>
> 7. `hungarian_build_sentence_review_prompt()` — asks the LLM to review generated sentences for correctness and age-appropriateness.
>
> Also add:
> - `HUNGARIAN_PERSONS` — English pronouns with Hungarian translations: [('I', 'én', 'aɪ'), ('You', 'te', 'juː'), ('He', 'ő (fiú)', 'hiː'), ('She', 'ő (lány)', 'ʃiː'), ('We', 'mi', 'wiː'), ('They', 'ők', 'ðeɪ')]. This is the single source of truth for pronouns in the Hungarian mode — the grammar functions in Sprint 3 and prompt functions here should both use this list.
> - `HUNGARIAN_GRAMMAR_PATTERNS` — basic English sentence patterns
>
> All content and instructions in prompts should be designed for 8-12 year old Hungarian children learning English.
>
> IMPORTANT: Don't touch any existing function. The existing Japanese prompt functions must not change."

### Step 4.3 — Test a prompt

After the functions are created, run:
```
python -c "from jlesson.prompt_template import hungarian_build_vocab_prompt; print(hungarian_build_vocab_prompt('food', 10, 6))"
```
Read the output to check it makes sense — it should ask for English-Hungarian vocabulary.

### Step 4.4 — Run tests

```
pytest tests/ -m "not integration and not internet and not video" -v
```

**Git checkpoint:**
```
git add -A
git commit -m "Sprint 4: Add Hungarian-English LLM prompt templates"
git push
```

---

## Sprint 5 — Voices & Cards for Hungarian

**Goal:** Add Hungarian TTS voices and card rendering support.

### Step 5.1 — Add Hungarian voices

Open `jlesson/video/tts_engine.py` and tell Copilot:

> "Add Hungarian voice entries to the VOICES dictionary. **Keep all existing Japanese and English voices.** Add:
> - `'hungarian_female': 'hu-HU-NoemiNeural'`
> - `'hungarian_male': 'hu-HU-TamasNeural'`
>
> Don't remove or change any existing voice entries."

### Step 5.2 — Add Hungarian card rendering support

Open `jlesson/video/cards.py` and tell Copilot:

> "Add Hungarian-English card rendering methods alongside the existing Japanese ones. **Keep all existing Japanese rendering methods unchanged.**
>
> Add new methods (or a parallel card renderer class) for Hungarian-English cards:
> - Cards should show English text prominently (since English is the target language)
> - Hungarian translation shown below in smaller text
> - Pronunciation guide shown in a different color
> - Use Segoe UI font for both languages (both use Latin alphabet — no need for Japanese fonts)
>
> The card size should be the same 1920x1080. Keep the same visual style (colors, background) as the Japanese cards, just different text layout.
>
> Don't modify any existing rendering methods."

### Step 5.3 — Run tests

```
pytest tests/ -m "not integration and not internet and not video" -v
```

**Git checkpoint:**
```
git add -A
git commit -m "Sprint 5: Add Hungarian voices and card rendering"
git push
```

---

## Sprint 6 — Wire Up the CLI

**Goal:** Add a `--language` flag so users can choose Japanese or Hungarian.

### Step 6.1 — Add language option to CLI commands

Open `jlesson/cli.py` and tell Copilot:

> "Add a `--language` option to the CLI commands. The option should accept 'eng-jap' (default) or 'hun-eng'. Add it to:
> - `lesson next` command
> - `lesson prompt` command
> - `vocab list` command
> - `vocab create` command
> - `vocab generate-prompt` command
> - `curriculum show` command
>
> When `--language eng-jap` (or no flag), everything works exactly as before — this is critical.
> When `--language hun-eng`, the command uses:
> - Hungarian vocabulary from `vocab/hungarian/`
> - Hungarian grammar progression
> - Hungarian prompt templates (the `hungarian_*` functions)
> - Hungarian curriculum file: `curriculum/curriculum_hungarian.json`
> - Hungarian voices and card rendering
>
> Read `jlesson/language_config.py` to see how to get the right config based on the language code.
> Read the existing CLI code carefully to understand how commands pass configuration to the pipeline."

### Step 6.2 — Thread language through the pipeline

Open `jlesson/lesson_pipeline.py` and tell Copilot:

> "Add a `language` field to `LessonConfig` (default: 'eng-jap'). When the pipeline runs, it should:
> - Use the language config from `jlesson/language_config.py` to get language-specific settings
> - Pass the right prompt functions, grammar progression, and voices based on the language
> - Save output to `output/` as before, but Hungarian lessons could use a subfolder like `output/hungarian/lesson_001/`
>
> **Critical:** When language is 'eng-jap' or not specified, everything must work exactly as before. Don't change the behavior of any existing Japanese pipeline step.
>
> Read `jlesson/language_config.py` to understand the language config system."

### Step 6.3 — Test both modes

```
# Japanese should still work exactly as before
jlesson lesson prompt food

# Hungarian should use the new prompts
jlesson lesson prompt food --language hun-eng
```

Compare the outputs — Japanese should show kanji/romaji references, Hungarian should show Hungarian translations.

### Step 6.4 — Run tests

```
pytest tests/ -m "not integration and not internet and not video" -v
```

**Git checkpoint:**
```
git add -A
git commit -m "Sprint 6: Add --language CLI flag and pipeline integration"
git push
```

---

## Sprint 7 — Testing & First Lesson

### Step 7.1 — Verify Japanese still works

This is **the most important check**. Run:
```
pytest tests/ -m "not integration and not internet and not video" -v
```
Every single existing test must pass. If any fail, fix them before continuing.

### Step 7.2 — Write Hungarian-specific tests

Tell Copilot:

> "Create a new test file `tests/test_hungarian.py` that tests:
> 1. HungarianNounItem and HungarianVerbItem can be created with correct fields
> 2. Hungarian vocabulary files in `vocab/hungarian/` are valid JSON with correct fields
> 3. Hungarian prompt functions return non-empty strings
> 4. HUN_TO_ENG_GRAMMAR_PROGRESSION has valid structure (ids, levels, prerequisites)
> 5. Hungarian language config has all required fields
>
> Model the tests after the existing test files. Use `@pytest.mark.unit` marker."

Run the new tests:
```
pytest tests/test_hungarian.py -v
```

### Step 7.3 — Generate your first Hungarian-English lesson!

```
jlesson lesson next --theme food --language hun-eng
```

Check the output:
- `content.json` — does it have English words with Hungarian translations?
- `report.md` — does the report make sense for a Hungarian child?
- Audio files — listen to them. Are they in the right languages?
- Video (if generated) — does it look right?

### Step 7.4 — Also verify Japanese still generates correctly

```
jlesson lesson next --theme food
```
This should produce a Japanese lesson exactly as before.

**Git checkpoint:**
```
git add -A
git commit -m "Sprint 7: Hungarian tests pass, first lesson generated"
git push
```

---

## Day-to-Day Workflow

### Before making changes
1. Open VS Code terminal (`` Ctrl+` ``)
2. Make sure you're in the right folder: `cd c:\01_dev\japanese`
3. Activate your environment: `conda activate py312`

### Making a change
1. **Open the file** you want to change in VS Code
2. **Open Copilot Chat** (Ctrl+Shift+I)
3. **Always remind Copilot:** "Keep all existing Japanese code working"
4. **Tell Copilot what to add** — be specific, reference the file
5. **Review the suggestion** — Copilot will show you what it wants to change
6. **Click "Apply"** or "Accept" to make the change
7. **Save the file** (Ctrl+S)

### After making changes
1. **Run ALL tests** to verify nothing is broken:
   ```
   pytest tests/ -m "not integration and not internet and not video" -v
   ```
2. **Check the test count** — the number of passing tests should only go UP (new tests added), never DOWN (existing tests broken)
3. **Save your work to Git:**
   ```
   git add -A
   git commit -m "Brief description of what you changed"
   git push
   ```

### When something breaks
1. **Don't panic** — Git saves all your previous work
2. **Copy the error message** from the terminal
3. **Paste it into Copilot Chat** and ask: "What does this error mean and how do I fix it? Remember, we must not break any existing Japanese functionality."
4. **If you want to undo everything** back to the last commit:
   ```
   git checkout .
   ```
   (This discards all changes since your last `git commit`)

### Testing Hungarian vs. Japanese

Always test **both** languages after any change:
```
# Quick Japanese check (should still work)
jlesson lesson prompt food

# Quick Hungarian check (your new feature)
jlesson lesson prompt food --language hun-eng
```

### Reading the project documentation

This project has detailed docs about every design decision:

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
> "Read docs/decision_tts_engine.md and then help me add Hungarian voices alongside the Japanese ones"

---

## Troubleshooting

### "I don't know which file to change"
Ask Copilot: `@workspace where is the code that handles [describe what you're looking for]?`

### "An existing Japanese test is failing!"
**Stop and fix this first.** This means you accidentally changed something you shouldn't have. Tell Copilot:
> "This existing test was passing before my changes and now it fails. I need to fix it WITHOUT changing the test — the code I added must be wrong. Help me find what I broke."

### "My new Hungarian code doesn't work"
Tell Copilot which file and what's wrong. Include the exact error:
> "My new `hungarian_build_vocab_prompt()` function in `prompt_template.py` is returning an error: [paste error]. All existing Japanese functions still work fine."

### "The AI generates wrong content for Hungarian"
The AI instructions are in the `hungarian_*` functions in `jlesson/prompt_template.py`. Open it and refine the prompts:
> "The AI is generating [describe problem] for Hungarian lessons. Update the `hungarian_build_noun_practice_prompt` to be more specific about [what you want]. Don't change any non-Hungarian functions."

### "Audio sounds wrong or uses the wrong language"
Check `jlesson/video/tts_engine.py`. Voice names follow a pattern: `{language}-{region}-{name}Neural`:
- `hu-HU-NoemiNeural` = Hungarian-Hungary-Noemi
- `en-US-AriaNeural` = English-US-Aria
- `ja-JP-NanamiNeural` = Japanese-Japan-Nanami

### "I get a Python error I don't understand"
Copy the **entire error message** (including the "Traceback" part) and paste it into Copilot Chat.

### "I want to undo my last change"
- **Undo in VS Code:** Ctrl+Z (for the current file)
- **Undo all changes since last commit:** `git checkout .`
- **See what you changed:** `git diff`
- **See a list of changed files:** `git status`

### "jlesson command not found"
Run: `pip install -e .[all]` — this reinstalls the tool after any changes to the code.

### "How do I know if I broke something?"
Run the full test suite and compare the numbers:
```
pytest tests/ -m "not integration and not internet and not video" -v
```
Your baseline pass count (before any changes) should never go down.

---

## Key Files Reference

### What stays the same (DO NOT modify these for Hungarian changes)
| File | What it does | Why you don't touch it |
|------|-------------|----------------------|
| `jlesson/lesson_store.py` | Saves lesson output to disk | Language-agnostic |
| `jlesson/llm_cache.py` | Caches AI responses | Language-agnostic |
| `jlesson/llm_client.py` | Connects to LM Studio AI | Language-agnostic |
| `jlesson/profiles.py` | Lesson styles (passive video, flashcards) | Language-agnostic |

### What you ADD to (keep existing code, add alongside)
| File | What to add |
|------|------------|
| `jlesson/models.py` | `HungarianNounItem`, `HungarianVerbItem`, `HungarianSentence` classes |
| `jlesson/curriculum.py` | `HUN_TO_ENG_GRAMMAR_PROGRESSION`, `HUNGARIAN_PERSONS` |
| `jlesson/prompt_template.py` | `hungarian_build_*()` prompt functions |
| `jlesson/vocab_generator.py` | Hungarian validation + prompt functions |
| `jlesson/video/tts_engine.py` | Hungarian voice entries in VOICES dict |
| `jlesson/video/cards.py` | Hungarian card rendering methods |
| `jlesson/cli.py` | `--language` flag on commands |
| `jlesson/lesson_pipeline.py` | `language` field in LessonConfig + language routing |

### What you CREATE new
| File | Purpose |
|------|---------|
| `jlesson/language_config.py` | Central language configuration system |
| `vocab/hungarian/*.json` | Hungarian-English vocabulary files |
| `curriculum/curriculum_hungarian.json` | Hungarian lesson progress tracker |
| `tests/test_hungarian.py` | Tests for Hungarian-specific code |

### Existing data (Japanese — don't change)
| File | What it does |
|------|-------------|
| `vocab/*.json` | Japanese vocabulary (food, travel, etc.) |
| `curriculum/curriculum.json` | Japanese lesson progress |
| `output/` | Generated lessons |
| `tests/test_*.py` | Existing tests (must keep passing) |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│              DAILY COMMANDS                                  │
├─────────────────────────────────────────────────────────────┤
│  conda activate py312                → activate Python      │
│  jlesson vocab list                  → Japanese vocab       │
│  jlesson vocab list --language hun-eng → Hungarian vocab    │
│  jlesson curriculum show               → Japanese progress  │
│  jlesson curriculum show --lang hun-eng → Hungarian progress│
│  jlesson lesson next --theme food      → Japanese lesson    │
│  jlesson lesson next --theme food      │                    │
│    --language hun-eng                  → Hungarian lesson   │
│  jlesson lesson prompt food            → preview JP prompt  │
│  jlesson lesson prompt food            │                    │
│    --language hun-eng                  → preview HU prompt  │
│  pytest tests/ -v                    → run ALL tests        │
│  pytest tests/test_hungarian.py -v   → run HU tests only   │
├─────────────────────────────────────────────────────────────┤
│              GIT COMMANDS                                   │
├─────────────────────────────────────────────────────────────┤
│  git status                    → see changes                │
│  git add -A                    → stage all changes          │
│  git commit -m "message"       → save changes               │
│  git push                      → upload to GitHub           │
│  git checkout .                → undo all changes           │
├─────────────────────────────────────────────────────────────┤
│              COPILOT TIPS                                   │
├─────────────────────────────────────────────────────────────┤
│  Open file first → then ask in chat                         │
│  @workspace → search whole project                          │
│  Ctrl+Shift+I → open Copilot chat                           │
│  Always say: "Keep existing Japanese code working"          │
│  Be specific: say exactly what to ADD                       │
│  Small steps: one change at a time                          │
│  Paste errors into chat for help                            │
│  Run tests after EVERY change                               │
└─────────────────────────────────────────────────────────────┘
```

---

*This guide was created to help **add** Hungarian-English lesson support to the existing Japanese Lesson Generator. The Japanese functionality remains fully intact. The project documentation in `docs/` has detailed technical background for every design decision made during development.*
