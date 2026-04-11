"""
LLM Configuration Module

Centralized configuration for LLM integration using OpenAI-compatible interface.
Supports switching between Ollama (local), OpenAI cloud, and other providers.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# LLM Provider Configuration — defaults to LM Studio (local)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-14b")

# Model-specific settings
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))

# Timeout settings (seconds)
LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))

# Reasoning effort for thinking-capable models (qwen3, o-series, etc.).
# "none"  — disable thinking entirely; sends "/no_think" as system message (fastest)
# "low"   — minimal reasoning pass
# "medium"— balanced reasoning (good for narrative/review tasks)
# "high"  — full thinking (recommended for planning tasks like canonical planner)
# "xhigh" — maximum reasoning budget
# For local models via LM Studio (qwen3), low/medium/high/xhigh all map to "/think".
# Legacy env var LLM_NO_THINK=true is equivalent to LLM_REASONING_EFFORT=none.
_legacy_no_think = os.getenv("LLM_NO_THINK", "").lower()
_effort_default = "none" if (_legacy_no_think == "true" or _legacy_no_think == "") else "medium"
LLM_REASONING_EFFORT: str = os.getenv("LLM_REASONING_EFFORT", _effort_default)

# Debug mode
LLM_DEBUG = os.getenv("LLM_DEBUG", "false").lower() == "true"