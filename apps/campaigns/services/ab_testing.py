"""A/B testing statistical service.

Implements sample size calculation, frequentist (z-test) analysis,
and Bayesian (Beta-Binomial) analysis for campaign A/B tests.
"""

from __future__ import annotations

import logging
import math
import random
from math import sqrt
from typing import Any

from django.db import transaction

from apps.campaigns.models import CampaignABTest

logger = logging.getLogger(__name__)


def _z_score(cumulative_prob: float) -> float:
    """Approximate standard normal z-score from cumulative probability.

    Uses a rational approximation (Abramowitz and Stegun formula 26.2.23).

    Args:
        cumulative_prob: Cumulative probability (0 to 1).

    Returns:
        Approximate z-score.
    """
    import math

    if cumulative_prob <= 0:
        return -6.0
    if cumulative_prob >= 1:
        return 6.0
    if cumulative_prob < 0.5:
        p = cumulative_prob
        sign = -1.0
    else:
        p = 1.0 - cumulative_prob
        sign = 1.0

    # Constants for approximation
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    if p <= 0:
        p = 1e-10

    try:
        t = sqrt(-2.0 * math.log(p))
    except ValueError:
        t = 6.0

    poly = c0 + c1 * t + c2 * t * t
    denom = 1.0 + d1 * t + d2 * t * t + d3 * t * t * t
    z = t - poly / denom
    return sign * z


def _normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function.

    Args:
        x: Input value.

    Returns:
        CDF value between 0 and 1.
    """
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1.0 if x >= 0 else -1.0
    x = abs(x) / sqrt(2.0)

    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(
        -x * x
    )

    return 0.5 * (1.0 + sign * y)


def calculate_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    significance: float = 0.05,
    power: float = 0.80,
    num_variants: int = 2,
    daily_traffic: int | None = None,
) -> dict[str, Any]:
    """Calculate required sample size per variant for an A/B test.

    Uses the pooled proportion formula with Bonferroni correction
    for multiple comparisons.

    Args:
        baseline_rate: Current conversion rate (e.g. 0.05).
        minimum_detectable_effect: Relative lift to detect (e.g. 0.20).
        significance: Alpha level (default 0.05).
        power: Statistical power (default 0.80).
        num_variants: Number of test variants.
        daily_traffic: Expected daily visitors for duration estimate.

    Returns:
        Dict with sample_size_per_variant, total_sample_size,
        estimated_duration_days, minimum_detectable_effect.
    """
    p1 = baseline_rate
    p2 = baseline_rate * (1.0 + minimum_detectable_effect)

    # Clamp p2 to valid range
    p2 = min(p2, 0.9999)

    p_bar = (p1 + p2) / 2.0

    # Z-scores
    z_alpha = _z_score(1.0 - significance / 2.0)
    z_beta = _z_score(power)

    # Standard errors
    se_null = sqrt(2.0 * p_bar * (1.0 - p_bar))
    se_alt = sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))

    # Effect size
    delta = abs(p2 - p1)
    if delta < 1e-10:
        return {
            "sample_size_per_variant": 0,
            "total_sample_size": 0,
            "estimated_duration_days": 0,
            "minimum_detectable_effect": minimum_detectable_effect,
        }

    n = ((z_alpha * se_null + z_beta * se_alt) / delta) ** 2

    # Bonferroni correction for multiple comparisons
    if num_variants > 2:
        num_comparisons = num_variants - 1
        adjusted_alpha = significance / num_comparisons
        adj_z_alpha = _z_score(1.0 - adjusted_alpha / 2.0)
        n = ((adj_z_alpha * se_null + z_beta * se_alt) / delta) ** 2

    n_per_variant = max(1, int(math.ceil(n)))
    total = n_per_variant * num_variants

    duration_days = 0
    if daily_traffic and daily_traffic > 0:
        duration_days = max(1, int(math.ceil(total / daily_traffic)))

    return {
        "sample_size_per_variant": n_per_variant,
        "total_sample_size": total,
        "estimated_duration_days": duration_days,
        "minimum_detectable_effect": minimum_detectable_effect,
    }


def _frequentist_analysis(
    variants: list[dict[str, Any]],
    significance_level: float,
) -> list[dict[str, Any]]:
    """Run frequentist z-test analysis on variants.

    Performs pairwise z-tests between all variant combinations.

    Args:
        variants: List of variant dicts with conversions and visitors.
        significance_level: Alpha threshold.

    Returns:
        Variants augmented with z-statistic, p-value, significant flag.
    """
    results = []
    for i, variant_a in enumerate(variants):
        x1 = variant_a.get("conversions", 0)
        n1 = variant_a.get("visitors", 1)
        if n1 == 0:
            n1 = 1

        cr_a = x1 / n1
        variant_result = {**variant_a, "conversion_rate": round(cr_a, 6)}

        pairwise: list[dict[str, Any]] = []
        for j, variant_b in enumerate(variants):
            if i == j:
                continue
            x2 = variant_b.get("conversions", 0)
            n2 = variant_b.get("visitors", 1)
            if n2 == 0:
                n2 = 1

            cr_b = x2 / n2
            p_pooled = (x1 + x2) / (n1 + n2)
            se = sqrt(p_pooled * (1.0 - p_pooled) * (1.0 / n1 + 1.0 / n2))

            if se > 0:
                z_stat = (cr_a - cr_b) / se
                p_value = 2.0 * (1.0 - _normal_cdf(abs(z_stat)))
            else:
                z_stat = 0.0
                p_value = 1.0

            ci_low = (cr_a - cr_b) - 1.96 * se
            ci_high = (cr_a - cr_b) + 1.96 * se

            pairwise.append(
                {
                    "variant_id": variant_b.get("id"),
                    "z_statistic": round(z_stat, 6),
                    "p_value": round(p_value, 6),
                    "significant": p_value < significance_level,
                    "confidence_interval": [round(ci_low, 6), round(ci_high, 6)],
                    "conversion_rate_diff": round(cr_a - cr_b, 6),
                }
            )

        variant_result["pairwise"] = pairwise
        results.append(variant_result)

    return results


def _bayesian_analysis(
    variants: list[dict[str, Any]],
    simulations: int = 10000,
) -> list[dict[str, Any]]:
    """Run Bayesian Beta-Binomial analysis on variants.

    Uses Beta(1,1) prior with Monte Carlo simulation for
    probability of being best.

    Args:
        variants: List of variant dicts with conversions and visitors.
        simulations: Number of Monte Carlo draws.

    Returns:
        Variants augmented with posterior mean, credible interval,
        and probability of being best.
    """
    # Posterior parameters: Beta(1 + conversions, 1 + non_conversions)
    posteriors: list[dict[str, Any]] = []
    for variant in variants:
        conversions = variant.get("conversions", 0)
        visitors = variant.get("visitors", 0)
        alpha = 1.0 + conversions
        beta = 1.0 + max(0, visitors - conversions)
        mean = alpha / (alpha + beta)
        variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1.0))
        std = math.sqrt(variance) if variance > 0 else 0

        # 95% credible interval
        # Approximate using normal approximation for simplicity
        ci_low = max(0.0, mean - 1.96 * std)
        ci_high = min(1.0, mean + 1.96 * std)

        posteriors.append(
            {
                **variant,
                "alpha": alpha,
                "beta": beta,
                "mean_conversion_rate": round(mean, 6),
                "credible_interval_95": [round(ci_low, 6), round(ci_high, 6)],
            }
        )

    # Monte Carlo: probability of being best
    num_variants = len(posteriors)
    if num_variants == 0:
        return posteriors

    wins = [0] * num_variants

    for _ in range(simulations):
        draws: list[float] = []
        for p in posteriors:
            # Beta distribution via gamma sampling
            g1 = random.gammavariate(p["alpha"], 1.0)
            g2 = random.gammavariate(p["beta"], 1.0)
            if g1 + g2 == 0:
                draws.append(0.5)
            else:
                draws.append(g1 / (g1 + g2))

        best_idx = max(range(num_variants), key=lambda i: draws[i])
        wins[best_idx] += 1

    for i, p in enumerate(posteriors):
        p["probability_best"] = round(wins[i] / simulations, 6)

    return posteriors


def select_winner(
    variants: list[dict[str, Any]],
    criteria: str = "conversion_rate",
) -> dict[str, Any] | None:
    """Select the winning variant based on the chosen criteria.

    Args:
        variants: List of analyzed variants.
        criteria: Metric to use for winner selection.

    Returns:
        The winning variant dict, or None.
    """
    if not variants:
        return None

    if criteria == "conversion_rate":
        return max(variants, key=lambda v: v.get("conversions", 0) / max(1, v.get("visitors", 1)))
    if criteria == "probability_best":
        return max(variants, key=lambda v: v.get("probability_best", 0.0))
    if criteria == "revenue":
        return max(variants, key=lambda v: v.get("revenue", 0.0))
    if criteria == "roas":
        return max(variants, key=lambda v: v.get("roas", 0.0))
    if criteria == "engagement":
        return max(variants, key=lambda v: v.get("engagement_actions", 0))

    return max(variants, key=lambda v: v.get("conversions", 0))


@transaction.atomic
def evaluate_test_results(test: CampaignABTest) -> dict[str, Any]:
    """Evaluate A/B test results using the configured statistical method.

    Args:
        test: The A/B test to evaluate.

    Returns:
        Dict with winner, results per variant, and method used.
    """
    variants = test.variants if isinstance(test.variants, list) else []
    if not variants:
        return {"winner": None, "results": [], "method": test.method, "error": "No variants"}

    if test.method == CampaignABTest.Method.FREQUENTIST:
        analyzed = _frequentist_analysis(variants, float(test.significance_level))
    elif test.method == CampaignABTest.Method.BAYESIAN:
        analyzed = _bayesian_analysis(variants)
    else:
        return {"winner": None, "results": [], "method": test.method, "error": "Unknown method"}

    winner = select_winner(analyzed, test.winner_criteria)

    # Persist results
    test.results = {
        "method": test.method,
        "criteria": test.winner_criteria,
        "variants": analyzed,
        "winner_variant_id": winner.get("id") if winner else None,
    }
    if winner:
        test.winner_variant_id = winner.get("id", "")
    test.save(update_fields=["results", "winner_variant_id", "updated_at"])

    return {
        "winner": winner,
        "results": analyzed,
        "method": test.method,
    }


def compute_and_save_sample_size(
    test: CampaignABTest,
    daily_traffic: int | None = None,
) -> dict[str, Any]:
    """Compute sample size and update the test record.

    Args:
        test: The A/B test.
        daily_traffic: Expected daily traffic.

    Returns:
        Sample size calculation result.
    """
    if test.baseline_rate is None or test.minimum_detectable_effect is None:
        return {
            "error": "baseline_rate and minimum_detectable_effect are required",
        }

    num_variants = len(test.variants) if isinstance(test.variants, list) and test.variants else 2

    result = calculate_sample_size(
        baseline_rate=float(test.baseline_rate),
        minimum_detectable_effect=float(test.minimum_detectable_effect),
        significance=float(test.significance_level),
        power=float(test.power),
        num_variants=num_variants,
        daily_traffic=daily_traffic or test.daily_traffic,
    )

    test.sample_size_per_variant = result["sample_size_per_variant"]
    test.estimated_duration_days = result["estimated_duration_days"]
    test.save(update_fields=["sample_size_per_variant", "estimated_duration_days", "updated_at"])

    return result
