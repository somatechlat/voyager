"""Anomaly detection service — statistical methods for metric monitoring.

Implements z-score, IQR, seasonal decomposition (STL), median absolute
deviation (MAD), and exponentially weighted moving average (EWMA) methods
for detecting unusual patterns in time-series metrics.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any

from apps.analytics_v2.services.dashboards import _fetch_metric_series

logger = logging.getLogger(__name__)

# Anomaly type classification thresholds
SPIKE_THRESHOLD = 1.5
DROP_THRESHOLD = 0.5


def detect_anomalies(
    metric: str,
    dates: list[str],
    values: list[float],
    method: str = "zscore",
    threshold: float = 3.0,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """Detect anomalies in a time series using the specified statistical method.

    Args:
        metric: Metric name being analyzed.
        dates: List of date strings.
        values: List of metric values corresponding to dates.
        method: Detection method (zscore, iqr, seasonal_decomposition, mad, ewma).
        threshold: Sensitivity threshold.
        lookback_days: Days of historical data.

    Returns:
        Dict with anomalies list, total_data_points, anomaly_rate, method.
    """
    if not values or len(values) < 3:
        return {
            "metric": metric,
            "method": method,
            "total_data_points": len(values),
            "anomaly_rate": 0.0,
            "anomalies": [],
            "message": "Insufficient data points (minimum 3 required)",
        }

    if method == "zscore":
        anomalies = _detect_zscore(dates, values, threshold)
    elif method == "iqr":
        anomalies = _detect_iqr(dates, values, threshold)
    elif method == "seasonal_decomposition":
        period = max(2, min(7, len(values) // 4))
        anomalies = _detect_seasonal(dates, values, threshold, period)
    elif method == "mad":
        anomalies = _detect_mad(dates, values, threshold)
    elif method == "ewma":
        anomalies = _detect_ewma(dates, values, threshold)
    else:
        logger.warning("Unknown anomaly method: %s, falling back to zscore", method)
        anomalies = _detect_zscore(dates, values, threshold)

    total = len(values)
    rate = len(anomalies) / total if total > 0 else 0.0

    return {
        "metric": metric,
        "method": method,
        "threshold": threshold,
        "total_data_points": total,
        "anomaly_rate": round(rate, 4),
        "anomalies": anomalies,
    }


def _detect_zscore(
    dates: list[str],
    values: list[float],
    threshold: float,
) -> list[dict[str, Any]]:
    """Z-Score: Flag values more than N standard deviations from mean.

    Args:
        dates: Date strings.
        values: Metric values.
        threshold: Number of standard deviations (typically 3).

    Returns:
        List of anomaly dicts with date, value, z_score, severity.
    """
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0

    anomalies = []
    if std == 0:
        return anomalies

    for i, (d, v) in enumerate(zip(dates, values)):
        z_score = (v - mean) / std
        if abs(z_score) > threshold:
            severity = "critical" if abs(z_score) > threshold + 1 else "warning" if abs(z_score) > threshold else "info"
            anomaly_type = _classify_anomaly(values, i)
            anomalies.append({
                "date": d,
                "value": round(v, 4),
                "expected_value": round(mean, 4),
                "z_score": round(z_score, 4),
                "deviation": round(abs(v - mean), 4),
                "severity": severity,
                "anomaly_type": anomaly_type,
                "method": "zscore",
            })

    return anomalies


def _detect_iqr(
    dates: list[str],
    values: list[float],
    multiplier: float,
) -> list[dict[str, Any]]:
    """IQR: Flag values outside Q1 - k*IQR and Q3 + k*IQR.

    Args:
        dates: Date strings.
        values: Metric values.
        multiplier: IQR multiplier (typically 1.5).

    Returns:
        List of anomaly dicts.
    """
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    q1 = _percentile(sorted_vals, 25)
    q3 = _percentile(sorted_vals, 75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr

    anomalies = []
    for i, (d, v) in enumerate(zip(dates, values)):
        if v < lower or v > upper:
            deviation = abs(v - lower) if v < lower else abs(v - upper)
            severity = "critical" if deviation > iqr else "warning"
            anomalies.append({
                "date": d,
                "value": round(v, 4),
                "expected_value": round((q1 + q3) / 2, 4),
                "deviation": round(deviation, 4),
                "severity": severity,
                "anomaly_type": _classify_anomaly(values, i),
                "method": "iqr",
                "bounds": {"lower": round(lower, 4), "upper": round(upper, 4)},
            })

    return anomalies


def _detect_seasonal(
    dates: list[str],
    values: list[float],
    threshold: float,
    period: int = 7,
) -> list[dict[str, Any]]:
    """Seasonal Decomposition (STL): Detect anomalies in residuals.

    Performs simple seasonal decomposition by averaging values per season
    position and analyzing residuals.

    Args:
        dates: Date strings.
        values: Metric values.
        threshold: Z-score threshold for residuals.
        period: Seasonal period (default 7 for weekly).

    Returns:
        List of anomaly dicts.
    """
    n = len(values)
    if n < period * 2:
        # Fall back to z-score if not enough data
        return _detect_zscore(dates, values, threshold)

    # Simple seasonal decomposition: compute seasonal component per position
    seasonal = [0.0] * n
    for pos in range(period):
        pos_values = [values[i] for i in range(pos, n, period)]
        avg = sum(pos_values) / len(pos_values) if pos_values else 0
        for i in range(pos, n, period):
            seasonal[i] = avg

    # Global mean as trend
    trend = sum(values) / n

    # Compute residuals
    residuals = []
    for i in range(n):
        residual = values[i] - trend - (seasonal[i] - trend)
        residuals.append(residual)

    # Z-score on residuals
    mean_r = sum(residuals) / len(residuals)
    var_r = sum((r - mean_r) ** 2 for r in residuals) / len(residuals)
    std_r = math.sqrt(var_r) if var_r > 0 else 0

    anomalies = []
    if std_r == 0:
        return anomalies

    for i, (d, v) in enumerate(zip(dates, values)):
        z_r = (residuals[i] - mean_r) / std_r
        if abs(z_r) > threshold:
            severity = "critical" if abs(z_r) > threshold + 1 else "warning"
            anomalies.append({
                "date": d,
                "value": round(v, 4),
                "expected_value": round(trend + (seasonal[i] - trend), 4),
                "residual": round(residuals[i], 4),
                "z_score": round(z_r, 4),
                "deviation": round(abs(residuals[i]), 4),
                "severity": severity,
                "anomaly_type": _classify_anomaly(values, i),
                "method": "seasonal_decomposition",
                "period": period,
            })

    return anomalies


def _detect_mad(
    dates: list[str],
    values: list[float],
    threshold: float,
) -> list[dict[str, Any]]:
    """Median Absolute Deviation: Robust outlier detection.

    MAD = median(|xi - median(x)|). Values with modified Z-score > threshold flagged.

    Args:
        dates: Date strings.
        values: Metric values.
        threshold: Modified Z-score threshold.

    Returns:
        List of anomaly dicts.
    """
    median = _percentile(sorted(values), 50)
    abs_deviations = [abs(v - median) for v in values]
    mad = _percentile(sorted(abs_deviations), 50)

    anomalies = []
    if mad == 0:
        return anomalies

    for i, (d, v) in enumerate(zip(dates, values)):
        modified_z = 0.6745 * (v - median) / mad
        if abs(modified_z) > threshold:
            severity = "critical" if abs(modified_z) > threshold + 1 else "warning"
            anomalies.append({
                "date": d,
                "value": round(v, 4),
                "expected_value": round(median, 4),
                "modified_z_score": round(modified_z, 4),
                "deviation": round(abs(v - median), 4),
                "severity": severity,
                "anomaly_type": _classify_anomaly(values, i),
                "method": "mad",
            })

    return anomalies


def _detect_ewma(
    dates: list[str],
    values: list[float],
    threshold: float,
) -> list[dict[str, Any]]:
    """EWMA: Exponentially Weighted Moving Average anomaly detection.

    Flags values that deviate significantly from the EWMA prediction.

    Args:
        dates: Date strings.
        values: Metric values.
        threshold: Number of standard deviations.

    Returns:
        List of anomaly dicts.
    """
    alpha = 0.3  # Smoothing factor
    ewma = values[0]
    ewma_var = 0.0

    anomalies = []
    ewma_series = [ewma]

    for i in range(1, len(values)):
        residual = values[i - 1] - ewma
        ewma_var = alpha * (residual ** 2) + (1 - alpha) * ewma_var
        ewma = alpha * values[i - 1] + (1 - alpha) * ewma
        ewma_series.append(ewma)

        std = math.sqrt(ewma_var) if ewma_var > 0 else 0
        if std > 0:
            z = (values[i] - ewma) / std
            if abs(z) > threshold:
                severity = "critical" if abs(z) > threshold + 1 else "warning"
                anomalies.append({
                    "date": dates[i],
                    "value": round(values[i], 4),
                    "expected_value": round(ewma, 4),
                    "ewma": round(ewma, 4),
                    "z_score": round(z, 4),
                    "deviation": round(abs(values[i] - ewma), 4),
                    "severity": severity,
                    "anomaly_type": _classify_anomaly(values, i),
                    "method": "ewma",
                })

    return anomalies


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute percentile from sorted values.

    Args:
        sorted_values: Pre-sorted list of values.
        p: Percentile (0-100).

    Returns:
        Percentile value.
    """
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    idx = (p / 100.0) * (n - 1)
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return sorted_values[lower]
    frac = idx - lower
    return sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower])


def _classify_anomaly(values: list[float], index: int) -> str:
    """Classify an anomaly as spike, drop, trend_change, or seasonal_shift.

    Args:
        values: Full time series values.
        index: Index of the anomalous value.

    Returns:
        Anomaly type string.
    """
    if index < 1 or not values:
        return "seasonal_shift"

    current = values[index]

    # Check for spike/drop using 7-day window average
    window_start = max(0, index - 7)
    prev_values = values[window_start:index]
    if prev_values:
        prev_avg = sum(prev_values) / len(prev_values)
        if prev_avg > 0:
            if current > prev_avg * SPIKE_THRESHOLD:
                return "spike"
            if current < prev_avg * DROP_THRESHOLD:
                return "drop"

    # Check for trend change using 14-day slope
    trend_window = values[max(0, index - 14):index]
    if len(trend_window) >= 2:
        recent_trend = _linear_slope(trend_window)
        if recent_trend != 0:
            direction_change = (current - values[index - 1]) * recent_trend < 0
            if direction_change:
                return "trend_change"

    return "seasonal_shift"


def _linear_slope(values: list[float]) -> float:
    """Calculate the slope of a linear regression on values.

    Args:
        values: List of y-values with implicit x = 0, 1, ..., n-1.

    Returns:
        Slope coefficient.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum(i * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator != 0 else 0.0


def should_trigger_alert(
    alert: Any,
    anomaly_result: dict[str, Any],
) -> bool:
    """Check if an alert should trigger based on cooldown and severity.

    Args:
        alert: AnomalyAlert instance.
        anomaly_result: Output from detect_anomalies.

    Returns:
        True if the alert should fire.
    """
    if not alert.enabled:
        return False

    anomalies = anomaly_result.get("anomalies", [])
    if not anomalies:
        return False

    # Check cooldown
    if alert.last_triggered_at:
        cooldown = timedelta(minutes=alert.cooldown_minutes)
        if datetime.utcnow() - alert.last_triggered_at.replace(tzinfo=None) < cooldown:
            return False

    # Filter by severity threshold
    has_critical = any(a.get("severity") == "critical" for a in anomalies)
    has_warning = any(a.get("severity") == "warning" for a in anomalies)

    return has_critical or has_warning
