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
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# Timeout settings (seconds)
LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "60"))

# Disable thinking/reasoning mode for models that support it (Qwen3, phi-4-reasoning, etc.).
# Sends "/no_think" as a system message, which skips the <think> block and makes
# responses faster and easier to parse.
LLM_NO_THINK = os.getenv("LLM_NO_THINK", "true").lower() == "true"

# Debug mode
LLM_DEBUG = os.getenv("LLM_DEBUG", "false").lower() == "true"