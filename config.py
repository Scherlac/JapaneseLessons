"""
LLM Configuration Module

Centralized configuration for LLM integration using OpenAI-compatible interface.
Supports switching between Ollama (local), OpenAI cloud, and other providers.
"""

import os

# LLM Provider Configuration
# Default to Ollama (local, free) for development
# For LM Studio, use: http://localhost:1234/v1
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")  # LM Studio default port
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")  # LM Studio API key
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-14b")  # Updated to match LM Studio model name

# Model-specific settings
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# Timeout settings (seconds)
LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "60"))

# Debug mode
LLM_DEBUG = os.getenv("LLM_DEBUG", "false").lower() == "true"