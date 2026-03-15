"""
LLM Client Module

Universal LLM client using OpenAI SDK for compatibility with Ollama, OpenAI, and other providers.
Provides simple interface for text generation with optional JSON mode.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from openai import OpenAI
from openai._exceptions import APIError, RateLimitError

from .config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_DEBUG,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_NO_THINK,
    LLM_REQUEST_TIMEOUT,
    LLM_TEMPERATURE,
)

# Set up logging
logger = logging.getLogger(__name__)
if LLM_DEBUG:
    logging.basicConfig(level=logging.DEBUG)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think(text: str) -> str:
    """Remove <think> blocks (complete or truncated) from reasoning models."""
    text = _THINK_RE.sub("", text)
    # Handle truncated block where </think> is missing (model was cut off mid-thought)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


def _find_json_objects(text: str) -> list[str]:
    """Return all top-level {...} substrings, handling arbitrary nesting depth."""
    results: list[str] = []
    depth = 0
    start: Optional[int] = None
    in_string = False
    escape_next = False
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                results.append(text[start:i + 1])
                start = None
    return results


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Try to extract a valid JSON object from text.

    Useful when reasoning/verbose models embed the answer inside prose.
    Scans from the end of the text since reasoning models place the answer last.
    """
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    # Code-fence extraction  ``` or ```json  (try before brace scan so fences win)
    fence = re.search(r'```(?:json)?[ \t]*\n?(.*?)```', text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass
    # Brace-depth scan — finds all top-level {...} blobs including nested ones;
    # try the last one first because reasoning models place the final answer at the end.
    for blob in reversed(_find_json_objects(text)):
        try:
            return json.loads(blob)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


# LM Studio uses llama.cpp grammar-based sampling and requires json_schema (not
# json_object).  This schema covers the translation response used by lesson_generator.py.
_TRANSLATION_SCHEMA = {
    "type": "object",
    "properties": {
        "english":  {"type": "string"},
        "japanese": {"type": "string"},
        "romaji":   {"type": "string"},
        "context":  {"type": "string"},
    },
    "required": ["english", "japanese", "romaji"],
}

# Mistral-7B-Instruct v0.x GGUFs use the old [INST] chat template which has no
# system-role token.  Sending a system message causes HTTP 400.
_NO_SYSTEM_ROLE_PATTERNS = ("mistral-7b-instruct",)


class LLMClient:
    """Universal LLM client using OpenAI-compatible interface."""

    def __init__(self):
        self.client = OpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            timeout=LLM_REQUEST_TIMEOUT,
            max_retries=0,
        )
        self.model = LLM_MODEL
        self.no_think = LLM_NO_THINK

    def _build_messages(self, prompt: str) -> list[dict]:
        """Build message list with correct role structure for the configured model.

        Models whose GGUF chat template has no system-role slot (Mistral v0.x) get
        the /no_think prefix folded into the user turn instead.
        """
        if self.no_think:
            system = "/no_think"
            if any(p in self.model.lower() for p in _NO_SYSTEM_ROLE_PATTERNS):
                # Old Mistral [INST] template has no system slot — prepend to user turn
                return [{"role": "user", "content": f"{system}\n\n{prompt}"}]
            return [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ]
        return [{"role": "user", "content": prompt}]

    def generate_text(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text from LLM.

        Args:
            prompt: The input prompt
            json_mode: Whether to request JSON-formatted response
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            APIError: For API-related errors
            RateLimitError: For rate limiting
            Exception: For timeouts and other connection errors
        """
        if temperature is None:
            temperature = LLM_TEMPERATURE
        if max_tokens is None:
            max_tokens = LLM_MAX_TOKENS

        kwargs = {
            "model": self.model,
            "messages": self._build_messages(prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            # LM Studio requires json_schema (grammar-sampled by llama.cpp).
            # json_object is not supported and returns HTTP 400.
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "translation",
                    "strict": True,
                    "schema": _TRANSLATION_SCHEMA,
                },
            }

        try:
            if LLM_DEBUG:
                logger.debug(f"Sending prompt to {self.model} via {LLM_BASE_URL}")
                logger.debug(f"JSON mode: {json_mode}")

            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            # Strip <think>...</think> blocks produced by reasoning/thinking models
            content = _strip_think(content)
            if LLM_DEBUG:
                logger.debug(f"Received response: {content[:200]}...")

            return content

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except APIError as e:
            # Fall back to plain text mode if the provider doesn't support json_schema.
            if json_mode and e.status_code == 400:
                logger.warning("json_schema response_format not supported, retrying in text mode")
                kwargs.pop("response_format", None)
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return _strip_think(content)
            logger.error(f"API error: {e}")
            raise
        except Exception as e:
            # Handle timeouts and other connection errors
            if "timeout" in str(e).lower():
                logger.error(f"Request timeout: {e}")
            else:
                logger.error(f"Unexpected error: {e}")
            raise

    def generate_json(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate and parse JSON response from LLM.

        Args:
            prompt: The input prompt (should instruct JSON output)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If response is not valid JSON
            Same exceptions as generate_text
        """
        # Add JSON instruction to prompt if not present
        if "json" not in prompt.lower():
            prompt = f"{prompt}\n\nRespond with valid JSON only."

        response_text = self.generate_text(
            prompt=prompt,
            json_mode=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # With json_schema grammar sampling (LM Studio) the response is already valid JSON.
        # For other providers, _extract_json scans for embedded JSON in verbose output.
        parsed = _extract_json(response_text)
        if parsed is not None:
            return parsed

        logger.error(f"Failed to parse JSON response: {response_text}")
        raise ValueError(f"LLM returned invalid JSON: {response_text[:200]}")

# Global client instance
_client = None

def get_llm_client() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client

def ask_llm(
    prompt: str,
    json_mode: bool = False,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Convenience function to ask the LLM a question.

    Args:
        prompt: The input prompt
        json_mode: Whether to request JSON response
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text response
    """
    client = get_llm_client()
    return client.generate_text(
        prompt=prompt,
        json_mode=json_mode,
        temperature=temperature,
        max_tokens=max_tokens,
    )

def ask_llm_json(
    prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Convenience function to ask the LLM for JSON response.

    Args:
        prompt: The input prompt
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Parsed JSON dictionary
    """
    client = get_llm_client()
    return client.generate_json(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def ask_llm_json_free(
    prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Ask the LLM for a JSON response without schema enforcement.

    Use this for complex responses (vocab dicts, sentence arrays, validation
    reports) where the structure doesn't fit the fixed _TRANSLATION_SCHEMA.
    Falls back to _extract_json for parsing, which handles reasoning-model
    verbosity and code-fence wrapping.

    Args:
        prompt: The input prompt (should instruct JSON output)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If the response cannot be parsed as JSON
    """
    client = get_llm_client()
    # Use text mode — no schema enforcement so the LLM can return any shape
    response_text = client.generate_text(
        prompt=prompt,
        json_mode=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    parsed = _extract_json(response_text)
    if parsed is not None:
        return parsed
    raise ValueError(f"LLM returned invalid JSON: {response_text[:200]}")