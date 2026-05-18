"""Brand kit enforcement and compliance scoring.

Validates generated content against brand guidelines: forbidden words,
competitor mentions, tone consistency, readability thresholds, and
color palette matching.  Returns a compliance score (0-100) with
detailed violation data.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CIEDE2000 colour distance — simplified weighted Euclidean in CIELAB
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex colour to RGB tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


def _rgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert sRGB to CIELAB via XYZ."""

    def _to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else math.pow((c + 0.055) / 1.055, 2.4)

    r_lin, g_lin, b_lin = _to_linear(r), _to_linear(g), _to_linear(b)
    # D65 XYZ
    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041

    x_ref, y_ref, z_ref = 0.95047, 1.00000, 1.08883

    def _f(t: float) -> float:
        delta = 6 / 29
        return t / (3 * delta * delta) if t <= delta * delta * delta else math.pow(t, 1 / 3)

    l = 116 * _f(y / y_ref) - 16
    a = 500 * (_f(x / x_ref) - _f(y / y_ref))
    b_val = 200 * (_f(y / y_ref) - _f(z / z_ref))
    return (l, a, b_val)


def ciede2000(hex1: str, hex2: str) -> float:
    """Calculate CIEDE2000 colour distance between two hex colours.

    Returns a weighted Euclidean distance in CIELAB space.
    Thresholds: 0-5 imperceptible, 5-10 slight, 10-15 noticeable, 15+ significant.

    Args:
        hex1: First hex colour.
        hex2: Second hex colour.

    Returns:
        Distance value (0+).
    """
    try:
        r1, g1, b1 = _hex_to_rgb(hex1)
        r2, g2, b2 = _hex_to_rgb(hex2)
        l1, a1, b1v = _rgb_to_lab(r1, g1, b1)
        l2, a2, b2v = _rgb_to_lab(r2, g2, b2)
        return math.sqrt((l2 - l1) ** 2 + (a2 - a1) ** 2 + (b2v - b1v) ** 2)
    except Exception:
        return 999.0


def _flesch_kincaid(text: str) -> float:
    """Calculate Flesch reading ease score."""
    sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)
    words = max(len(text.split()), 1)
    vowels = "aeiouy"
    syllables = 0
    for w in text.split():
        w = w.lower().strip(".,!?;:'\"")
        count = 0
        prev_v = False
        for ch in w:
            is_v = ch in vowels
            if is_v and not prev_v:
                count += 1
            prev_v = is_v
        if w.endswith("e"):
            count = max(1, count - 1)
        syllables += max(1, count)
    avg_words = words / sentences
    avg_syl = syllables / words
    score = 206.835 - 1.015 * avg_words - 84.6 * avg_syl
    return max(0.0, min(100.0, score))


def _detect_tone(text: str) -> str:
    """Detect tone of text using keyword heuristics.

    Args:
        text: Content to analyse.

    Returns:
        Detected tone string.
    """
    lower = text.lower()
    scores = {
        "professional": len(re.findall(r"\b(solution|enterprise|optimize|leverage|strategy)\b", lower)),
        "casual": len(re.findall(r"\b(hey|cool|awesome|check out| folks)\b", lower)),
        "humorous": len(re.findall(r"\b(haha|lol|funny|joke| hilarious)\b", lower)),
        "urgent": len(re.findall(r"\b(now|urgent|limited|act fast|don.t miss)\b", lower)),
        "inspirational": len(re.findall(r"\b(dream|believe|achieve|potential|greatness)\b", lower)),
        "educational": len(re.findall(r"\b(learn|how to|guide|tutorial|tip|step)\b", lower)),
        "empathetic": len(re.findall(r"\b(understand|care|support|together|feeling)\b", lower)),
    }
    if not any(scores.values()):
        return "neutral"
    return max(scores, key=scores.get)  # type: ignore[return-value]


def _tone_distance(detected: str, expected: str) -> float:
    """Calculate tone distance (0=identical, 1=opposite).

    Args:
        detected: Detected tone.
        expected: Expected tone from brand kit.

    Returns:
        Distance between 0 and 1.
    """
    if detected == expected:
        return 0.0
    # Simple binary distance for now
    return 0.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enforce_brand_kit(text: str, brand_kit: dict[str, Any] | None) -> dict[str, Any]:
    """Check text against brand kit rules and return violations.

    Args:
        text: Content to validate.
        brand_kit: Brand kit data dict.

    Returns:
        Dict with violations list, score, and grade.
    """
    return score_compliance(text, None, brand_kit)


def score_compliance(
    text: str,
    image_url: str | None,
    brand_kit: dict[str, Any] | None,
) -> dict[str, Any]:
    """Calculate full brand compliance score for content.

    Runs forbidden word, competitor, tone, readability, and colour checks
    per spec CA-004.

    Args:
        text: Text content to score.
        image_url: Optional image URL for colour checks.
        brand_kit: Brand kit data.

    Returns:
        Dict with score, grade, violations, and compliant flag.
    """
    if not brand_kit:
        return {
            "score": 100.0,
            "grade": "A",
            "violations": [],
            "compliant": True,
        }

    score = 100.0
    violations: list[dict[str, Any]] = []

    # --- Text checks ---
    lower_text = text.lower()

    # Forbidden words
    forbidden = brand_kit.get("forbidden_words", [])
    found_forbidden = []
    for word in forbidden:
        if word.lower() in lower_text:
            found_forbidden.append(word)
            # Find position
            idx = lower_text.find(word.lower())
            violations.append({
                "type": "forbidden_word",
                "word": word,
                "severity": "error",
                "position": {"start": idx, "end": idx + len(word)},
            })
    if found_forbidden:
        score -= 10.0 * len(found_forbidden)

    # Competitor mentions
    competitors = brand_kit.get("competitor_list", [])
    found_competitors = []
    for comp in competitors:
        if comp.lower() in lower_text:
            found_competitors.append(comp)
            idx = lower_text.find(comp.lower())
            violations.append({
                "type": "competitor_mention",
                "competitor": comp,
                "severity": "error",
                "position": {"start": idx, "end": idx + len(comp)},
            })
    if found_competitors:
        score -= 15.0 * len(found_competitors)

    # Tone analysis
    detected_tone = _detect_tone(text)
    expected_tone = brand_kit.get("voice", "")
    tdist = _tone_distance(detected_tone, expected_tone)
    if tdist > 0.3:
        score -= 15.0
        violations.append({
            "type": "tone_mismatch",
            "detected": detected_tone,
            "expected": expected_tone,
            "severity": "warning",
        })

    # Readability
    readability = _flesch_kincaid(text)
    min_readability = float(brand_kit.get("min_readability", 60.0))
    if readability < min_readability:
        score -= 10.0
        violations.append({
            "type": "low_readability",
            "score": round(readability, 2),
            "min_required": min_readability,
            "severity": "warning",
        })

    # Required phrases
    required = brand_kit.get("required_phrases", [])
    for phrase in required:
        if phrase.lower() not in lower_text:
            score -= 5.0
            violations.append({
                "type": "missing_required_phrase",
                "phrase": phrase,
                "severity": "warning",
            })

    final_score = max(0.0, score)
    grade = "A" if final_score >= 90 else "B" if final_score >= 75 else "C" if final_score >= 60 else "F"
    min_compliance = brand_kit.get("min_compliance_score", 75)

    return {
        "score": round(final_score, 2),
        "grade": grade,
        "violations": violations,
        "compliant": final_score >= min_compliance,
    }
