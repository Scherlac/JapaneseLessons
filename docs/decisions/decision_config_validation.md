# Decision: Configuration Management + Data Validation

**Status:** Decided — python-dotenv for config; pydantic v2 for data validation  
**Date:** 2026-03-15  
**Context:** Two related areas are addressed here because the same already-installed packages
(`python-dotenv` 1.2.1, `pydantic` 2.12.5) solve both problems cleanly, and the decisions
are complementary.

---

## Part A — Configuration Management

### Current State

`config.py` reads configuration from environment variables with hardcoded defaults:

```python
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL    = os.getenv("LLM_MODEL", "qwen/qwen3-14b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
# ... etc
```

Problems:
- No `.env` file support — all overrides must be set as shell environment variables
- No validation — `LLM_TEMPERATURE=abc` silently crashes at `float()` with an unhelpful message
- Adding a new config key requires touching `config.py` + updating every caller

### Options

#### Option A1: Keep `config.py` + add `python-dotenv` (INSTALLED)

`python-dotenv` 1.2.1 is already installed. Adding two lines to `config.py`:

```python
from dotenv import load_dotenv
load_dotenv()  # reads .env file if present, does not override existing env vars
```

This allows developers to create a `.env` file:
```
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=qwen/qwen3-14b
LLM_TEMPERATURE=0.7
LLM_NO_THINK=true
LLM_CACHE=true
```

| Aspect | Detail |
|--------|--------|
| **Install** | `python-dotenv` already installed |
| **Type safety** | None — values are still strings from `os.getenv` |
| **Validation** | Manual `float()`, `int()` conversions remain |
| **Change impact** | 2 lines added to `config.py` |

**Pros:** Minimal change; `.env` file is the standard developer ergonomics pattern  
**Cons:** No type safety; no validation of bad values

---

#### Option A2: `pydantic-settings` (NOT INSTALLED)

A separate package (`pip install pydantic-settings`) that provides `BaseSettings`:

```python
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    llm_base_url: str = "http://localhost:1234/v1"
    llm_model: str = "qwen/qwen3-14b"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    llm_request_timeout: int = 60
    llm_no_think: bool = True
    llm_debug: bool = False
    llm_cache: bool = False

    class Config:
        env_file = ".env"
```

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install pydantic-settings` (~new dep) |
| **Type safety** | Full — types declared with annotations |
| **Validation** | Pydantic raises `ValidationError` for bad values |
| **`.env` support** | Built-in via `env_file = ".env"` |
| **Change impact** | Rewrites `config.py` |

**Pros:** Type-safe; validated; elegant  
**Cons:** New dependency (pydantic itself is installed, but `pydantic-settings` is separate); more complex than needed for 7 settings

---

### Config Decision: python-dotenv + existing config.py pattern ✅

**Rationale:**
- `python-dotenv` is already installed — zero cost
- 2-line change unlocks `.env` file developer ergonomics
- 7 config values are a trivially small number — typed settings class adds no real value at this scale
- `pydantic-settings` is YAGNI for 7 env vars; consider it if config grows beyond ~20 keys
- Add a `.env.example` to the repo root documenting all keys

---

## Part B — Data Validation

### Current State

`vocab_generator.py` contains ~40 lines of hand-rolled `validate_vocab_schema()`:

```python
_REQUIRED_NOUN_FIELDS = {"english", "japanese", "kanji", "romaji"}
_REQUIRED_VERB_FIELDS = {"english", "japanese", "kanji", "romaji", "type", "masu_form"}
_VALID_VERB_TYPES = {"る-verb", "う-verb", "irregular", "な-adj"}

def validate_vocab_schema(vocab: dict) -> list[str]:
    errors: list[str] = []
    if "theme" not in vocab:
        errors.append("Missing top-level 'theme' field")
    nouns = vocab.get("nouns")
    if not isinstance(nouns, list) or len(nouns) == 0:
        errors.append("'nouns' must be a non-empty list")
    # ... 30 more lines
```

Additionally, `curriculum.py` and `lesson_pipeline.py` (planned) will have their own dict
types with no enforcement. The `LessonContext` dataclass needs a clear schema.

### Options

#### Option B1: Keep hand-rolled validation

Continue with `validate_vocab_schema()`. Extend to cover curriculum and lesson content with
more hand-rolled code.

**Pros:** No new dependency  
**Cons:** Verbose; errors are string lists (not structured); duplicates logic already in `pydantic`; as schema grows, the validator grows proportionally

---

#### Option B2: `pydantic` v2 models (INSTALLED — 2.12.5)

Define Pydantic models for all data shapes. Validation happens at instantiation.

```python
from pydantic import BaseModel, field_validator
from typing import Literal

class Noun(BaseModel):
    english: str
    japanese: str
    kanji: str
    romaji: str

class Verb(BaseModel):
    english: str
    japanese: str
    kanji: str
    romaji: str
    type: Literal["る-verb", "う-verb", "irregular", "な-adj"]
    masu_form: str

class VocabFile(BaseModel):
    theme: str
    nouns: list[Noun]
    verbs: list[Verb]

    @field_validator("nouns", "verbs")
    @classmethod
    def must_be_non_empty(cls, v):
        if not v:
            raise ValueError("must not be empty")
        return v
```

Usage replaces `validate_vocab_schema()`:
```python
try:
    vocab = VocabFile.model_validate(raw_dict)
except ValidationError as e:
    print(e)  # structured, detailed error messages
```

Bonus: `VocabFile.model_json_schema()` generates a JSON Schema that can be used as the
`json_schema` argument to LLM calls — ensuring the LLM produces structurally valid vocab JSON.

| Aspect | Detail |
|--------|--------|
| **Install** | Already installed |
| **Validation** | Automatic on `model_validate()` — raises `ValidationError` with field-level detail |
| **Type safety** | Full — IDE autocompletion on model instances |
| **JSON schema** | `model_json_schema()` — can drive LLM `json_schema` response_format |
| **Serialisation** | `model.model_dump()` → `dict`; `model.model_dump_json()` → JSON string |
| **Migration** | `validate_vocab_schema()` can be replaced function-by-function |

**Pros:** Already installed; eliminates ~40 lines of error-prone hand-rolled validation; IDE support;  JSON schema generation is a bonus that improves LLM output quality  
**Cons:** Introduces pydantic as a project-level import (not just a test dependency) — acceptable given it's already installed

---

#### Option B3: `attrs` (INSTALLED — 25.4.0)

`attrs` provides declarative class definitions with validators.

```python
import attr

@attr.s
class Noun:
    english = attr.ib(validator=attr.validators.instance_of(str))
    japanese = attr.ib(validator=attr.validators.instance_of(str))
```

`attrs` is installed, but `pydantic` v2 is strictly superior for this use case:
- Pydantic handles nested validation (list of dicts) out of the box
- Pydantic generates JSON schema for LLM use
- Pydantic's error messages are more detailed
- `attrs` is better suited for performance-critical internal data structures, not external data validation

---

## Data Validation Decision: `pydantic` v2 models ✅

**Rationale:**
- Already installed — zero cost
- Replaces ~40 lines of hand-rolled validation with ~20 lines of readable model definitions
- `model_json_schema()` can drive the LLM `json_schema` response_format for vocab generation — structural improvement, not just a cleanup
- Type safety on model instances improves IDE experience throughout the pipeline
- `LessonContent`, `LessonContext`, `VocabFile` all benefit from pydantic models

**Migration plan:**
1. Add `models.py` with `Noun`, `Verb`, `VocabFile`, `GrammarSpec`, `LessonContent` models
2. Replace `validate_vocab_schema()` in `vocab_generator.py` with `VocabFile.model_validate()`
3. Use `VocabFile.model_json_schema()` to build the LLM prompt schema for vocab generation
4. Add `LessonContent` model used by `lesson_store.py` for persistence validation
5. Keep `_PERSONS_BEGINNER` etc. as plain constants — pydantic for external data, dataclasses for pipeline state

**Models to define:**
```
models.py
  Noun            — vocab noun entry
  Verb            — vocab verb entry
  VocabFile       — full vocab JSON file
  GrammarSpec     — one grammar progression entry (mirrors GRAMMAR_PROGRESSION dicts)
  GeneralItem        — LLM-generated noun practice item (with example_sentence, memory_tip)
  GeneralItem        — LLM-generated verb practice item (with polite_forms)
  Sentence        — LLM-generated grammar sentence
  LessonContent   — full lesson payload (noun_items + verb_items + sentences)
```
