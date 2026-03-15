"""
Tests for llm_client.py

Two test categories:

  Unit tests  — always run, no server required. Cover pure-Python helpers:
                _strip_think, _extract_json, LLMClient._build_messages.

  Integration — require LM Studio running at http://localhost:1234.
                Automatically skipped when the server is unreachable.

Usage:
    # All tests (unit + integration if LM Studio is up):
    pytest tests/test_llm_client.py -v

    # Unit tests only:
    pytest tests/test_llm_client.py -v -m "not integration"

    # Integration tests only:
    pytest tests/test_llm_client.py -v -m integration
"""

import json
import time

import pytest

from jlesson.llm_client import (
    LLMClient,
    _NO_SYSTEM_ROLE_PATTERNS,
    _TRANSLATION_SCHEMA,
    _extract_json,
    _strip_think,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers shared by unit + integration
# ─────────────────────────────────────────────────────────────────────────────

LM_STUDIO_BASE = "http://localhost:1234/v1"
_HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer lm-studio"}


def _lm_studio_reachable() -> bool:
    try:
        import requests
        r = requests.get(f"{LM_STUDIO_BASE}/models", timeout=4)
        return r.status_code == 200
    except Exception:
        return False


def _list_generation_models() -> list[str]:
    """Return IDs of all non-embedding models currently loaded in LM Studio."""
    import requests
    r = requests.get(f"{LM_STUDIO_BASE}/models", timeout=4)
    models = r.json().get("data", [])
    return [
        m["id"] for m in models
        if not any(kw in m["id"].lower() for kw in ("embed", "embedding"))
    ]


# Evaluated once at collection time so skips are applied immediately.
_server_up = _lm_studio_reachable()
_available_models: list[str] = _list_generation_models() if _server_up else []

lm_studio = pytest.mark.skipif(
    not _server_up,
    reason="LM Studio not running at http://localhost:1234",
)


# ─────────────────────────────────────────────────────────────────────────────
# Unit — _strip_think
# ─────────────────────────────────────────────────────────────────────────────

class TestStripThink:
    def test_removes_complete_block(self):
        assert _strip_think("<think>reasoning</think>Answer.") == "Answer."

    def test_removes_multiline_block(self):
        assert _strip_think("<think>\nline 1\nline 2\n</think>Result.") == "Result."

    def test_removes_truncated_block(self):
        # Model was cut off before </think>
        assert _strip_think("<think>started but never finished") == ""

    def test_passthrough_no_block(self):
        assert _strip_think("こんにちは。") == "こんにちは。"

    def test_strips_surrounding_whitespace(self):
        assert _strip_think("  <think>x</think>  answer  ") == "answer"

    def test_multiple_blocks(self):
        text = "<think>first</think>middle<think>second</think>end"
        assert _strip_think(text) == "middleend"


# ─────────────────────────────────────────────────────────────────────────────
# Unit — _extract_json
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractJson:
    _VALID = {"english": "I eat fish.", "japanese": "魚を食べます。", "romaji": "Sakana o tabemasu."}

    def test_direct_parse(self):
        text = json.dumps(self._VALID)
        assert _extract_json(text) == self._VALID

    def test_json_embedded_in_prose(self):
        text = f'Here is the translation: {json.dumps(self._VALID)} Hope that helps!'
        result = _extract_json(text)
        assert result is not None
        assert result["japanese"] == "魚を食べます。"

    def test_json_in_json_code_fence(self):
        text = f'```json\n{json.dumps(self._VALID)}\n```'
        result = _extract_json(text)
        assert result is not None
        assert result["romaji"] == "Sakana o tabemasu."

    def test_json_in_plain_code_fence(self):
        text = f'```\n{json.dumps(self._VALID)}\n```'
        result = _extract_json(text)
        assert result is not None
        assert result["english"] == "I eat fish."

    def test_picks_last_blob_from_reasoning_output(self):
        # Reasoning models put the answer last — we must not pick the intermediate one.
        wrong = {"intermediate": "step"}
        right = {"english": "dog", "japanese": "犬", "romaji": "inu"}
        text = f"Thinking... {json.dumps(wrong)}\nFinal answer: {json.dumps(right)}"
        result = _extract_json(text)
        assert result is not None
        assert result["japanese"] == "犬"

    def test_returns_none_for_plain_prose(self):
        assert _extract_json("This is not JSON at all.") is None

    def test_returns_none_for_empty_string(self):
        assert _extract_json("") is None

    def test_returns_none_for_only_whitespace(self):
        assert _extract_json("   \n  ") is None


# ─────────────────────────────────────────────────────────────────────────────
# Unit — LLMClient._build_messages
# ─────────────────────────────────────────────────────────────────────────────

def _make_client(model_id: str, no_think: bool) -> LLMClient:
    """Create a bare LLMClient instance without calling __init__ (no network needed)."""
    client = LLMClient.__new__(LLMClient)
    client.model = model_id
    client.no_think = no_think
    return client


class TestBuildMessages:
    def test_standard_model_no_think_enabled(self):
        client = _make_client("qwen/qwen3-14b", no_think=True)
        msgs = client._build_messages("Translate this.")
        assert msgs[0] == {"role": "system", "content": "/no_think"}
        assert msgs[1] == {"role": "user", "content": "Translate this."}

    def test_standard_model_no_think_disabled(self):
        client = _make_client("qwen/qwen3-14b", no_think=False)
        msgs = client._build_messages("Translate this.")
        assert msgs == [{"role": "user", "content": "Translate this."}]

    def test_mistral_no_system_role_with_no_think(self):
        # Mistral [INST] GGUF template has no system slot — must fold into user turn.
        client = _make_client("mistral-7b-instruct-v0.3", no_think=True)
        msgs = client._build_messages("Translate this.")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert "/no_think" in msgs[0]["content"]
        assert "Translate this." in msgs[0]["content"]

    def test_mistral_no_think_disabled(self):
        client = _make_client("mistral-7b-instruct-v0.3", no_think=False)
        msgs = client._build_messages("Hello.")
        assert msgs == [{"role": "user", "content": "Hello."}]

    def test_mistral_pattern_is_case_insensitive(self):
        # Pattern matching uses model.lower(), so mixed-case IDs are handled.
        client = _make_client("mistralai/Mistral-7B-Instruct-v0.3", no_think=True)
        msgs = client._build_messages("Hi.")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    def test_non_mistral_model_gets_system_role(self):
        for model_id in ("qwen/qwen3.5-9b", "microsoft/phi-4-reasoning-plus", "meta-llama-3.1-8b"):
            client = _make_client(model_id, no_think=True)
            msgs = client._build_messages("Hi.")
            assert msgs[0]["role"] == "system", f"Expected system role for {model_id}"
            assert msgs[1]["role"] == "user"


# ─────────────────────────────────────────────────────────────────────────────
# Integration — configured model (config.py LLM_MODEL)
# ─────────────────────────────────────────────────────────────────────────────

@lm_studio
@pytest.mark.integration
class TestLLMClientIntegration:
    """Live tests using the model configured in config.py."""

    def test_generate_text_returns_content(self):
        from llm_client import get_llm_client
        client = get_llm_client()
        t0 = time.time()
        result = client.generate_text(
            "Say hello in Japanese. One short sentence.",
            max_tokens=128,
        )
        elapsed = time.time() - t0
        assert isinstance(result, str)
        assert len(result.strip()) > 0, "Response was empty"
        print(f"\n  Response ({elapsed:.2f}s): {result.strip()}")

    def test_generate_text_strips_think_blocks(self):
        from llm_client import get_llm_client
        client = get_llm_client()
        result = client.generate_text(
            "What is the Japanese word for 'water'?",
            max_tokens=256,
        )
        assert "<think>" not in result
        assert "</think>" not in result

    def test_generate_json_returns_translation(self):
        from llm_client import get_llm_client
        client = get_llm_client()
        t0 = time.time()
        result = client.generate_json(
            'Translate the English sentence into Japanese.\n'
            'English sentence: "I eat fish."\n'
            'Return JSON with keys: english, japanese, romaji, context.'
        )
        elapsed = time.time() - t0
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result.get("english"), "english field is empty"
        assert result.get("japanese"), "japanese field is empty"
        assert result.get("romaji"),   "romaji field is empty"
        print(f"\n  english:  {result.get('english')}")
        print(f"  japanese: {result.get('japanese')}")
        print(f"  romaji:   {result.get('romaji')}")
        print(f"  ({elapsed:.2f}s)")

    def test_configured_model_in_lm_studio(self):
        from config import LLM_MODEL
        assert any(LLM_MODEL in m for m in _available_models), (
            f"Configured model '{LLM_MODEL}' not found in LM Studio. "
            f"Available: {_available_models}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Integration — spike-07-style sweep across all generation models
# ─────────────────────────────────────────────────────────────────────────────

@lm_studio
@pytest.mark.integration
class TestAllModelsConnectivity:
    """Verify at least one generation model is loaded."""

    def test_at_least_one_model_available(self):
        assert len(_available_models) > 0, "No generation models found in LM Studio"

    def test_models_list(self):
        print(f"\n  Available generation models ({len(_available_models)}):")
        for m in _available_models:
            print(f"    • {m}")


@lm_studio
@pytest.mark.integration
@pytest.mark.skip(reason="Spike-07-style sweep across all models — run manually when needed")
@pytest.mark.parametrize("model_id", _available_models)
def test_json_schema_per_model(model_id: str):
    """Each generation model must return valid JSON with required keys via json_schema.

    This is the spike-07 equivalent: grammar-sampled structured output test.
    Validates that llama.cpp grammar sampling enforces the translation schema
    regardless of each model's verbosity or thinking-mode behaviour.
    """
    import requests

    def _build(mid: str, system: str, user: str) -> list[dict]:
        if any(p in mid.lower() for p in _NO_SYSTEM_ROLE_PATTERNS):
            return [{"role": "user", "content": f"{system}\n\n{user}"}]
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    body = {
        "model": model_id,
        "messages": _build(
            model_id,
            "/no_think",
            'Translate the English sentence into Japanese. English: "I eat fish."',
        ),
        "temperature": 0.3,
        "max_tokens": 256,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "translation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "english":  {"type": "string"},
                        "japanese": {"type": "string"},
                        "romaji":   {"type": "string"},
                    },
                    "required": ["english", "japanese", "romaji"],
                },
            },
        },
    }

    t0 = time.time()
    r = requests.post(
        f"{LM_STUDIO_BASE}/chat/completions",
        headers=_HEADERS,
        json=body,
        timeout=180,
    )
    elapsed = time.time() - t0

    assert r.status_code == 200, (
        f"HTTP {r.status_code} for model '{model_id}': {r.text[:300]}"
    )

    content = r.json()["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Response is not valid JSON for '{model_id}': {content[:200]} — {exc}")

    assert parsed.get("japanese"), (
        f"japanese field empty for '{model_id}': {parsed}"
    )
    assert parsed.get("romaji"), (
        f"romaji field empty for '{model_id}': {parsed}"
    )

    print(f"\n  {model_id} ({elapsed:.2f}s)")
    print(f"    english:  {parsed.get('english')}")
    print(f"    japanese: {parsed.get('japanese')}")
    print(f"    romaji:   {parsed.get('romaji')}")
