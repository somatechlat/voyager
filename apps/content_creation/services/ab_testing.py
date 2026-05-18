"""A/B testing engine with statistical significance testing.

Creates A/B tests, tracks variant performance, and calculates winners
using chi-squared tests for statistical significance at p < 0.05.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def _chi_squared_pvalue(
    conversions_a: int,
    impressions_a: int,
    conversions_b: int,
    impressions_b: int,
) -> float:
    """Calculate chi-squared p-value for two proportions.

    Uses the chi-squared test of independence to determine whether
    the difference in conversion rates between two variants is
    statistically significant.

    Args:
        conversions_a: Conversions for variant A.
        impressions_a: Impressions for variant A.
        conversions_b: Conversions for variant B.
        impressions_b: Impressions for variant B.

    Returns:
        P-value (0-1).  < 0.05 indicates significance.
    """
    if impressions_a == 0 or impressions_b == 0:
        return 1.0

    # Observed
    non_conv_a = impressions_a - conversions_a
    non_conv_b = impressions_b - conversions_b

    # Expected
    total_conv = conversions_a + conversions_b
    total_non = non_conv_a + non_conv_b
    total_a = impressions_a
    total_b = impressions_b
    grand = total_a + total_b

    if grand == 0:
        return 1.0

    expected = [
        (total_a * total_conv) / grand,
        (total_a * total_non) / grand,
        (total_b * total_conv) / grand,
        (total_b * total_non) / grand,
    ]
    observed = [conversions_a, non_conv_a, conversions_b, non_conv_b]

    chi2 = 0.0
    for o, e in zip(observed, expected):
        if e > 0:
            chi2 += ((o - e) ** 2) / e

    # Approximate p-value from chi2 with 1 DOF
    # Wilson-Hilferty approximation
    if chi2 <= 0:
        return 1.0
    try:
        p = math.erfc(math.sqrt(chi2 / 2))
    except Exception:
        p = 1.0
    return min(1.0, max(0.0, p))


def create_test(
    name: str,
    content_generation_id: str,
    variants: list[dict[str, Any]],
    sample_size: int | None = None,
    winner_criteria: str = "ctr",
    start_date: str | None = None,
    end_date: str | None = None,
    tenant_id: str = "",
) -> dict[str, Any]:
    """Create a new A/B test configuration.

    Validates variant structure and returns test metadata.

    Args:
        name: Human-readable test name.
        content_generation_id: Base content UUID.
        variants: List of variant content objects.
        sample_size: Target impressions per variant.
        winner_criteria: Metric for winner selection.
        start_date: ISO start datetime.
        end_date: ISO end datetime.
        tenant_id: Tenant scope.

    Returns:
        Dict with test configuration and validation status.
    """
    if not variants or len(variants) < 2:
        return {
            "error": "At least 2 variants are required for A/B testing",
            "valid": False,
        }

    enriched_variants = []
    for i, v in enumerate(variants):
        enriched_variants.append({
            "variant_id": v.get("variant_id", f"variant_{i + 1}"),
            "name": v.get("name", f"Variant {i + 1}"),
            "content_text": v.get("content_text", ""),
            "content_html": v.get("content_html", ""),
            "image_url": v.get("image_url", ""),
            "impressions": v.get("impressions", 0),
            "clicks": v.get("clicks", 0),
            "conversions": v.get("conversions", 0),
            "engagement_score": v.get("engagement_score", 0.0),
        })

    return {
        "valid": True,
        "name": name,
        "content_generation_id": content_generation_id,
        "variants": enriched_variants,
        "variant_count": len(enriched_variants),
        "sample_size": sample_size,
        "winner_criteria": winner_criteria,
        "start_date": start_date,
        "end_date": end_date,
        "tenant_id": tenant_id,
    }


def calculate_winner(variants: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate the winning A/B test variant.

    Computes CTR, conversion rate, and engagement rate for each variant.
    Runs pairwise chi-squared tests between all combinations.

    Args:
        variants: List of variant performance data.

    Returns:
        Dict with winner, confidence, significance, and per-variant metrics.
    """
    if not variants:
        return {
            "winner": None,
            "significant": False,
            "message": "No variants provided",
        }

    # Compute metrics
    for v in variants:
        impressions = v.get("impressions", 0)
        clicks = v.get("clicks", 0)
        conversions = v.get("conversions", 0)
        likes = v.get("likes", 0)
        comments = v.get("comments", 0)
        shares = v.get("shares", 0)

        v["ctr"] = (clicks / impressions * 100) if impressions > 0 else 0.0
        v["conversion_rate"] = (conversions / clicks * 100) if clicks > 0 else 0.0
        v["engagement_rate"] = (
            ((likes + comments + shares) / impressions * 100)
            if impressions > 0
            else 0.0
        )

    # Sort by conversion rate (default winner criteria)
    sorted_variants = sorted(
        variants,
        key=lambda x: x.get("conversion_rate", 0.0),
        reverse=True,
    )
    leading = sorted_variants[0]

    # Pairwise chi-squared against all other variants
    sig_pairs = []
    for other in sorted_variants[1:]:
        p = _chi_squared_pvalue(
            leading.get("conversions", 0),
            max(leading.get("impressions", 0), 1),
            other.get("conversions", 0),
            max(other.get("impressions", 0), 1),
        )
        sig_pairs.append({
            "variant_a": leading.get("variant_id"),
            "variant_b": other.get("variant_id"),
            "p_value": round(p, 6),
            "significant": p < 0.05,
        })

    is_significant = any(p["significant"] for p in sig_pairs)

    if is_significant:
        min_p = min(p["p_value"] for p in sig_pairs if p["significant"])
        return {
            "winner": {
                "variant_id": leading.get("variant_id"),
                "name": leading.get("name"),
                "conversion_rate": round(leading.get("conversion_rate", 0.0), 4),
                "ctr": round(leading.get("ctr", 0.0), 4),
                "engagement_rate": round(leading.get("engagement_rate", 0.0), 4),
            },
            "confidence": round(1.0 - min_p, 4),
            "significant": True,
            "method": "chi_squared",
            "p_value": round(min_p, 6),
            "pairwise_results": sig_pairs,
            "variant_metrics": [
                {
                    "variant_id": v.get("variant_id"),
                    "name": v.get("name"),
                    "ctr": round(v.get("ctr", 0.0), 4),
                    "conversion_rate": round(v.get("conversion_rate", 0.0), 4),
                    "engagement_rate": round(v.get("engagement_rate", 0.0), 4),
                    "impressions": v.get("impressions", 0),
                    "clicks": v.get("clicks", 0),
                    "conversions": v.get("conversions", 0),
                }
                for v in variants
            ],
        }

    return {
        "winner": None,
        "significant": False,
        "message": "No statistically significant winner yet. "
                   "Collect more impressions per variant.",
        "pairwise_results": sig_pairs,
        "variant_metrics": [
            {
                "variant_id": v.get("variant_id"),
                "name": v.get("name"),
                "ctr": round(v.get("ctr", 0.0), 4),
                "conversion_rate": round(v.get("conversion_rate", 0.0), 4),
                "engagement_rate": round(v.get("engagement_rate", 0.0), 4),
                "impressions": v.get("impressions", 0),
            }
            for v in variants
        ],
    }
