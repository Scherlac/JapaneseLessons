#!/usr/bin/env python3
"""
Spike 07: LM Studio API Evaluation

Explores the LM Studio local API to:
1. Check server connectivity
2. List available (downloaded) models
3. Load a model if none is loaded
4. Run a simple generation test to confirm it works
5. Report latency and JSON-mode compatibility

LM Studio exposes an OpenAI-compatible API at http://localhost:1234/v1
plus a subset of extra endpoints for model management.

Usage:
    python spike/spike_07_lmstudio_api.py
"""

import json
import re
import sys
import time
from pathlib import Path

import requests


def strip_think(text: str) -> str:
    """Remove <think>...</think> reasoning blocks produced by thinking models.
    Also handles truncated blocks where </think> is missing.
    """
    # Complete block
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Truncated block (no closing tag)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


# Add this as a system message to disable thinking mode on Qwen3 and similar models
NO_THINK_SYSTEM = "/no_think"

BASE_URL = "http://localhost:1234"
API_BASE = f"{BASE_URL}/v1"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer lm-studio"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get(path: str, timeout: int = 5) -> requests.Response:
    return requests.get(f"{API_BASE}{path}", headers=HEADERS, timeout=timeout)


def post(path: str, body: dict, timeout: int = 30) -> requests.Response:
    return requests.post(
        f"{API_BASE}{path}", headers=HEADERS,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        timeout=timeout,
    )


def section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def check_connectivity() -> bool:
    section("1. Connectivity check")
    try:
        r = get("/models", timeout=4)
        print(f"  ✅ Server reachable — HTTP {r.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Cannot connect to {BASE_URL}")
        print("     → Make sure LM Studio is open and the local server is started")
        print("       (LM Studio → Local Server tab → Start Server)")
        return False
    except requests.exceptions.Timeout:
        print(f"  ❌ Connection timed out")
        return False


def list_models() -> list[dict]:
    section("2. Available models")
    try:
        r = get("/models")
        r.raise_for_status()
        models = r.json().get("data", [])
        if not models:
            print("  ⚠️  No models loaded. Load a model in LM Studio first.")
        else:
            for m in models:
                print(f"  • {m['id']}")
        return models
    except Exception as e:
        print(f"  ❌ Failed to list models: {e}")
        return []


def check_loaded_model(models: list[dict]) -> str | None:
    """Return the id of the currently loaded model, or None."""
    section("3. Loaded model")
    if not models:
        print("  ⚠️  No model is currently loaded in LM Studio.")
        print("     → In LM Studio: go to the Chat tab, pick a model, click Load.")
        return None
    # LM Studio typically lists only the loaded model(s)
    model_id = models[0]["id"]
    print(f"  ✅ Active model: {model_id}")
    return model_id


def test_plain_text(model_id: str) -> bool:
    section("4. Plain text generation")
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": NO_THINK_SYSTEM},
            {"role": "user", "content": "Say hello in Japanese. One sentence only."},
        ],
        "temperature": 0.5,
        "max_tokens": 256,
    }
    try:
        t0 = time.time()
        r = post("/chat/completions", body, timeout=30)
        elapsed = time.time() - t0
        r.raise_for_status()
        content = strip_think(r.json()["choices"][0]["message"]["content"])
        print(f"  ✅ Response ({elapsed:.2f}s): {content.strip()}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_json_object_mode(model_id: str) -> bool:
    section("5. JSON object mode (response_format)")
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": NO_THINK_SYSTEM},
            {"role": "user", "content": (
                'Return a JSON object with keys "english", "japanese", "romaji". '
                'English sentence: "I eat fish."'
            )},
        ],
        "temperature": 0.3,
        "max_tokens": 256,
        "response_format": {"type": "json_object"},
    }
    try:
        t0 = time.time()
        r = post("/chat/completions", body, timeout=30)
        elapsed = time.time() - t0
        if r.status_code == 400:
            print(f"  ⚠️  json_object not supported (HTTP 400): {r.json()}")
            return False
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        print(f"  ✅ JSON mode works ({elapsed:.2f}s)")
        print(f"     english:  {parsed.get('english')}")
        print(f"     japanese: {parsed.get('japanese')}")
        print(f"     romaji:   {parsed.get('romaji')}")
        return True
    except json.JSONDecodeError:
        print(f"  ⚠️  Response was not valid JSON: {content}")
        return False
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_json_via_prompt(model_id: str) -> bool:
    """Fallback: ask for JSON in plain text mode (no response_format)."""
    section("6. JSON via prompt (text mode fallback)")
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": NO_THINK_SYSTEM},
            {"role": "user", "content": (
                'Return ONLY a raw JSON object — no markdown, no explanation.\n'
                'Keys: "english", "japanese", "romaji".\n'
                'English sentence: "I drink water."'
            )},
        ],
        "temperature": 0.3,
        "max_tokens": 256,
    }
    try:
        t0 = time.time()
        r = post("/chat/completions", body, timeout=30)
        elapsed = time.time() - t0
        r.raise_for_status()
        content = strip_think(r.json()["choices"][0]["message"]["content"])
        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        print(f"  ✅ Prompt-based JSON works ({elapsed:.2f}s)")
        print(f"     english:  {parsed.get('english')}")
        print(f"     japanese: {parsed.get('japanese')}")
        print(f"     romaji:   {parsed.get('romaji')}")
        return True
    except json.JSONDecodeError:
        print(f"  ⚠️  Could not parse JSON from response: {content}")
        return False
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("🚀 Spike 07: LM Studio API Evaluation")
    print(f"   Target: {BASE_URL}")

    if not check_connectivity():
        sys.exit(1)

    models = list_models()
    model_id = check_loaded_model(models)

    if not model_id:
        print("\n⛔ No model loaded — cannot run generation tests.")
        print("   Load a model in LM Studio and re-run this spike.")
        sys.exit(1)

    plain_ok = test_plain_text(model_id)
    json_mode_ok = test_json_object_mode(model_id)
    if not json_mode_ok:
        json_prompt_ok = test_json_via_prompt(model_id)
    else:
        json_prompt_ok = None  # not needed

    # Summary
    section("Summary")
    print(f"  Model loaded:        ✅ {model_id}")
    print(f"  Plain text:          {'✅' if plain_ok else '❌'}")
    print(f"  JSON object mode:    {'✅' if json_mode_ok else '⚠️  not supported'}")
    if json_prompt_ok is not None:
        print(f"  JSON via prompt:     {'✅' if json_prompt_ok else '❌'}")

    if not json_mode_ok and not json_prompt_ok:
        print("\n  ❌ Model cannot reliably produce JSON — consider a different model.")
    elif not json_mode_ok and json_prompt_ok:
        print("\n  ℹ️  Use prompt-based JSON (no response_format). llm_client.py already has this fallback.")
    else:
        print("\n  ✅ LM Studio is ready for use with this project.")

    # Save results
    output_dir = Path("spike/output")
    output_dir.mkdir(exist_ok=True)
    results = {
        "base_url": BASE_URL,
        "model_id": model_id,
        "plain_text_ok": plain_ok,
        "json_mode_ok": json_mode_ok,
        "json_prompt_ok": json_prompt_ok,
    }
    out_file = output_dir / "spike_07_lmstudio_api.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n  💾 Results saved to {out_file}")


if __name__ == "__main__":
    main()
