"""Thin wrapper around the Groq chat-completions API.

Used only for the two generation steps that are NOT memory reasoning:
the "without memory" baseline (deliberately has no Hindsight context, so
the before/after demo has a real, honest contrast) and appeal-draft
generation. The "with memory" strategy comes from Hindsight's own
reflect() — see app/memory/hindsight_client.py — not from here.
"""

from groq import Groq, GroqError

from app.core.config import get_settings


class LLMError(Exception):
    """Raised when the LLM call fails, so callers can degrade gracefully
    instead of crashing the request (see Phase 22 error-handling rule:
    every external dependency should fail gracefully)."""


def chat_completion(system: str, user: str, *, temperature: float = 0.3, max_completion_tokens: int = 1200) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise LLMError("GROQ_API_KEY is not configured")

    client = Groq(api_key=settings.groq_api_key)
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )
    except GroqError as exc:
        # The SDK already retries transient failures (max_retries=2 by default);
        # anything that reaches here is worth surfacing, not silently swallowing.
        raise LLMError(f"LLM call failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise LLMError("LLM returned an empty response")
    return content
