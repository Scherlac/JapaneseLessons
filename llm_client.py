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

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_DEBUG,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_REQUEST_TIMEOUT,
    LLM_TEMPERATURE,
)

# Set up logging
logger = logging.getLogger(__name__)
if LLM_DEBUG:
    logging.basicConfig(level=logging.DEBUG)

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
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            if LLM_DEBUG:
                logger.debug(f"Sending prompt to {self.model} via {LLM_BASE_URL}")
                logger.debug(f"JSON mode: {json_mode}")

            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            # Strip <think>...</think> blocks produced by reasoning/thinking models
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if LLM_DEBUG:
                logger.debug(f"Received response: {content[:200]}...")

            return content

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except APIError as e:
            # Some providers (e.g. LM Studio) don't support json_object response_format.
            # Retry without it — the prompt already requests JSON output.
            if json_mode and e.status_code == 400:
                logger.warning("json_object response_format not supported, retrying in text mode")
                kwargs.pop("response_format", None)
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
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

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response_text}")
            raise ValueError(f"LLM returned invalid JSON: {e}") from e

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