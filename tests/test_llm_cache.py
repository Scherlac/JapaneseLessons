"""
Tests for llm_cache.py

Unit tests only — no LLM server required.  The llm_client.ask_llm_json_free()
function is monkeypatched throughout so tests run offline and instantly.

Coverage:
  - Cache miss: calls LLM, writes file, returns result
  - Cache hit:  reads file, does NOT call LLM again
  - sha256 key: identical prompts always hit the same file
  - clear_cache: deletes all .json files and returns correct count
  - cache_size:  returns correct entry count; 0 when dir absent
  - LLM_CACHE_DIR env var overrides default cache directory
"""

import json
from pathlib import Path

import pytest

import jlesson.llm_cache as cache_mod
from jlesson.llm_cache import (
    _cache_path,
    _resolve_cache_dir,
    ask_llm_cached,
    cache_size,
    clear_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STUB_RESPONSE = {"sentences": [{"english": "test", "japanese": "テスト"}]}


def _stub_llm(prompt: str) -> dict:  # noqa: ARG001
    return _STUB_RESPONSE


# ---------------------------------------------------------------------------
# _resolve_cache_dir
# ---------------------------------------------------------------------------

class TestResolveCacheDir:
    def test_explicit_path_wins(self, tmp_path):
        result = _resolve_cache_dir(tmp_path)
        assert result == tmp_path

    def test_env_var_wins_over_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path))
        result = _resolve_cache_dir(None)
        assert result == tmp_path

    def test_default_when_no_env(self, monkeypatch):
        monkeypatch.delenv("LLM_CACHE_DIR", raising=False)
        result = _resolve_cache_dir(None)
        assert result.parts[-2:] == ("output", ".cache")


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------

class TestCachePath:
    def test_returns_json_file(self, tmp_path):
        p = _cache_path("hello", tmp_path)
        assert p.suffix == ".json"
        assert p.parent == tmp_path

    def test_same_prompt_same_path(self, tmp_path):
        p1 = _cache_path("abc", tmp_path)
        p2 = _cache_path("abc", tmp_path)
        assert p1 == p2

    def test_different_prompts_different_paths(self, tmp_path):
        p1 = _cache_path("prompt A", tmp_path)
        p2 = _cache_path("prompt B", tmp_path)
        assert p1 != p2


# ---------------------------------------------------------------------------
# ask_llm_cached
# ---------------------------------------------------------------------------

class TestAskLlmCached:
    def test_cache_miss_calls_llm_and_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        result = ask_llm_cached("my prompt", cache_dir=tmp_path)
        assert result == _STUB_RESPONSE
        expected_file = _cache_path("my prompt", tmp_path)
        assert expected_file.exists()

    def test_cache_hit_returns_stored_result_without_llm(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        # Prime the cache
        ask_llm_cached("cached prompt", cache_dir=tmp_path)

        # Now replace LLM stub with one that raises if called
        def _should_not_be_called(_prompt):
            raise AssertionError("LLM should not be called on cache hit")

        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _should_not_be_called)
        result = ask_llm_cached("cached prompt", cache_dir=tmp_path)
        assert result == _STUB_RESPONSE

    def test_written_cache_file_is_valid_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        ask_llm_cached("json check", cache_dir=tmp_path)
        path = _cache_path("json check", tmp_path)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == _STUB_RESPONSE

    def test_cache_dir_created_automatically(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        nested = tmp_path / "a" / "b" / "cache"
        ask_llm_cached("auto-create dir", cache_dir=nested)
        assert nested.is_dir()

    def test_env_var_selects_cache_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path))
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        ask_llm_cached("env prompt")
        # File should land in tmp_path, not the default dir
        expected = _cache_path("env prompt", tmp_path)
        assert expected.exists()

    def test_different_prompts_yield_different_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        ask_llm_cached("prompt one", cache_dir=tmp_path)
        ask_llm_cached("prompt two", cache_dir=tmp_path)
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 2


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------

class TestClearCache:
    def test_deletes_all_json_files_and_returns_count(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        ask_llm_cached("p1", cache_dir=tmp_path)
        ask_llm_cached("p2", cache_dir=tmp_path)
        ask_llm_cached("p3", cache_dir=tmp_path)
        deleted = clear_cache(cache_dir=tmp_path)
        assert deleted == 3
        assert list(tmp_path.glob("*.json")) == []

    def test_returns_zero_when_dir_missing(self, tmp_path):
        missing = tmp_path / "nonexistent"
        assert clear_cache(cache_dir=missing) == 0

    def test_returns_zero_when_cache_empty(self, tmp_path):
        assert clear_cache(cache_dir=tmp_path) == 0


# ---------------------------------------------------------------------------
# cache_size
# ---------------------------------------------------------------------------

class TestCacheSize:
    def test_returns_count_of_cached_entries(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        assert cache_size(cache_dir=tmp_path) == 0
        ask_llm_cached("first", cache_dir=tmp_path)
        assert cache_size(cache_dir=tmp_path) == 1
        ask_llm_cached("second", cache_dir=tmp_path)
        assert cache_size(cache_dir=tmp_path) == 2

    def test_returns_zero_when_dir_missing(self, tmp_path):
        missing = tmp_path / "no_such_dir"
        assert cache_size(cache_dir=missing) == 0

    def test_decreases_after_clear(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "ask_llm_json_free", _stub_llm)
        ask_llm_cached("a", cache_dir=tmp_path)
        ask_llm_cached("b", cache_dir=tmp_path)
        clear_cache(cache_dir=tmp_path)
        assert cache_size(cache_dir=tmp_path) == 0
