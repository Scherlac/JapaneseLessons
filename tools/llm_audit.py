"""Analyze LLM prompt/response cache and generated lesson outputs.

This script scans the local LLM cache at ~/.jlesson/cache and the workspace
output/ folder for curriculum lesson artifacts. It produces a summary of:

- prompt/response pair counts and categories
- cache mismatches (prompt without response, response without prompt)
- common prompt types detected by keyword heuristics
- curriculum outputs and lesson counts
- candidate audit issues for LLM optimization

Run as:
    python tools/llm_audit.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

CACHE_DIR = Path.home() / ".jlesson" / "cache"
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = WORKSPACE_ROOT / "output"

PROMPT_TYPE_PATTERNS = [
    (re.compile(r"Resolve the following canonical", re.IGNORECASE), "item_resolve"),
    (re.compile(r"curriculum writer adapting a movie|adapt a movie or TV-show script", re.IGNORECASE), "subtitle_narrative"),
    (re.compile(r"Create a progression of .* narrative blocks|planning a .* lesson narrative", re.IGNORECASE), "narrative"),
    (re.compile(r"Generate a JSON vocabulary file|Generate a JSON vocabulary file for the theme", re.IGNORECASE), "vocab_generation"),
    (re.compile(r"FIBONACCI LEARNING CYCLE|Pass 1:.*draft outline|Pass 2:.*revised outline", re.IGNORECASE), "lesson_plan"),
    (re.compile(r"build a prompt that asks for an english-french vocabulary json file", re.IGNORECASE), "vocab_generation"),
]

CURRICULUM_GLOB = "**/curriculum*.json"


@dataclass
class PromptCacheEntry:
    hash: str
    prompt_path: Path | None
    response_path: Path | None
    prompt_text: str | None = None
    response_size: int | None = None
    prompt_size: int | None = None
    prompt_type: str | None = None
    response_keys: list[str] | None = None
    response_valid: bool = False
    response_error: str | None = None


@dataclass
class CurriculumArtifact:
    path: Path
    lesson_count: int
    languages: list[str]
    lesson_ids: list[int]
    name: str | None
    created_at: str | None


def detect_prompt_type(prompt_text: str) -> str:
    for pattern, category in PROMPT_TYPE_PATTERNS:
        if pattern.search(prompt_text):
            return category
    return "unknown"


def _prompt_hash_from_file(path: Path) -> str:
    name = path.name
    if name.endswith(".prompt.txt"):
        return name[: -len(".prompt.txt")]
    return path.stem


def load_cache_entries(cache_dir: Path) -> list[PromptCacheEntry]:
    entries: dict[str, PromptCacheEntry] = {}
    for prompt_file in cache_dir.glob("*.prompt.txt"):
        key = _prompt_hash_from_file(prompt_file)
        entry = entries.setdefault(
            key,
            PromptCacheEntry(hash=key, prompt_path=prompt_file, response_path=None),
        )
        entry.prompt_path = prompt_file
        entry.prompt_size = prompt_file.stat().st_size
    for response_file in cache_dir.glob("*.json"):
        key = _prompt_hash_from_file(response_file)
        entry = entries.setdefault(
            key,
            PromptCacheEntry(hash=key, prompt_path=None, response_path=response_file),
        )
        entry.response_path = response_file
        entry.response_size = response_file.stat().st_size
    return list(entries.values())


def inspect_entry(entry: PromptCacheEntry) -> PromptCacheEntry:
    if entry.prompt_path and entry.prompt_path.exists():
        try:
            entry.prompt_text = entry.prompt_path.read_text(encoding="utf-8")
            entry.prompt_type = detect_prompt_type(entry.prompt_text)
        except Exception as exc:
            entry.prompt_text = None
            entry.response_error = f"prompt-read-error: {exc}"
    if entry.response_path and entry.response_path.exists():
        try:
            raw = json.loads(entry.response_path.read_text(encoding="utf-8"))
            entry.response_keys = list(raw.keys())
            entry.response_valid = True
        except Exception as exc:
            entry.response_valid = False
            entry.response_error = f"response-parse-error: {exc}"
    return entry


def summarize_prompt_cache(entries: list[PromptCacheEntry]) -> dict[str, Any]:
    total = len(entries)
    with_prompt = sum(1 for e in entries if e.prompt_path is not None)
    with_response = sum(1 for e in entries if e.response_path is not None)
    complete_pairs = sum(1 for e in entries if e.prompt_path and e.response_path)
    missing_prompt = [e.hash for e in entries if e.response_path and not e.prompt_path]
    missing_response = [e.hash for e in entries if e.prompt_path and not e.response_path]
    prompt_types: dict[str, int] = {}
    unknown_prompts = []
    broken_responses = []
    for e in entries:
        if e.prompt_type:
            prompt_types[e.prompt_type] = prompt_types.get(e.prompt_type, 0) + 1
        else:
            unknown_prompts.append(e.hash)
        if e.response_path and not e.response_valid:
            broken_responses.append({"hash": e.hash, "error": e.response_error})
    return {
        "total_entries": total,
        "entries_with_prompt": with_prompt,
        "entries_with_response": with_response,
        "complete_pairs": complete_pairs,
        "missing_prompt_files": missing_prompt,
        "missing_response_files": missing_response,
        "prompt_type_counts": prompt_types,
        "unknown_prompt_hashes": unknown_prompts[:20],
        "broken_responses": broken_responses[:20],
    }


def load_curriculum_artifacts(output_dir: Path) -> list[CurriculumArtifact]:
    artifacts: list[CurriculumArtifact] = []
    for path in sorted(output_dir.glob(CURRICULUM_GLOB)):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            lessons = raw.get("lessons", [])
            languages = []
            if "name" in raw:
                languages.append(raw.get("name"))
            artifacts.append(
                CurriculumArtifact(
                    path=path,
                    lesson_count=len(lessons),
                    languages=languages,
                    lesson_ids=[
                        int(lesson["id"])
                        for lesson in lessons
                        if isinstance(lesson, dict)
                        and isinstance(lesson.get("id"), int)
                    ],
                    name=raw.get("name"),
                    created_at=raw.get("created_at"),
                )
            )
        except Exception:
            artifacts.append(
                CurriculumArtifact(
                    path=path,
                    lesson_count=0,
                    languages=[],
                    lesson_ids=[],
                    name=None,
                    created_at=None,
                )
            )
    return artifacts


def summarize_curriculum_artifacts(artifacts: list[CurriculumArtifact]) -> dict[str, Any]:
    return {
        "curriculum_files": [
            {
                "path": str(a.path.relative_to(WORKSPACE_ROOT)),
                "lesson_count": a.lesson_count,
                "name": a.name,
                "created_at": a.created_at,
                "lesson_ids": a.lesson_ids[:20],
            }
            for a in artifacts
        ],
        "total_curricula": len(artifacts),
        "total_lessons": sum(a.lesson_count for a in artifacts),
    }


def build_report(cache_summary: dict[str, Any], curriculum_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "workspace_root": str(WORKSPACE_ROOT),
        "cache_dir": str(CACHE_DIR),
        "cache_summary": cache_summary,
        "curriculum_summary": curriculum_summary,
    }


def save_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    entries = load_cache_entries(CACHE_DIR)
    entries = [inspect_entry(entry) for entry in entries]
    summary = summarize_prompt_cache(entries)

    curricula = load_curriculum_artifacts(OUTPUT_DIR)
    curriculum_summary = summarize_curriculum_artifacts(curricula)

    report = build_report(summary, curriculum_summary)
    out_path = WORKSPACE_ROOT / "output" / "llm_audit_summary.json"
    save_report(report, out_path)
    print(f"LLM audit report written to: {out_path}")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
