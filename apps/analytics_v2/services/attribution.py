"""Attribution modeling service — 6 attribution models.

Implements First-Touch, Last-Touch, Linear, Time-Decay, Position-Based
(U-Shaped), and Data-Driven (Markov Chain) attribution models for
assigning conversion credit across touchpoints.
"""

from __future__ import annotations

import logging
import math
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

from apps.analytics_v2.models.attribution import AttributionModel, ConversionPath, Touchpoint

logger = logging.getLogger(__name__)

# Default model-specific parameters
DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "time_decay": {"half_life_days": 7},
    "position_based": {"first_weight": 0.4, "last_weight": 0.4, "middle_weight": 0.2},
}


def calculate_attribution(
    touchpoints: list[dict[str, Any]],
    conversion_date: datetime,
    conversion_value: float,
    model_type: str,
    model_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Calculate attribution credits for a set of touchpoints.

    Applies the specified attribution model to distribute conversion credit
    across all touchpoints in the conversion journey.

    Args:
        touchpoints: Ordered list of touchpoint dicts with channel, platform,
            campaign, timestamp keys.
        conversion_date: When the conversion occurred.
        conversion_value: Monetary value of the conversion.
        model_type: Attribution model type identifier.
        model_config: Optional model-specific parameters.

    Returns:
        List of touchpoints with credit and revenue_attributed fields added.
    """
    if not touchpoints:
        return []

    cfg = model_config or {}
    sorted_tps = sorted(touchpoints, key=lambda t: t.get("timestamp", datetime.min))

    if model_type == "first_touch":
        credited = _first_touch(sorted_tps)
    elif model_type == "last_touch":
        credited = _last_touch(sorted_tps)
    elif model_type == "linear":
        credited = _linear(sorted_tps)
    elif model_type == "time_decay":
        half_life = cfg.get("half_life_days", DEFAULT_CONFIG["time_decay"]["half_life_days"])
        credited = _time_decay(sorted_tps, conversion_date, half_life)
    elif model_type == "position_based":
        first_w = cfg.get("first_weight", DEFAULT_CONFIG["position_based"]["first_weight"])
        last_w = cfg.get("last_weight", DEFAULT_CONFIG["position_based"]["last_weight"])
        credited = _position_based(sorted_tps, first_w, last_w)
    elif model_type == "data_driven":
        credited = _data_driven(sorted_tps)
    else:
        logger.warning("Unknown attribution model: %s, falling back to last_touch", model_type)
        credited = _last_touch(sorted_tps)

    # Calculate attributed revenue
    for tp in credited:
        tp["revenue_attributed"] = conversion_value * tp.get("credit", 0)

    return credited


def _first_touch(touchpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """First-Touch: 100% credit to the first touchpoint.

    Args:
        touchpoints: Ordered list of touchpoints.

    Returns:
        Touchpoints with credit assigned.
    """
    result = deepcopy(touchpoints)
    if result:
        for i, tp in enumerate(result):
            tp["credit"] = 1.0 if i == 0 else 0.0
    return result


def _last_touch(touchpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Last-Touch: 100% credit to the last touchpoint.

    Args:
        touchpoints: Ordered list of touchpoints.

    Returns:
        Touchpoints with credit assigned.
    """
    result = deepcopy(touchpoints)
    if result:
        for i, tp in enumerate(result):
            tp["credit"] = 1.0 if i == len(result) - 1 else 0.0
    return result


def _linear(touchpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Linear: Equal credit to all touchpoints.

    Args:
        touchpoints: Ordered list of touchpoints.

    Returns:
        Touchpoints with equal credit assigned.
    """
    result = deepcopy(touchpoints)
    if result:
        credit = 1.0 / len(result)
        for tp in result:
            tp["credit"] = credit
    return result


def _time_decay(
    touchpoints: list[dict[str, Any]],
    conversion_date: datetime,
    half_life: float = 7,
) -> list[dict[str, Any]]:
    """Time-Decay: More credit to touchpoints closer to conversion.

    Uses exponential decay: weight = 2^(-days_before_conversion / half_life).

    Args:
        touchpoints: Ordered list of touchpoints.
        conversion_date: When the conversion occurred.
        half_life: Number of days for credit to halve.

    Returns:
        Touchpoints with decay-weighted credit assigned.
    """
    result = deepcopy(touchpoints)
    if not result:
        return result

    weights = []
    for tp in result:
        ts = tp.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        days_before = max(0, (conversion_date - ts).total_seconds() / 86400)
        weight = 2 ** (-days_before / half_life)
        tp["weight"] = weight
        weights.append(weight)

    total_weight = sum(weights)
    if total_weight > 0:
        for tp in result:
            tp["credit"] = tp["weight"] / total_weight
    else:
        for tp in result:
            tp["credit"] = 1.0 / len(result)

    return result


def _position_based(
    touchpoints: list[dict[str, Any]],
    first_weight: float = 0.4,
    last_weight: float = 0.4,
) -> list[dict[str, Any]]:
    """Position-Based (U-Shaped): First and last get highest credit.

    Default: 40% first, 40% last, 20% distributed among middle touchpoints.
    For 1 touchpoint: 100%. For 2: 50/50.

    Args:
        touchpoints: Ordered list of touchpoints.
        first_weight: Credit proportion for the first touchpoint.
        last_weight: Credit proportion for the last touchpoint.

    Returns:
        Touchpoints with position-based credit assigned.
    """
    result = deepcopy(touchpoints)
    n = len(result)
    if n == 0:
        return result
    if n == 1:
        result[0]["credit"] = 1.0
    elif n == 2:
        result[0]["credit"] = 0.5
        result[1]["credit"] = 0.5
    else:
        middle_weight = 1.0 - first_weight - last_weight
        middle_count = n - 2
        result[0]["credit"] = first_weight
        result[-1]["credit"] = last_weight
        if middle_count > 0 and middle_weight > 0:
            middle_credit = middle_weight / middle_count
            for i in range(1, n - 1):
                result[i]["credit"] = middle_credit
        else:
            # Redistribute if no middle weight
            result[0]["credit"] += middle_weight / 2
            result[-1]["credit"] += middle_weight / 2
    return result


def _data_driven(touchpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Data-Driven (Markov Chain): Uses transition probabilities.

    Builds a simple transition matrix from touchpoint sequences and
    calculates removal effect for each unique channel.

    Args:
        touchpoints: Ordered list of touchpoints.

    Returns:
        Touchpoints with data-driven credit assigned.
    """
    result = deepcopy(touchpoints)
    if not result:
        return result

    # Extract unique channels
    channels = list(dict.fromkeys(tp.get("channel", "unknown") for tp in result))
    n = len(channels)
    if n == 0:
        return result
    if n == 1:
        for tp in result:
            tp["credit"] = 1.0
        return result

    # Build transition counts
    transitions: dict[str, dict[str, float]] = {c: {} for c in channels + ["start", "conversion", "null"]}
    prev = "start"
    for tp in result:
        ch = tp.get("channel", "unknown")
        transitions[prev][ch] = transitions[prev].get(ch, 0) + 1
        prev = ch
    transitions[prev]["conversion"] = transitions[prev].get("conversion", 0) + 1

    # Add null exits
    for ch in channels:
        total_out = sum(transitions[ch].values())
        if total_out > 0:
            transitions[ch]["null"] = transitions[ch].get("null", 0) + 1

    # Normalize to probabilities
    probs: dict[str, dict[str, float]] = {}
    for ch_from, targets in transitions.items():
        total = sum(targets.values())
        if total > 0:
            probs[ch_from] = {ch_to: count / total for ch_to, count in targets.items()}
        else:
            probs[ch_from] = {}

    # Calculate conversion probability with all channels
    full_rate = _markov_conversion_rate(probs, channels)

    # Calculate removal effect for each channel
    removal_effects = {}
    for ch in channels:
        modified_probs = _remove_channel(probs, ch)
        modified_rate = _markov_conversion_rate(modified_probs, [c for c in channels if c != ch])
        removal_effects[ch] = max(0, full_rate - modified_rate)

    # Normalize removal effects to credits
    total_effect = sum(removal_effects.values())
    channel_credits = {ch: (eff / total_effect if total_effect > 0 else 1.0 / n) for ch, eff in removal_effects.items()}

    # Distribute channel credits to individual touchpoints
    for tp in result:
        ch = tp.get("channel", "unknown")
        tp["credit"] = channel_credits.get(ch, 0)
        tp["removal_effect"] = removal_effects.get(ch, 0)

    return result


def _markov_conversion_rate(
    probs: dict[str, dict[str, float]],
    channels: list[str],
    max_steps: int = 100,
) -> float:
    """Calculate conversion probability using Markov chain absorption.

    Args:
        probs: Transition probability matrix.
        channels: Active channel names.
        max_steps: Maximum path length to simulate.

    Returns:
        Conversion probability (0.0-1.0).
    """
    # Simulate paths from start state
    conv_prob = 0.0
    state_probs: dict[str, float] = {"start": 1.0}

    for _ in range(max_steps):
        new_state_probs: dict[str, float] = {}
        for state, prob in state_probs.items():
            if state in ("conversion", "null"):
                continue
            for next_state, trans_prob in probs.get(state, {}).items():
                if next_state == "conversion":
                    conv_prob += prob * trans_prob
                elif next_state != "null":
                    new_state_probs[next_state] = new_state_probs.get(next_state, 0) + prob * trans_prob
        state_probs = new_state_probs
        if not state_probs:
            break

    return min(1.0, max(0.0, conv_prob))


def _remove_channel(
    probs: dict[str, dict[str, float]],
    channel: str,
) -> dict[str, dict[str, float]]:
    """Remove a channel from the transition matrix, redistributing its probability.

    Args:
        probs: Original transition probability matrix.
        channel: Channel to remove.

    Returns:
        Modified transition matrix with the channel removed.
    """
    modified = {k: dict(v) for k, v in probs.items() if k != channel}
    for ch_from in modified:
        if channel in modified[ch_from]:
            redistributed = modified[ch_from].pop(channel)
            remaining = [k for k in modified[ch_from] if k != channel and k != ch_from]
            if remaining and redistributed > 0:
                share = redistributed / len(remaining)
                for r in remaining:
                    modified[ch_from][r] = modified[ch_from].get(r, 0) + share
            elif "null" in modified[ch_from]:
                modified[ch_from]["null"] = modified[ch_from].get("null", 0) + redistributed
    return modified


def visualize_conversion_path(
    touchpoints: list[dict[str, Any]],
    conversion_value: float,
    conversion_date: datetime,
) -> dict[str, Any]:
    """Build a visualization-ready conversion path structure.

    Args:
        touchpoints: Ordered list of credited touchpoints.
        conversion_value: Total conversion value.
        conversion_date: Conversion timestamp.

    Returns:
        Dict with steps, timing, and credit allocation.
    """
    steps = []
    sorted_tps = sorted(touchpoints, key=lambda t: t.get("timestamp", datetime.min))

    for i, tp in enumerate(sorted_tps):
        ts = tp.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        prev_ts = sorted_tps[i - 1].get("timestamp") if i > 0 else None
        if isinstance(prev_ts, str):
            prev_ts = datetime.fromisoformat(prev_ts.replace("Z", "+00:00"))

        time_since = None
        if prev_ts and ts:
            time_since = round((ts - prev_ts).total_seconds() / 3600, 2)

        steps.append({
            "step": i + 1,
            "channel": tp.get("channel", ""),
            "platform": tp.get("platform", ""),
            "campaign": tp.get("campaign", ""),
            "touchpoint_type": tp.get("touchpoint_type", ""),
            "timestamp": ts.isoformat() if ts else None,
            "time_since_previous_hours": time_since,
            "credit": round(tp.get("credit", 0), 4),
            "revenue_attributed": round(tp.get("revenue_attributed", 0), 2),
        })

    first_ts = sorted_tps[0].get("timestamp") if sorted_tps else None
    if isinstance(first_ts, str):
        first_ts = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))

    total_time = None
    if first_ts and conversion_date:
        total_time = round((conversion_date - first_ts).total_seconds() / 3600, 2)

    return {
        "steps": steps,
        "total_time_to_conversion_hours": total_time,
        "total_steps": len(steps),
        "conversion_value": float(conversion_value),
        "conversion_date": conversion_date.isoformat(),
    }


def get_attribution_summary(
    credited_touchpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize attribution results by channel and platform.

    Args:
        credited_touchpoints: Touchpoints with credit assigned.

    Returns:
        Dict with channel_credits, platform_credits, total_credit.
    """
    channel_totals: dict[str, float] = {}
    platform_totals: dict[str, float] = {}
    total_revenue = 0.0

    for tp in credited_touchpoints:
        ch = tp.get("channel", "unknown")
        pl = tp.get("platform", "unknown")
        credit = tp.get("credit", 0)
        rev = tp.get("revenue_attributed", 0)
        channel_totals[ch] = channel_totals.get(ch, 0) + credit
        platform_totals[pl] = platform_totals.get(pl, 0) + credit
        total_revenue += rev

    return {
        "channel_credits": dict(sorted(channel_totals.items(), key=lambda x: -x[1])),
        "platform_credits": dict(sorted(platform_totals.items(), key=lambda x: -x[1])),
        "total_credit": sum(channel_totals.values()),
        "total_revenue_attributed": round(total_revenue, 2),
    }
