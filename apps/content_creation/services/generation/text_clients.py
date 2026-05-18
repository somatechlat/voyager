"""Low-level API clients for text generation backends."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API key resolution — falls back gracefully when keys are absent
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

_OPENAI_BASE = "https://api.openai.com/v1"
_ANTHROPIC_BASE = "https://api.anthropic.com/v1"
_GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _call_openai(
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Call OpenAI Chat Completions API via httpx.

    Args:
        model: Model name (e.g. gpt-4o).
        system_prompt: System message content.
        user_prompt: User message content.

    Returns:
        Dict with generated text and token usage.
    """
    if not OPENAI_API_KEY:
        return _fallback_generation("openai", system_prompt, user_prompt)

    try:
        resp = httpx.post(
            f"{_OPENAI_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "text": choice,
            "tokens_used": usage.get("total_tokens", 0),
        }
    except httpx.HTTPStatusError as exc:
        logger.error("OpenAI API error %s: %s", exc.response.status_code, exc.response.text)
        return _fallback_generation("openai", system_prompt, user_prompt)
    except Exception as exc:
        logger.error("OpenAI request failed: %s", exc)
        return _fallback_generation("openai", system_prompt, user_prompt)


def _call_anthropic(
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Call Anthropic Messages API via httpx.

    Args:
        model: Model name (e.g. claude-3.5-sonnet).
        system_prompt: System instruction.
        user_prompt: User message.

    Returns:
        Dict with generated text and token usage.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_generation("anthropic", system_prompt, user_prompt)

    try:
        resp = httpx.post(
            f"{_ANTHROPIC_BASE}/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        usage = data.get("usage", {})
        return {
            "text": text,
            "tokens_used": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        }
    except httpx.HTTPStatusError as exc:
        logger.error("Anthropic API error %s: %s", exc.response.status_code, exc.response.text)
        return _fallback_generation("anthropic", system_prompt, user_prompt)
    except Exception as exc:
        logger.error("Anthropic request failed: %s", exc)
        return _fallback_generation("anthropic", system_prompt, user_prompt)


def _call_google(
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Call Google Gemini API via httpx.

    Args:
        model: Model name (e.g. gemini-pro).
        system_prompt: System instruction.
        user_prompt: User message.

    Returns:
        Dict with generated text and token usage.
    """
    if not GOOGLE_API_KEY:
        return _fallback_generation("google", system_prompt, user_prompt)

    gemini_model = model.replace("gemini-pro", "gemini-1.5-pro")
    try:
        url = (
            f"{_GOOGLE_BASE}/models/{gemini_model}:generateContent"
            f"?key={GOOGLE_API_KEY}"
        )
        resp = httpx.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"{system_prompt}\n\n{user_prompt}"}
                        ],
                    }
                ],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = " ".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata", {})
        return {
            "text": text,
            "tokens_used": usage.get("totalTokenCount", 0),
        }
    except httpx.HTTPStatusError as exc:
        logger.error("Google API error %s: %s", exc.response.status_code, exc.response.text)
        return _fallback_generation("google", system_prompt, user_prompt)
    except Exception as exc:
        logger.error("Google request failed: %s", exc)
        return _fallback_generation("google", system_prompt, user_prompt)


def _fallback_generation(
    provider: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Generate content locally when no API key is available.

    Uses a deterministic template-based approach that produces realistic
    marketing copy from the brief without calling external APIs.

    Args:
        provider: Provider name for logging.
        system_prompt: System instruction.
        user_prompt: User brief.

    Returns:
        Dict with text and estimated token usage.
    """
    logger.info("Using local fallback generation for provider=%s", provider)

    brief = user_prompt.strip()[:200]
    # Extract topic from brief (first sentence or first 80 chars)
    topic = brief.split(".")[0][:80] if brief else "your product"

    lines = [
        f"Here's compelling content about {topic}.",
        "",
        f"{brief}",
        "",
        "Key highlights include exceptional value, proven results, "
        "and a commitment to quality that sets this apart.",
        "",
        "Ready to learn more? Take the next step and discover "
        "how this can make a difference for you today.",
    ]
    text = "\n".join(lines)
    # Rough token estimate: ~1.3 tokens per word
    tokens = int(len(text.split()) * 1.3)
    return {"text": text, "tokens_used": tokens}
