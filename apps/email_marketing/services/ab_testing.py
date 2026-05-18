"""A/B testing service with statistical testing.

Handles sample size calculation, chi-squared significance testing,
winner selection, and lift calculation for email experiments.
"""

from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------------------
# Sample size calculation
# ---------------------------------------------------------------------------


def calculate_sample_size(
    baseline_rate: float,
    mde: float,
    confidence: float = 0.95,
    power: float = 0.80,
) -> dict[str, Any]:
    """Calculate required sample size per variant for an A/B test.

    Uses the standard two-proportion z-test formula.

    Args:
        baseline_rate: Expected baseline conversion rate (0-1).
        mde: Minimum detectable effect as relative lift (e.g. 0.1 for 10%).
        confidence: Statistical confidence level.
        power: Statistical power (1 - beta).

    Returns:
        Dict with sample_per_variant, total_sample, and notes.
    """
    if baseline_rate <= 0 or baseline_rate >= 1:
        return {
            "sample_per_variant": 0,
            "total_sample": 0,
            "error": "Baseline rate must be between 0 and 1",
        }
    if mde <= 0:
        return {
            "sample_per_variant": 0,
            "total_sample": 0,
            "error": "MDE must be positive",
        }
    z_alpha = _z_score(1 - (1 - confidence) / 2)
    z_beta = _z_score(power)
    p1 = baseline_rate
    p2 = min(baseline_rate * (1 + mde), 0.9999)
    p_bar = (p1 + p2) / 2
    n = (
        (
            z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
            + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        )
        ** 2
    ) / ((p2 - p1) ** 2)
    sample_per_variant = math.ceil(n)
    return {
        "sample_per_variant": sample_per_variant,
        "total_sample": sample_per_variant * 2,
        "baseline_rate": baseline_rate,
        "mde": mde,
        "confidence": confidence,
        "power": power,
    }


def _z_score(cdf: float) -> float:
    """Approximate the z-score for a given CDF value.

    Uses the Beasley-Springer-Moro approximation.

    Args:
        cdf: Cumulative probability (0-1).

    Returns:
        Z-score.
    """
    if cdf <= 0:
        return -6.0
    if cdf >= 1:
        return 6.0
    if cdf == 0.5:
        return 0.0
    a = [
        2.50662823884,
        -18.61500062529,
        41.39119773534,
        -25.44106049637,
    ]
    b = [
        -8.47351093090,
        23.08336743743,
        -21.06224101826,
        3.13082909833,
    ]
    c = [
        0.3374754822726147,
        0.9761690190917186,
        0.1607979714918209,
        0.0276438810333863,
        0.0038405729373609,
        0.0003951896511919,
        0.0000321767881768,
        0.0000002888167364,
        0.0000003960315187,
    ]
    y = cdf - 0.5
    if abs(y) < 0.42:
        r = y * y
        return (
            y
            * (((a[3] * r + a[2]) * r + a[1]) * r + a[0])
            / ((((b[3] * r + b[2]) * r + b[1]) * r + b[0]) * r + 1)
        )
    r = cdf if y < 0 else 1 - cdf
    r = math.log(-math.log(r))
    x = c[0] + r * (
        c[1]
        + r * (c[2] + r * (c[3] + r * (c[4] + r * (c[5] + r * (c[6] + r * (c[7] + r * c[8]))))))
    )
    return -x if y < 0 else x


# ---------------------------------------------------------------------------
# Chi-squared test
# ---------------------------------------------------------------------------


def chi_squared_test(
    control_conversions: int,
    control_total: int,
    variant_conversions: int,
    variant_total: int,
) -> dict[str, Any]:
    """Perform a chi-squared test for two proportions.

    Args:
        control_conversions: Conversions in control group.
        control_total: Total in control group.
        variant_conversions: Conversions in variant group.
        variant_total: Total in variant group.

    Returns:
        Dict with chi2 statistic, p-value, significant flag, and rates.
    """
    if control_total == 0 or variant_total == 0:
        return {
            "chi2": 0.0,
            "p_value": 1.0,
            "significant": False,
            "control_rate": 0.0,
            "variant_rate": 0.0,
        }
    control_non = control_total - control_conversions
    variant_non = variant_total - variant_conversions
    row1 = control_conversions + variant_conversions
    row2 = control_non + variant_non
    col1 = control_total
    col2 = variant_total
    total = col1 + col2
    if total == 0:
        return {
            "chi2": 0.0,
            "p_value": 1.0,
            "significant": False,
            "control_rate": 0.0,
            "variant_rate": 0.0,
        }
    expected_11 = col1 * row1 / total
    expected_12 = col2 * row1 / total
    expected_21 = col1 * row2 / total
    expected_22 = col2 * row2 / total
    cells = [
        (control_conversions, expected_11),
        (variant_conversions, expected_12),
        (control_non, expected_21),
        (variant_non, expected_22),
    ]
    chi2 = sum((obs - exp) ** 2 / exp for obs, exp in cells if exp > 0)
    p_value = _chi2_cdf(1, chi2)
    control_rate = control_conversions / control_total
    variant_rate = variant_conversions / variant_total
    significant = p_value < 0.05 and chi2 > 3.841
    return {
        "chi2": round(chi2, 6),
        "p_value": round(p_value, 6),
        "significant": significant,
        "control_rate": round(control_rate, 6),
        "variant_rate": round(variant_rate, 6),
        "control_total": control_total,
        "variant_total": variant_total,
    }


def _chi2_cdf(k: int, x: float) -> float:
    """Upper tail probability for chi-squared distribution.

    Uses the incomplete gamma function approximation.

    Args:
        k: Degrees of freedom.
        x: Chi-squared statistic.

    Returns:
        P-value (upper tail probability).
    """
    if x <= 0:
        return 1.0
    return math.exp(-x / 2) * sum((x / 2) ** i / math.factorial(i) for i in range(k // 2 + 1))


# ---------------------------------------------------------------------------
# Winner selection
# ---------------------------------------------------------------------------


def select_winner(
    variants: list[dict[str, Any]],
    metric: str = "opens",
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Select the winning variant from A/B test results.

    Compares each variant against the control (first variant)
    using chi-squared testing.

    Args:
        variants: List of variant result dicts with metric counts and totals.
        metric: Metric to compare (opens, clicks, conversions).
        confidence_level: Required confidence level.

    Returns:
        Dict with winner variant, test results, and significance.
    """
    if len(variants) < 2:
        return {"winner": variants[0] if variants else None, "significant": False, "tests": []}
    control = variants[0]
    control_conversions = control.get(metric, 0)
    control_total = control.get("sent", 1)
    tests = []
    best_variant = control
    best_rate = control_conversions / control_total if control_total > 0 else 0
    for variant in variants[1:]:
        var_conversions = variant.get(metric, 0)
        var_total = variant.get("sent", 1)
        result = chi_squared_test(
            control_conversions,
            control_total,
            var_conversions,
            var_total,
        )
        result["variant_id"] = variant.get("id")
        result["control_id"] = control.get("id")
        tests.append(result)
        var_rate = var_conversions / var_total if var_total > 0 else 0
        if result["significant"] and var_rate > best_rate:
            best_rate = var_rate
            best_variant = variant
    any_significant = any(t["significant"] for t in tests)
    return {
        "winner": best_variant,
        "significant": any_significant,
        "confidence_level": confidence_level,
        "tests": tests,
    }


def calculate_lift(
    control_value: float,
    variant_value: float,
) -> dict[str, Any]:
    """Calculate percentage lift of variant over control.

    Args:
        control_value: Control metric value.
        variant_value: Variant metric value.

    Returns:
        Dict with absolute lift and percentage lift.
    """
    if control_value == 0:
        return {"absolute_lift": variant_value, "pct_lift": 0.0}
    absolute = variant_value - control_value
    pct = ((variant_value - control_value) / control_value) * 100.0
    return {"absolute_lift": round(absolute, 6), "pct_lift": round(pct, 2)}
