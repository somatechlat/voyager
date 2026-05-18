"""Text generation with multi-model routing and quality scoring."""

from __future__ import annotations

import logging
import time
from typing import Any

from .text_clients import (
    _call_anthropic,
    _call_google,
    _call_openai,
    _fallback_generation,
)

logger = logging.getLogger(__name__)

# Platform character limits per spec
PLATFORM_LIMITS: dict[str, int] = {
    "instagram": 2200,
    "tiktok": 2200,
    "linkedin": 3000,
    "twitter": 280,
    "facebook": 63206,
    "youtube": 5000,
    "pinterest": 500,
    "threads": 500,
    "email": 10000,
    "blog": 10000,
}

# Model routing rules per spec CA-001
LONG_FORM_TYPES = {"blog", "press_release", "product_description", "newsletter"}


def _select_model(content_type: str, language: str) -> str:
    """Select the optimal model based on content type and language.

    Routing rules:
        - Long-form (blog, press_release, product_description) → Claude 3.5
        - Ad copy / social post in non-English → GPT-4o (multilingual)
        - Video script → GPT-4o (structured output)
        - Default → Claude 3.5 (best marketing copy)

    Args:
        content_type: The content type enum value.
        language: ISO 639-1 language code.

    Returns:
        Model identifier string.
    """
    if content_type in LONG_FORM_TYPES:
        return "claude-3.5-sonnet"
    if content_type in {"ad_copy", "social_post"} and language != "en":
        return "gpt-4o"
    if content_type == "video_script":
        return "gpt-4o"
    return "claude-3.5-sonnet"


def _build_system_prompt(
    brand_kit: dict[str, Any] | None,
    tone: str,
    seo_keywords: list[str],
    content_type: str,
    platforms: list[str],
) -> str:
    """Assemble a system prompt from brand kit, tone, and constraints.

    Args:
        brand_kit: Loaded brand kit data or None.
        tone: Desired tone (overridden by brand kit if present).
        seo_keywords: Keywords to integrate.
        content_type: Target content type.
        platforms: Target platforms.

    Returns:
        System prompt string ready for the model.
    """
    parts: list[str] = []
    parts.append("You are an expert marketing copywriter. "
                 "Generate high-quality, engaging content.")

    effective_tone = tone
    if brand_kit:
        effective_tone = brand_kit.get("voice", tone)
        if brand_kit.get("forbidden_words"):
            parts.append(
                "NEVER use these words: "
                f"{', '.join(brand_kit['forbidden_words'])}."
            )
        if brand_kit.get("required_phrases"):
            parts.append(
                "Include these phrases naturally: "
                f"{', '.join(brand_kit['required_phrases'])}."
            )
        if brand_kit.get("tone_rules"):
            rules = brand_kit["tone_rules"]
            if isinstance(rules, list):
                parts.append("Tone rules: " + "; ".join(str(r) for r in rules))
            else:
                parts.append(f"Tone rules: {rules}")

    parts.append(f"Tone: {effective_tone}.")
    parts.append(f"Content type: {content_type}.")
    if platforms:
        limits = []
        for p in platforms:
            limit = PLATFORM_LIMITS.get(p, "")
            if limit:
                limits.append(f"{p}: {limit} chars")
        if limits:
            parts.append("Platform limits — " + ", ".join(limits) + ".")
    if seo_keywords:
        parts.append(
            f"Integrate these SEO keywords naturally (1-3% density): "
            f"{', '.join(seo_keywords)}."
        )

    return "\n\n".join(parts)


def _flesch_kincaid(text: str) -> float:
    """Calculate Flesch-Kincaid reading ease score.

    Higher = easier to read.  60-70 is standard.  0-100 scale.

    Args:
        text: Input text to score.

    Returns:
        Flesch reading ease score.
    """
    sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)
    words = max(len(text.split()), 1)
    syllables = sum(max(1, _count_syllables(w)) for w in text.split())
    avg_words_per_sentence = words / sentences
    avg_syllables_per_word = syllables / words
    score = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
    return max(0.0, min(100.0, score))


def _count_syllables(word: str) -> int:
    """Approximate syllable count for a word."""
    word = word.lower().strip(".,!?;:'\"")
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_v = ch in vowels
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    if word.endswith("e"):
        count = max(1, count - 1)
    return max(1, count)


def _seo_density(text: str, keywords: list[str]) -> float:
    """Calculate SEO keyword density as a percentage.

    Args:
        text: Generated content.
        keywords: Target keywords.

    Returns:
        Density percentage (0-100).
    """
    if not keywords or not text:
        return 0.0
    words = text.lower().split()
    if not words:
        return 0.0
    total = len(words)
    hits = sum(1 for w in words if any(kw.lower() in w for kw in keywords))
    return (hits / total) * 100


def _predict_engagement(text: str, content_type: str) -> float:
    """Predict engagement score (0-100) using a heuristic model.

    Factors: length appropriateness, question marks (engagement hooks),
    emoji presence, CTA presence.

    Args:
        text: Generated content.
        content_type: Type of content.

    Returns:
        Engagement prediction score.
    """
    score = 50.0
    if "?" in text:
        score += 10
    if any(c in text for c in ["!", "🚀", "✨", "🔥", "💡"]):
        score += 10
    if any(w in text.lower() for w in ["click", "learn", "discover", "try", "get"]):
        score += 10
    if 50 <= len(text) <= 500:
        score += 15
    elif len(text) > 1000:
        score -= 10
    return max(0.0, min(100.0, score))


def _scan_forbidden_words(text: str, forbidden: list[str]) -> list[dict[str, Any]]:
    """Scan text for forbidden words.

    Args:
        text: Content to scan.
        forbidden: List of forbidden words.

    Returns:
        List of violation dicts with word, position, severity.
    """
    violations = []
    lower_text = text.lower()
    for word in forbidden:
        idx = lower_text.find(word.lower())
        if idx >= 0:
            violations.append({
                "type": "forbidden_word",
                "word": word,
                "position": {"start": idx, "end": idx + len(word)},
                "severity": "error",
            })
    return violations


def _scan_competitors(text: str, competitors: list[str]) -> list[dict[str, Any]]:
    """Scan text for competitor mentions.

    Args:
        text: Content to scan.
        competitors: List of competitor names.

    Returns:
        List of violation dicts.
    """
    violations = []
    lower_text = text.lower()
    for comp in competitors:
        idx = lower_text.find(comp.lower())
        if idx >= 0:
            violations.append({
                "type": "competitor_mention",
                "competitor": comp,
                "position": {"start": idx, "end": idx + len(comp)},
                "severity": "error",
            })
    return violations


def generate_text(
    brief: str,
    content_type: str,
    platforms: list[str],
    brand_kit: dict[str, Any] | None = None,
    tone: str = "professional",
    language: str = "en",
    max_length: int | None = None,
    seo_keywords: list[str] | None = None,
    include_cta: bool = True,
    variations: int = 1,
) -> dict[str, Any]:
    """Generate marketing text via multi-model routing.

    Selects the optimal model, constructs a system prompt with brand
    enforcement, calls the model API, and post-processes the result
    with readability, engagement, SEO, and compliance scoring.

    Args:
        brief: Content brief (10-5000 chars).
        content_type: Type of content.
        platforms: Target platforms.
        brand_kit: Optional brand kit data.
        tone: Desired tone.
        language: ISO 639-1 language code.
        max_length: Maximum character length.
        seo_keywords: SEO keywords to integrate.
        include_cta: Whether to include a call-to-action.
        variations: Number of variations (1-5).

    Returns:
        Dict with generated text, metadata, scores, and warnings.
    """
    start_time = time.monotonic()
    model = _select_model(content_type, language)
    keywords = seo_keywords or []

    system_prompt = _build_system_prompt(
        brand_kit, tone, keywords, content_type, platforms
    )
    user_prompt = brief
    if include_cta:
        user_prompt += (
            "\n\nInclude a clear call-to-action at the end."
        )

    result = _call_text_model(model, system_prompt, user_prompt, language)
    text = result.get("text", "")

    generation_time_ms = int((time.monotonic() - start_time) * 1000)

    # Post-processing
    warnings: list[dict[str, Any]] = []
    if brand_kit:
        warnings.extend(_scan_forbidden_words(
            text, brand_kit.get("forbidden_words", [])
        ))
        warnings.extend(_scan_competitors(
            text, brand_kit.get("competitor_list", [])
        ))

    readability = _flesch_kincaid(text)
    seo_density_val = _seo_density(text, keywords)
    seo_score = 100.0 if 1.0 <= seo_density_val <= 3.0 else 50.0
    engagement = _predict_engagement(text, content_type)

    platform_adaptations = []
    for platform in platforms:
        limit = PLATFORM_LIMITS.get(platform)
        adapted = text
        within_limit = True
        if limit and len(adapted) > limit:
            adapted = adapted[: limit - 3] + "..."
            within_limit = False
            warnings.append({
                "type": "length_exceeded",
                "message": f"{platform}: text truncated to {limit} chars",
                "severity": "warning",
            })
        platform_adaptations.append({
            "platform": platform,
            "adapted_text": adapted,
            "character_count": len(adapted),
            "within_limit": within_limit,
        })

    overall_quality = (readability + engagement + seo_score) / 3.0
    if warnings:
        overall_quality = max(0.0, overall_quality - len(warnings) * 5)

    return {
        "text": text,
        "model_used": model,
        "tokens_used": result.get("tokens_used", 0),
        "generation_time_ms": generation_time_ms,
        "language": language,
        "word_count": len(text.split()),
        "character_count": len(text),
        "scores": {
            "readability": round(readability, 2),
            "engagement_prediction": round(engagement, 2),
            "brand_compliance": 100.0 - len(warnings) * 10,
            "seo_score": round(seo_score, 2),
            "overall_quality": round(overall_quality, 2),
        },
        "platforms": platform_adaptations,
        "warnings": warnings,
        "variations": [],
    }


def _call_text_model(
    model: str,
    system_prompt: str,
    user_prompt: str,
    language: str = "en",
) -> dict[str, Any]:
    """Call the appropriate model API via httpx.

    Routes to OpenAI, Anthropic, or Google based on model name.
    Falls back to a local generation when no API key is configured.

    Args:
        model: Model identifier.
        system_prompt: System/instruction prompt.
        user_prompt: User content brief.
        language: Language code.

    Returns:
        Dict with ``text`` and ``tokens_used``.
    """
    if "gpt" in model.lower() or model.startswith("gpt-"):
        return _call_openai(model, system_prompt, user_prompt)
    if "claude" in model.lower():
        return _call_anthropic(model, system_prompt, user_prompt)
    if "gemini" in model.lower():
        return _call_google(model, system_prompt, user_prompt)
    # Default to Claude
    return _call_anthropic(model, system_prompt, user_prompt)
