# Decision: LLM Integration

**Status:** Open  
**Date:** 2026-03-14  
**Context:** The deterministic lesson generator covers formulaic patterns (nouns, verbs, polite-form conjugation) but cannot produce natural varied sentences, context-dependent particle usage, idiomatic expressions, casual speech, or explanations. An LLM is needed for the grammar phase at minimum, and optionally for vocabulary generation.

---

## What the LLM Would Do

| Task | Deterministic OK? | LLM Needed? |
|------|-------------------|-------------|
| Noun repetition cycle (INTRODUCE/RECALL/...) | Yes | No |
| Verb repetition cycle | Yes | No |
| Polite-form conjugation (ます/ません/ました/ませんでした) | Yes | No |
| Natural grammar sentences ("I eat fish" vs "I eat water") | Partially (needs curated pairs) | Yes — produces natural sentences |
| Casual/te-form/potential/volitional conjugation | Hard to template | Yes |
| Context sentences showing particle nuance (は vs が) | No | Yes |
| Vocabulary generation for new themes | No | Yes |
| Lesson explanations / grammar notes | No | Yes |

---

## Options

### Option 1: Ollama (Local, Free)

**What:** Local LLM server running open models (Qwen, Gemma, Llama, Mistral) on GPU.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install ollama` (client); separate Ollama server download |
| **Models** | Qwen 2.5 7B/14B, Gemma 3 12B, Llama 3.x 8B, Mistral 7B — all in GGUF |
| **GPU fit** | 16GB VRAM (5060 Ti / 9060 XT): 7B Q8 easily, 14B Q4 fits, 12B Q5 fits |
| **Japanese quality** | Qwen 2.5 14B — excellent Japanese; Gemma 3 12B — good |
| **API** | OpenAI-compatible REST + Python client; sync & async |
| **Latency** | ~2-8s for 200 tokens on 7B model (local GPU) |
| **Cost** | $0 (runs on your hardware) |
| **Offline** | Yes, fully offline after model download |
| **NVIDIA support** | Native CUDA |
| **AMD support** | ROCm support (Linux); Vulkan backend (Windows) — 9060 XT may need Vulkan |
| **JSON mode** | Yes — `format='json'` parameter |
| **Streaming** | Yes |

```python
from ollama import chat
response = chat(model='qwen2.5:14b', messages=[
    {'role': 'user', 'content': prompt}
], format='json')
print(response.message.content)
```

**Pros:** Free, private, offline, no API key, fast iteration, JSON mode  
**Cons:** Requires Ollama server running separately; model quality < cloud frontier models; 14B models are slower; AMD Windows support may need Vulkan workaround

---

### Option 2: llama-cpp-python (Local, Free, Embedded)

**What:** Python bindings for llama.cpp — runs GGUF models directly in-process, no separate server.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install llama-cpp-python` (builds from source — needs C compiler) |
| **Models** | Same GGUF models as Ollama (Qwen, Gemma, Llama, Mistral) from HuggingFace |
| **GPU fit** | Same as Ollama — 16GB VRAM |
| **Japanese quality** | Same models, same quality |
| **API** | OpenAI-compatible in-process; also includes OpenAI-compatible web server |
| **Latency** | Similar to Ollama |
| **Cost** | $0 |
| **Offline** | Yes |
| **NVIDIA support** | CUDA via `CMAKE_ARGS="-DGGML_CUDA=on"` |
| **AMD support** | hipBLAS (ROCm) or Vulkan |
| **JSON mode** | Yes — `response_format={"type": "json_object"}` or JSON Schema |
| **Streaming** | Yes |

```python
from llama_cpp import Llama
llm = Llama.from_pretrained(
    repo_id="Qwen/Qwen2.5-14B-Instruct-GGUF",
    filename="*q4_k_m.gguf",
    n_gpu_layers=-1,
    n_ctx=4096,
)
output = llm.create_chat_completion(
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
)
```

**Pros:** No separate server process; JSON Schema mode for structured output; in-process = simpler deployment  
**Cons:** Build from source (needs Visual Studio on Windows); model management is manual (download GGUFs yourself); slightly more setup friction than Ollama

---

### Option 3: OpenAI API (Cloud)

**What:** GPT-4o / GPT-5.2 via cloud API.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install openai` |
| **Models** | gpt-4o-mini (~$0.15/1M input), gpt-4o (~$2.50/1M), gpt-5.2 |
| **Japanese quality** | Excellent — frontier models, best Japanese accuracy |
| **API** | Official SDK; sync + async; streaming; structured outputs |
| **Latency** | ~1-3s for typical responses |
| **Cost** | Per-token; ~$0.01-0.05 per lesson generation with gpt-4o-mini |
| **Offline** | No — requires internet |
| **JSON mode** | Yes — `response_format={"type": "json_object"}` + structured outputs |

```python
from openai import OpenAI
client = OpenAI()  # uses OPENAI_API_KEY env var
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
)
```

**Pros:** Best quality; fastest; structured outputs; minimal setup  
**Cons:** Costs money; requires API key; requires internet; data leaves your machine

---

### Option 4: Anthropic API (Cloud)

**What:** Claude Opus/Sonnet via cloud API.

| Aspect | Detail |
|--------|--------|
| **Install** | `pip install anthropic` |
| **Models** | claude-sonnet-4-20250514 (~$3/1M input), claude-opus-4-20250514 |
| **Japanese quality** | Excellent — strong at following structured output formats |
| **API** | Official SDK; sync + async; streaming |
| **Latency** | ~2-5s typical |
| **Cost** | Per-token; ~$0.02-0.10 per lesson with Sonnet |
| **Offline** | No |
| **JSON mode** | Via prompt instruction (no native `response_format` param, but reliable) |

```python
from anthropic import Anthropic
client = Anthropic()  # uses ANTHROPIC_API_KEY env var
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}],
)
```

**Pros:** Very high quality; excellent instruction following; great at structured tasks  
**Cons:** Costs money; requires API key; no native JSON mode (though very reliable from prompts)

---

### Option 5: OpenAI-Compatible Interface (Abstraction Layer)

**What:** Use the OpenAI Python SDK as a universal client — it works with OpenAI, Ollama, llama-cpp-python server, Azure, and many other providers by changing `base_url`.

| Provider | base_url |
|----------|----------|
| OpenAI | `https://api.openai.com/v1` (default) |
| Ollama | `http://localhost:11434/v1` |
| llama-cpp-python server | `http://localhost:8000/v1` |
| Azure OpenAI | `https://<endpoint>.openai.azure.com/` |
| Any OpenAI-compatible | Custom URL |

```python
from openai import OpenAI

# Switch between providers with just base_url + api_key
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")  # Ollama
# client = OpenAI()  # OpenAI cloud
# client = OpenAI(base_url="http://localhost:8000/v1", api_key="local")  # llama.cpp

response = client.chat.completions.create(
    model="qwen2.5:14b",
    messages=[{"role": "user", "content": prompt}],
)
```

**Pros:** Single interface for all providers; switch local ↔ cloud with one config change; `openai` SDK is well-maintained  
**Cons:** Anthropic doesn't use this (needs its own SDK); some features may not map 1:1

---

## Comparison Matrix

| Criteria | Ollama | llama-cpp-python | OpenAI API | Anthropic API | OpenAI SDK (universal) |
|----------|--------|-----------------|------------|---------------|----------------------|
| **Cost** | Free | Free | Pay-per-token | Pay-per-token | Depends on backend |
| **Offline** | Yes | Yes | No | No | Depends |
| **Setup ease** | Medium (server) | Hard (build) | Easy | Easy | Easy |
| **Japanese quality** | Good (Qwen 14B) | Good (Qwen 14B) | Excellent | Excellent | Depends on backend |
| **JSON mode** | Yes | Yes + Schema | Yes + Schema | Via prompt | Yes |
| **5060 Ti / 9060 XT** | CUDA / Vulkan | CUDA / ROCm / Vulkan | N/A | N/A | Depends |
| **Speed (200 tokens)** | ~2-8s local | ~2-8s local | ~1-3s cloud | ~2-5s cloud | Depends |
| **Async** | Yes | Via server | Yes | Yes | Yes |
| **Privacy** | Full | Full | No | No | Depends |
| **Dependency** | ollama server + pip | C compiler + pip | pip only | pip only | pip only |

---

## Recommendation

**Use Option 5 (OpenAI-compatible interface) + Option 1 (Ollama) as default backend.**

Rationale:
1. **Code once** — use `openai` SDK with configurable `base_url`. This lets us switch between Ollama (local/free) and OpenAI cloud (high quality) with a single env var.
2. **GPU-ready** — Ollama on 5060 Ti (CUDA) or 9060 XT (Vulkan) can run Qwen 2.5 14B at Q4, which has strong Japanese capability.
3. **Free by default** — no API key needed for daily development; cloud APIs optional for higher quality.
4. **JSON mode** — both Ollama and OpenAI support `response_format={"type": "json_object"}` through the same interface.
5. **KISS** — one `pip install openai`, one config class, swap backends via env var.

### Implementation Plan

```python
# config.py
import os

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")  # default: Ollama
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:14b")
```

```python
# llm_client.py
from openai import OpenAI
from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

def ask_llm(prompt: str, json_mode: bool = False) -> str:
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    return response.choices[0].message.content
```

### Recommended Models by GPU

| GPU | VRAM | Best Model | Quantization | Notes |
|-----|------|-----------|--------------|-------|
| RTX 5060 Ti | 16GB | Qwen 2.5 14B Instruct | Q4_K_M | Native CUDA, best Japanese |
| RX 9060 XT | 16GB | Qwen 2.5 14B Instruct | Q4_K_M | Vulkan backend on Windows |
| Either | 16GB | Gemma 3 12B | Q5_K_M | Alternative, good Japanese |
| Either | 16GB | Llama 3.x 8B | Q8_0 | Faster but weaker Japanese |

### Deterministic + LLM Hybrid Strategy

Keep both approaches and pick per-phase:

| Phase | Generator | Why |
|-------|-----------|-----|
| Phase 1 (Nouns) | Deterministic | Formulaic — no creativity needed |
| Phase 2 (Verbs) | Deterministic | Same cyclic pattern |
| Phase 3 (Grammar — polite) | Deterministic | ます-form conjugation is regular |
| Phase 3 (Grammar — varied) | LLM | Casual forms, te-form, idiomatic sentences |
| Vocabulary generation | LLM | Needs cultural/contextual knowledge |
| Grammar explanations | LLM | Free-form text |

This hybrid approach means the tool works fully offline/free with deterministic mode, and LLM enhances quality when available.
