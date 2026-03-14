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
import pathlib

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


EMBEDDING_KEYWORDS = ("embed", "embedding")


def is_generation_model(model_id: str) -> bool:
    """Return False for embedding-only models that can't do chat completions."""
    return not any(kw in model_id.lower() for kw in EMBEDDING_KEYWORDS)


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
                tag = "" if is_generation_model(m["id"]) else "  [embedding — skip]"
                print(f"  • {m['id']}{tag}")
        return models
    except Exception as e:
        print(f"  ❌ Failed to list models: {e}")
        return []


def get_generation_models(models: list[dict]) -> list[str]:
    """Return IDs of all models capable of chat completions."""
    section("3. Generation models")
    gen_models = [m["id"] for m in models if is_generation_model(m["id"])]
    if not gen_models:
        print("  ⚠️  No generation models found in LM Studio.")
    else:
        for mid in gen_models:
            print(f"  ✅ {mid}")
    return gen_models


def test_plain_text(model_id: str, timeout: int = 120) -> bool:
    section(f"Plain text generation — {model_id}")
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
        r = post("/chat/completions", body, timeout=timeout)
        elapsed = time.time() - t0
        r.raise_for_status()
        content = strip_think(r.json()["choices"][0]["message"]["content"])
        print(f"  ✅ Response ({elapsed:.2f}s): {content.strip()}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_json_object_mode(model_id: str, timeout: int = 120) -> bool:
    section(f"JSON object mode — {model_id}")
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
        r = post("/chat/completions", body, timeout=timeout)
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


def test_json_via_prompt(model_id: str, timeout: int = 120) -> bool:
    """Fallback: ask for JSON in plain text mode (no response_format)."""
    section(f"JSON via prompt fallback — {model_id}")
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
        r = post("/chat/completions", body, timeout=timeout)
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


def evaluate_model(model_id: str) -> dict:
    """Run all three tests for one model and return a result dict."""
    print(f"\n{'#'*55}")
    print(f"  EVALUATING: {model_id}",flush=True)
    print(f"{'#'*55}")
    # First request to a new model may trigger LM Studio to swap it in — allow extra time
    plain_ok = test_plain_text(model_id, timeout=180)
    json_mode_ok = test_json_object_mode(model_id, timeout=120)
    json_prompt_ok: bool | None
    if not json_mode_ok:
        json_prompt_ok = test_json_via_prompt(model_id, timeout=120)
    else:
        json_prompt_ok = None  # not needed

    json_capable = json_mode_ok or bool(json_prompt_ok)

    print(f"\n  {'─'*45}")
    print(f"  Plain text:       {'✅' if plain_ok else '❌'}")
    print(f"  JSON object mode: {'✅' if json_mode_ok else '⚠️  not supported'}")
    if json_prompt_ok is not None:
        print(f"  JSON via prompt:  {'✅' if json_prompt_ok else '❌'}")
    if not json_capable:
        verdict = "❌ Cannot reliably produce JSON — not suitable"
    elif not json_mode_ok and json_prompt_ok:
        verdict = "ℹ️  Use prompt-based JSON (llm_client.py fallback path)"
    else:
        verdict = "✅ Ready — JSON object mode supported"
    print(f"  Verdict:          {verdict}", flush=True)

    return {
        "model_id": model_id,
        "plain_text_ok": plain_ok,
        "json_mode_ok": json_mode_ok,
        "json_prompt_ok": json_prompt_ok,
        "json_capable": json_capable,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("🚀 Spike 07: LM Studio API Evaluation (all models)")
    print(f"   Target: {BASE_URL}")

    if not check_connectivity():
        sys.exit(1)

    models = list_models()
    gen_model_ids = get_generation_models(models)

    if not gen_model_ids:
        print("\n⛔ No generation models available — cannot run tests.")
        sys.exit(1)

    all_results = []
    for mid in gen_model_ids:
        result = evaluate_model(mid)
        all_results.append(result)

    # Summary table
    section("Final Summary")
    print(f"  {'Model':<45} {'Plain':^7} {'JSON mode':^10} {'JSON prompt':^12} {'Usable':^7}")
    print(f"  {'─'*45} {'─'*7} {'─'*10} {'─'*12} {'─'*7}")
    for r in all_results:
        plain  = "✅" if r["plain_text_ok"] else "❌"
        jmode  = "✅" if r["json_mode_ok"] else "—"
        jprompt = ("✅" if r["json_prompt_ok"] else "❌") if r["json_prompt_ok"] is not None else "—"
        usable = "✅" if r["json_capable"] else "❌"
        print(f"  {r['model_id']:<45} {plain:^7} {jmode:^10} {jprompt:^12} {usable:^7}", flush=True)

    # Save results
    output_dir = pathlib.Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    results_payload = {"base_url": BASE_URL, "models": all_results}
    out_file = output_dir / "spike_07_lmstudio_api.json"
    out_file.write_text(json.dumps(results_payload, indent=2, ensure_ascii=False))
    print(f"\n  💾 Results saved to {out_file}")


if __name__ == "__main__":
    import pathlib

    # Redirect output to a log file for easier review
    log_dir = pathlib.Path(__file__).parent / "output" / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"spike_07_lmstudio_api_{int(time.time())}.log"
    with log_file.open("w", encoding="utf-8") as f:
        sys.stdout = f
        main()
