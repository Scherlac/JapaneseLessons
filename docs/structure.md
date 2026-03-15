# Japanese Learning Material — Structure

## Problem Statement

1. **Isolated focus**: Most training materials cover only one area — just vocabulary *or* just grammar — never combining them in a single lesson flow.
2. **Low repetition count**: Typical materials repeat a word only briefly (e.g. English → Japanese → Japanese) which is insufficient for retention.

## Design Principles

- **Integrated lessons**: Each unit combines vocabulary *and* grammar so the learner sees words in context immediately.
- **High repetition**: Every item is repeated multiple times across different phases (introduction, recall, usage in sentences).
- **Progressive build-up**: Nouns → Verbs → Grammar (using the learned nouns and verbs).

---

## Unit Structure

### Phase 1 — Nouns (6 items)

| # | English | Japanese (Kana) | Romaji |
|---|---------|-----------------|--------|
| 1 |         |                 |        |
| 2 |         |                 |        |
| 3 |         |                 |        |
| 4 |         |                 |        |
| 5 |         |                 |        |
| 6 |         |                 |        |

**Repetition cycle per noun:**

1. English → Japanese (introduce)
2. Japanese → English (recall)
3. English → Japanese (reinforce)
4. Japanese → Japanese (self-confirm)
5. English → Japanese (final lock-in)

→ **5 touches per noun, 30 total for the noun phase.**

### Phase 2 — Verbs (6 items)

| # | English | Japanese (Kana) | Romaji |
|---|---------|-----------------|--------|
| 1 |         |                 |        |
| 2 |         |                 |        |
| 3 |         |                 |        |
| 4 |         |                 |        |
| 5 |         |                 |        |
| 6 |         |                 |        |

Same repetition cycle as nouns → **30 touches.**

### Phase 3 — Grammar (3 sentence patterns × 3 declinations)

Each grammar pattern is practised with three persons:

| Person    | Japanese marker | Example pronoun |
|-----------|-----------------|-----------------|
| I (me)    | 私は (watashi wa) | 私             |
| You       | あなたは (anata wa) | あなた         |
| He / She  | 彼は / 彼女は (kare wa / kanojo wa) | 彼 / 彼女 |

**3 grammar patterns**, each declined across **me / you / he-she** = **9 sentences**.

Each sentence reuses nouns and verbs from Phases 1 & 2, giving additional repetition of the vocabulary in context.

**Repetition cycle per sentence:**

1. English → Japanese (translate)
2. Japanese → English (comprehend)
3. English → Japanese (reinforce)

→ **3 touches × 9 sentences = 27 touches.**

---

## Summary per Unit

| Phase          | Items | Repetitions each | Total touches |
|----------------|-------|-------------------|---------------|
| Nouns          | 6     | 5                 | 30            |
| Verbs          | 6     | 5                 | 30            |
| Grammar        | 9     | 3                 | 27            |
| **Total**      |       |                   | **87**        |

---

## Touch System

The sections above describe *what* is learned and *how many* repetitions occur.
This section formalises *what each touch actually contains* — what the learner
sees, hears, and does — and how a **rulebook** compiles raw lesson items into a
complete, renderable touch sequence.

### Terminology

| Term | Definition |
|------|------------|
| **Item** | A single learning unit: a noun, a verb, or a grammar sentence. |
| **Touch** | One learner interaction with an item. Each touch presents the item in a specific way. |
| **Touch type** | Mechanical specification of a touch: what is shown, what audio plays, in what order. |
| **Repetition cycle** | An ordered list of touch types applied to every item in a phase. |
| **Profile** | A named rulebook variant that targets a specific use case (e.g. passive video, active flash cards). Different profiles reuse the same items but define different touch types and repetition cycles. |
| **Rulebook** | The complete mapping for one profile: phase → repetition cycle → required assets per touch. Given a lesson's items, the rulebook produces the full touch sequence and asset manifest. |

### Touch Anatomy

A touch is a timed sequence of **stages** within one video clip.
Different touch types have different numbers of stages:

| Stage | Purpose | Typical content |
|-------|---------|-----------------|
| **Prompt** | Challenge or introduction | Text card, audio, or both |
| **Pause** | Thinking time (optional) | Same card, silence |
| **Reveal** | Answer or confirmation | New card, audio, or both |

Not every touch needs all three stages. A passive-listening touch may have
no pause and no distinct reveal — just sequential audio over a card.

### Touch Type Catalogue

All available touch types across all profiles. Each profile selects a subset.

#### Card-based (visual prompt → visual reveal)

| ID | Prompt | Reveal | Prompt audio | Reveal audio | Pause | Learner action |
|----|--------|--------|:------------:|:------------:|:-----:|----------------|
| `en→jp` | English text | JP text + reading | — | 🔊 JP female | ✓ | Produce Japanese from English |
| `jp→en` | JP text | English text | 🔊 JP female | — | ✓ | Recognise meaning from Japanese |
| `jp→jp` | JP text | JP text (same) | — | 🔊 JP female | ✓ | Self-confirm pronunciation |

#### Listen-first (audio-led, passive-friendly)

| ID | Card shown | Audio sequence | Pause | Learner action |
|----|------------|----------------|:-----:|----------------|
| `listen:en,jp-m,jp-f` | EN + JP text | 🔊 EN → 🔊 JP male → 🔊 JP female | — | Listen & absorb |
| `listen:jp-f,jp-m` | JP text | 🔊 JP female → 🔊 JP male | — | Hear two speakers |
| `listen:en,jp-f` | EN + JP text | 🔊 EN → 🔊 JP female | — | Map English to Japanese |

### Assets per Touch Type

| Touch type | Cards needed | EN voice | JP female | JP male |
|------------|-------------|:--------:|:---------:|:-------:|
| `en→jp` | EN card, JP card | — | ✓ | — |
| `jp→en` | JP card, EN card | — | ✓ | — |
| `jp→jp` | JP card | — | ✓ | — |
| `listen:en,jp-m,jp-f` | EN+JP card | ✓ | ✓ | ✓ |
| `listen:jp-f,jp-m` | JP card | — | ✓ | ✓ |
| `listen:en,jp-f` | EN+JP card | ✓ | ✓ | — |

**Unique assets per item** (de-duplicated — assets are rendered once and reused):

| Asset | Description |
|-------|-------------|
| Card: EN | English word or sentence |
| Card: JP | Japanese text + reading |
| Card: EN+JP | Bilingual card (both languages) |
| Audio: EN | English TTS |
| Audio: JP female | Japanese TTS (female voice) |
| Audio: JP male | Japanese TTS (male voice) |

→ Up to **6 unique assets per item**. The asset manifest depends on which
  touch types appear in the profile's repetition cycles.

---

### Profile: Passive Video

**Use case:** The learner watches a video. No interaction, no pauses.
English-speaking learner acquiring Japanese through repeated audio exposure.

**Touch pattern per item:** hear the English word/sentence, then hear it
in Japanese twice — male and female — while seeing both languages on screen.

#### Repetition Cycle — Nouns & Verbs (3 touches)

| # | Touch type | Intent | What the learner experiences |
|---|-----------|--------|------------------------------|
| 1 | `listen:en,jp-m,jp-f` | introduce | Hear English, then Japanese (male), then Japanese (female). See bilingual card. |
| 2 | `listen:jp-f,jp-m` | reinforce | Hear Japanese only — female then male. See JP card. |
| 3 | `listen:en,jp-m,jp-f` | lock-in | Full cycle again: English → JP male → JP female. |

#### Repetition Cycle — Grammar Sentences (2 touches)

| # | Touch type | Intent | What the learner experiences |
|---|-----------|--------|------------------------------|
| 1 | `listen:en,jp-m,jp-f` | translate | Hear the English sentence, then both JP voices. |
| 2 | `listen:en,jp-f` | reinforce | Hear English → JP female only (faster pacing). |

#### Compilation Example (Passive Video)

2 nouns + 2 grammar sentences:

```
Phase 1 — Nouns
  noun₁  touch 1  listen:en,jp-m,jp-f  introduce
  noun₂  touch 1  listen:en,jp-m,jp-f  introduce
  noun₁  touch 2  listen:jp-f,jp-m     reinforce
  noun₂  touch 2  listen:jp-f,jp-m     reinforce
  noun₁  touch 3  listen:en,jp-m,jp-f  lock-in
  noun₂  touch 3  listen:en,jp-m,jp-f  lock-in
Phase 3 — Grammar
  sent₁  touch 1  listen:en,jp-m,jp-f  translate
  sent₂  touch 1  listen:en,jp-m,jp-f  translate
  sent₁  touch 2  listen:en,jp-f       reinforce
  sent₂  touch 2  listen:en,jp-f       reinforce
```

**10 touches**, **4 items**.

| Asset | Count |
|-------|-------|
| EN+JP bilingual cards | 4 |
| JP-only cards | 2 (nouns only, touch 2) |
| EN TTS audio | 4 |
| JP female TTS audio | 4 |
| JP male TTS audio | 4 |
| **Total unique assets** | **18** |
| **Total rendered clips** | **10** |

---

### Profile: Active Flash Cards

**Use case:** The learner actively engages — sees a prompt, pauses to think,
then the reveal appears. Current default for the video pipeline.

#### Repetition Cycle — Nouns & Verbs (5 touches)

| # | Touch type | Intent | What happens |
|---|-----------|--------|--------------|
| 1 | `en→jp` | introduce | First exposure: see English, learn Japanese |
| 2 | `jp→en` | recall | See Japanese, remember the English meaning |
| 3 | `en→jp` | reinforce | Produce Japanese again from English |
| 4 | `jp→jp` | confirm | See Japanese, hear Japanese, self-check pronunciation |
| 5 | `en→jp` | lock-in | Final production from English |

#### Repetition Cycle — Grammar Sentences (3 touches)

| # | Touch type | Intent | What happens |
|---|-----------|--------|--------------|
| 1 | `en→jp` | translate | Produce the full Japanese sentence |
| 2 | `jp→en` | comprehend | Understand the Japanese sentence |
| 3 | `en→jp` | reinforce | Produce Japanese one more time |

#### Compilation Example (Active Flash Cards)

2 nouns + 2 grammar sentences:

```
Phase 1 — Nouns
  noun₁  touch 1  en→jp  introduce
  noun₂  touch 1  en→jp  introduce
  noun₁  touch 2  jp→en  recall
  noun₂  touch 2  jp→en  recall
  noun₁  touch 3  en→jp  reinforce
  noun₂  touch 3  en→jp  reinforce
  noun₁  touch 4  jp→jp  confirm
  noun₂  touch 4  jp→jp  confirm
  noun₁  touch 5  en→jp  lock-in
  noun₂  touch 5  en→jp  lock-in
Phase 3 — Grammar
  sent₁  touch 1  en→jp  translate
  sent₂  touch 1  en→jp  translate
  sent₁  touch 2  jp→en  comprehend
  sent₂  touch 2  jp→en  comprehend
  sent₁  touch 3  en→jp  reinforce
  sent₂  touch 3  en→jp  reinforce
```

**16 touches**, **4 items**.

| Asset | Count |
|-------|-------|
| EN cards | 4 |
| JP cards | 4 |
| JP female TTS audio | 4 |
| **Total unique assets** | **12** |
| **Total rendered clips** | **16** |

---

### Summary per Unit by Profile

| Profile | Noun touches | Verb touches | Grammar touches | Total (6n + 6v + 9g) |
|---------|:-----------:|:-----------:|:---------------:|:---------------------:|
| **Passive Video** | 3 | 3 | 2 | 18 + 18 + 18 = **54** |
| **Active Flash Cards** | 5 | 5 | 3 | 30 + 30 + 27 = **87** |

### Extensibility

New profiles and touch types can be added independently:

**Adding a touch type:**
1. Define it in the Touch Type Catalogue (columns: what's shown, what's heard).
2. Add a card renderer for any new card layout.
3. Add TTS generation for any new voice/language.

**Adding a profile:**
1. Name the use case and target learner.
2. Pick touch types from the catalogue (or define new ones).
3. Define a repetition cycle per phase.
4. The compilation logic and asset pipeline remain unchanged.

---

## Common Japanese Grammar Structures — Overview

Japanese grammar follows a **Subject–Object–Verb (SOV)** word order and relies heavily on **particles** (small words after nouns) to mark grammatical roles. Verbs come at the end and conjugate for tense, politeness, and negation.

### 1. Basic Sentence: A は B です (A wa B desu)

> "A is B."

| Person | Japanese | English |
|--------|----------|---------|
| I      | 私は学生です (watashi wa gakusei desu) | I am a student. |
| You    | あなたは先生です (anata wa sensei desu) | You are a teacher. |
| He     | 彼は日本人です (kare wa nihonjin desu) | He is Japanese. |

- **は (wa)** — topic marker ("as for A …")
- **です (desu)** — polite copula ("is/am/are")

### 2. Existence: A に B が あります / います (A ni B ga arimasu / imasu)

> "There is B in/at A."

- **あります (arimasu)** — for inanimate objects
- **います (imasu)** — for living things
- **に (ni)** — location particle ("in/at")
- **が (ga)** — subject marker

| Example | Japanese | English |
|---------|----------|---------|
| Object  | テーブルに本があります (tēburu ni hon ga arimasu) | There is a book on the table. |
| Person  | 部屋に猫がいます (heya ni neko ga imasu) | There is a cat in the room. |

### 3. Action: A は B を V ます (A wa B o V-masu)

> "A does [verb] B."

| Person | Japanese | English |
|--------|----------|---------|
| I      | 私は水を飲みます (watashi wa mizu o nomimasu) | I drink water. |
| You    | あなたはパンを食べます (anata wa pan o tabemasu) | You eat bread. |
| She    | 彼女は本を読みます (kanojo wa hon o yomimasu) | She reads a book. |

- **を (o)** — object marker ("B" is what receives the action)
- **ます (masu)** — polite verb ending (present/future tense)

### 4. Destination / Direction: A は B へ/に 行きます (A wa B e/ni ikimasu)

> "A goes to B."

| Person | Japanese | English |
|--------|----------|---------|
| I      | 私は学校に行きます (watashi wa gakkō ni ikimasu) | I go to school. |
| You    | あなたは日本へ行きます (anata wa nihon e ikimasu) | You go to Japan. |
| He     | 彼は店に行きます (kare wa mise ni ikimasu) | He goes to the shop. |

- **へ (e)** / **に (ni)** — direction/destination particle ("to")

### 5. Desire: A は B が ほしいです / V たいです

> "A wants B." / "A wants to [verb]."

| Form | Japanese | English |
|------|----------|---------|
| Noun (want thing) | 私は車がほしいです (watashi wa kuruma ga hoshii desu) | I want a car. |
| Verb (want to do) | 私は食べたいです (watashi wa tabetai desu) | I want to eat. |

- **ほしい (hoshii)** — "want" (for objects)
- **〜たい (tai)** — "want to …" (attached to verb stem)

### 6. Past Tense: V ました / A でした

> Polite past of verbs and copula.

| Present | Past | English |
|---------|------|---------|
| 食べます (tabemasu) | 食べました (tabemashita) | ate |
| 飲みます (nomimasu) | 飲みました (nomimashita) | drank |
| です (desu) | でした (deshita) | was/were |

### 7. Negation: V ません / A ではありません

> Polite negative forms.

| Positive | Negative | English |
|----------|----------|---------|
| 食べます | 食べません (tabemasen) | do not eat |
| 飲みます | 飲みません (nomimasen) | do not drink |
| 学生です | 学生ではありません (gakusei dewa arimasen) | am not a student |

### 8. Adjectives: い-adjectives & な-adjectives

| Type | Example | Sentence | English |
|------|---------|----------|---------|
| い-adj | 大きい (ōkii) | 大きい犬です (ōkii inu desu) | It is a big dog. |
| な-adj | 静か (shizuka) | 静かな部屋です (shizuka na heya desu) | It is a quiet room. |

- い-adjectives end in い and conjugate directly.
- な-adjectives need **な** before a noun.

### 9. Questions: 〜か (ka)

> Add **か** at the end to make any sentence a question.

| Statement | Question | English |
|-----------|----------|---------|
| 日本人です | 日本人ですか (nihonjin desu ka) | Are you Japanese? |
| 食べます | 食べますか (tabemasu ka) | Do you eat? |

### 10. Giving Reason: 〜から (kara)

> "Because …"

| Japanese | English |
|----------|---------|
| 暑いですから、水を飲みます (atsui desu kara, mizu o nomimasu) | Because it is hot, I drink water. |

---

### Key Particles — Quick Reference

| Particle | Role | Example |
|----------|------|---------|
| は (wa)  | Topic marker | 私**は**学生です |
| が (ga)  | Subject marker | 猫**が**います |
| を (o)   | Object marker | 水**を**飲みます |
| に (ni)  | Location / time / direction | 学校**に**行きます |
| へ (e)   | Direction | 日本**へ**行きます |
| で (de)  | Location of action / means | 学校**で**勉強します |
| の (no)  | Possession | 私**の**本 (my book) |
| か (ka)  | Question | 学生です**か** |
| から (kara) | From / because | 東京**から**来ました |
| まで (made) | Until / to | 駅**まで**歩きます |

---

## Dimensions of Japanese Grammar

Every Japanese sentence can be described by its position along several independent **dimensions** (axes). Each dimension has a finite set of values. Combining them creates the full space of possible sentence forms.

### Dimension Map

| #  | Dimension         | Values                                                                                         | Count |
|----|-------------------|-----------------------------------------------------------------------------------------------|-------|
| 1  | **Person**        | I (私), you (あなた), he (彼), she (彼女), it, we (私たち), you pl. (あなたたち), they (彼ら)   | 7     |
| 2  | **Tense**         | Present/Future (〜ます), Past (〜ました)                                                       | 2     |
| 3  | **Polarity**      | Affirmative (〜ます), Negative (〜ません)                                                      | 2     |
| 4  | **Politeness**    | Casual (食べる), Polite (食べます), Honorific/Humble (keigo)                                   | 3     |
| 5  | **Verb Type**     | る-verbs / ichidan (食べる), う-verbs / godan (飲む), irregular (する, 来る)                     | 3     |
| 6  | **Aspect**        | Simple, Progressive/continuous (〜ている), Completed/resultative (〜てある)                     | 3     |
| 7  | **Mood**          | Indicative, Volitional (〜ましょう), Imperative (〜て/〜なさい), Conditional (〜たら/〜ば), Potential (〜られる) | 5 |
| 8  | **Voice**         | Active, Passive (〜られる), Causative (〜させる), Causative-passive (〜させられる)               | 4     |
| 9  | **Sentence Type** | Statement, Question (〜か), Request (〜てください), Invitation (〜ませんか)                    | 4     |
| 10 | **Adjective Type**| い-adjective (大きい), な-adjective (静かな)                                                    | 2     |
| 11 | **Sentence Pattern** | A is B (AはBです), Existence (AにBがある), Action (AはBをVます), Direction (AはBへ行く), Desire (Vたい) | 5+ |

### How the Dimensions Combine

A single sentence sits at one point in this multi-dimensional space. For example:

> **私は水を飲みました。** (I drank water.)

| Dimension         | Value                |
|-------------------|----------------------|
| Person            | I (私)               |
| Tense             | Past (〜ました)       |
| Polarity          | Affirmative          |
| Politeness        | Polite (ます-form)    |
| Verb Type         | う-verb (飲む)        |
| Aspect            | Simple               |
| Mood              | Indicative           |
| Voice             | Active               |
| Sentence Type     | Statement            |
| Sentence Pattern  | Action (AはBをVます)  |

Change any single dimension and you get a different sentence:

| Change            | Result                                         | English                         |
|-------------------|-------------------------------------------------|---------------------------------|
| Tense → Present   | 私は水を飲みます                                 | I drink water.                  |
| Polarity → Neg    | 私は水を飲みませんでした                          | I did not drink water.          |
| Person → He       | 彼は水を飲みました                                | He drank water.                 |
| Politeness → Casual | 私は水を飲んだ                                  | I drank water. (casual)         |
| Voice → Passive   | 水は私に飲まれました                              | The water was drunk by me.      |
| Mood → Volitional | 水を飲みましょう                                  | Let's drink water.              |
| Sentence Type → Question | 私は水を飲みましたか                        | Did I drink water?              |
| Aspect → Progressive | 私は水を飲んでいます                            | I am drinking water.            |

### Prioritised Dimensions for Beginners

Not all dimensions are equally important at the start. Here is a suggested learning order:

| Priority | Dimension         | Beginner scope                          | Why first                              |
|----------|-------------------|-----------------------------------------|----------------------------------------|
| ★★★      | Person            | I, you, he/she                          | Core to every sentence                 |
| ★★★      | Tense             | Present, past                           | Needed immediately                     |
| ★★★      | Polarity          | Affirmative, negative                   | Yes/no is fundamental                  |
| ★★★      | Sentence Pattern  | "A is B", Action, Existence             | The 3 most used patterns               |
| ★★☆      | Sentence Type     | Statement, question                     | Conversations need both                |
| ★★☆      | Politeness        | Polite (ます-form) only                  | Safe default for all situations        |
| ★★☆      | Verb Type         | One of each (る/う/irregular)            | Needed to conjugate correctly          |
| ★☆☆      | Aspect            | Simple + progressive (〜ている)          | "I am doing" comes up often            |
| ★☆☆      | Mood              | Indicative + volitional (〜ましょう)     | "Let's …" is useful early              |
| ☆☆☆      | Voice             | Active only                             | Passive/causative can wait             |

### Beginner Combination Grid (for lesson planning)

Focusing on ★★★ dimensions only:

| | **Affirmative Present** | **Negative Present** | **Affirmative Past** | **Negative Past** |
|---|---|---|---|---|
| **I**      | 私は食べます | 私は食べません | 私は食べました | 私は食べませんでした |
| **You**    | あなたは食べます | あなたは食べません | あなたは食べました | あなたは食べませんでした |
| **He/She** | 彼は食べます | 彼は食べません | 彼は食べました | 彼は食べませんでした |

→ **3 persons × 2 tenses × 2 polarities = 12 forms per verb** — a manageable grid per lesson.

---

## Next Steps

- [ ] Pick a theme for Unit 1 (e.g. food, travel, daily routine)
- [ ] Fill in the 6 nouns and 6 verbs
- [ ] Define the 3 grammar patterns
- [ ] Generate the full lesson file with all repetition rounds
