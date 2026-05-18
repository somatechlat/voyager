"""Trend detection with velocity, acceleration, and lifecycle scoring.

Identifies emerging trends across social media, news, and search data
using weighted scoring and lifecycle classification.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone

from ..models import TrendDetection

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes mention data to detect and score trends.

    Uses volume, velocity (rate of change), and acceleration
    (rate of change of rate of change) to classify trends.
    """

    # Weighting factors for composite score
    VOLUME_WEIGHT = 0.3
    VELOCITY_WEIGHT = 0.4
    ACCELERATION_WEIGHT = 0.3

    def __init__(self, baseline_multiplier: float = 2.0) -> None:
        """Initialize the trend analyzer.

        Args:
            baseline_multiplier: Multiplier above baseline to consider trending.
        """
        self.baseline_multiplier = baseline_multiplier

    def calculate_trend_score(
        self,
        data_points: list[dict[str, Any]],
        industry_baseline: int = 0,
    ) -> dict[str, Any]:
        """Calculate trend score from daily mention data.

        Args:
            data_points: List of dicts with ``date`` and ``mentions`` keys.
            industry_baseline: Baseline mention count for normalization.

        Returns:
            Dict with score, stage, volume, velocity, acceleration,
            peak_date, and estimated_lifespan.
        """
        if not data_points:
            return {
                "score": Decimal("0"),
                "stage": TrendDetection.Stage.EMERGING,
                "volume": 0,
                "velocity": Decimal("0"),
                "acceleration": Decimal("0"),
                "peak_date": None,
                "estimated_lifespan_days": None,
            }

        # Sort by date
        sorted_data = sorted(data_points, key=lambda x: x.get("date", ""))
        mentions = [d.get("mentions", 0) for d in sorted_data]

        # Total volume
        volume = sum(mentions)

        # Velocity: average daily change
        velocity = self._calculate_velocity(mentions)

        # Acceleration: change in velocity
        acceleration = self._calculate_acceleration(mentions)

        # Normalize each metric to 0-100 range
        normalized_volume = self._minmax_normalize(volume, max(industry_baseline, 1))
        normalized_velocity = self._minmax_normalize(
            abs(velocity), max(industry_baseline * 0.1, 1)
        )
        normalized_acceleration = self._minmax_normalize(
            abs(acceleration), max(industry_baseline * 0.05, 1)
        )

        # Weighted composite score
        score = (
            normalized_volume * Decimal(str(self.VOLUME_WEIGHT))
            + normalized_velocity * Decimal(str(self.VELOCITY_WEIGHT))
            + normalized_acceleration * Decimal(str(self.ACCELERATION_WEIGHT))
        )
        score = max(Decimal("0"), min(Decimal("100"), score))

        # Lifecycle stage
        stage = self._classify_stage(velocity, acceleration)

        # Peak date
        peak_date = self._find_peak(sorted_data)

        # Estimated lifespan
        lifespan = self._estimate_lifespan(sorted_data, stage)

        return {
            "score": round(score, 2),
            "stage": stage,
            "volume": volume,
            "velocity": round(velocity, 4),
            "acceleration": round(acceleration, 4),
            "peak_date": peak_date,
            "estimated_lifespan_days": lifespan,
        }

    def _calculate_velocity(self, mentions: list[int]) -> Decimal:
        """Calculate average daily change in mentions.

        Args:
            mentions: Daily mention counts.

        Returns:
            Average daily change as a Decimal.
        """
        if len(mentions) < 2:
            return Decimal("0")

        changes = [mentions[i] - mentions[i - 1] for i in range(1, len(mentions))]
        avg_change = statistics.mean(changes)
        return Decimal(str(avg_change))

    def _calculate_acceleration(self, mentions: list[int]) -> Decimal:
        """Calculate change in velocity (second derivative).

        Args:
            mentions: Daily mention counts.

        Returns:
            Acceleration as a Decimal.
        """
        if len(mentions) < 3:
            return Decimal("0")

        velocities = [mentions[i] - mentions[i - 1] for i in range(1, len(mentions))]
        accelerations = [velocities[i] - velocities[i - 1] for i in range(1, len(velocities))]
        avg_accel = statistics.mean(accelerations) if accelerations else 0
        return Decimal(str(avg_accel))

    def _minmax_normalize(self, value: Decimal, baseline: float) -> Decimal:
        """Normalize a value to 0-100 using min-max scaling.

        Args:
            value: The value to normalize.
            baseline: Reference baseline for scaling.

        Returns:
            Normalized value between 0 and 100.
        """
        if baseline <= 0:
            baseline = 1.0
        normalized = (abs(value) / Decimal(str(baseline))) * Decimal("100")
        return min(Decimal("100"), normalized)

    def _classify_stage(self, velocity: Decimal, acceleration: Decimal) -> str:
        """Classify trend lifecycle stage.

        Args:
            velocity: Rate of change in mentions.
            acceleration: Rate of change of velocity.

        Returns:
            Stage string from TrendDetection.Stage choices.
        """
        vel_pos = velocity > Decimal("0")
        accel_pos = acceleration > Decimal("0")

        if accel_pos and vel_pos:
            return TrendDetection.Stage.EMERGING
        elif not accel_pos and vel_pos:
            return TrendDetection.Stage.PEAKING
        elif not vel_pos and not accel_pos:
            return TrendDetection.Stage.DECLINING
        else:
            return TrendDetection.Stage.RECOVERING

    def _find_peak(self, data_points: list[dict[str, Any]]) -> datetime | None:
        """Find the peak date from data points.

        Args:
            data_points: Sorted list of dicts with date and mentions.

        Returns:
            Datetime of peak, or None.
        """
        if not data_points:
            return None

        peak_point = max(data_points, key=lambda x: x.get("mentions", 0))
        date_str = peak_point.get("date")
        if date_str:
            try:
                return timezone.make_aware(
                    datetime.strptime(date_str, "%Y-%m-%d")
                )
            except (ValueError, TypeError):
                pass
        return None

    def _estimate_lifespan(
        self,
        data_points: list[dict[str, Any]],
        stage: str,
    ) -> int | None:
        """Estimate remaining trend lifespan in days.

        Args:
            data_points: Historical data points.
            stage: Current lifecycle stage.

        Returns:
            Estimated remaining days, or None.
        """
        if not data_points:
            return None

        # Stage-based estimates
        estimates: dict[str, int] = {
            TrendDetection.Stage.EMERGING: 30,
            TrendDetection.Stage.PEAKING: 14,
            TrendDetection.Stage.DECLINING: 7,
            TrendDetection.Stage.RECOVERING: 21,
        }

        base_estimate = estimates.get(stage, 14)

        # Adjust based on data length
        data_span = len(data_points)
        if data_span > 30:
            base_estimate = int(base_estimate * 0.7)
        elif data_span < 7:
            base_estimate = int(base_estimate * 1.5)

        return max(1, base_estimate)

    def detect_trends_for_tenant(
        self,
        tenant_id: str,
        topic: str,
        source: str,
        data_points: list[dict[str, Any]],
        industry_baseline: int = 0,
    ) -> TrendDetection:
        """Create a TrendDetection record from analyzed data.

        Args:
            tenant_id: Tenant scope identifier.
            topic: The trending topic.
            source: Data source name.
            data_points: Daily mention counts.
            industry_baseline: Baseline for normalization.

        Returns:
            Created TrendDetection instance.
        """
        result = self.calculate_trend_score(data_points, industry_baseline)

        trend = TrendDetection.objects.create(
            tenant_id=tenant_id,
            topic=topic,
            source=source,
            mention_count=result["volume"],
            trend_score=result["score"],
            velocity=Decimal(str(result["velocity"])),
            acceleration=Decimal(str(result["acceleration"])),
            stage=result["stage"],
            peak_date=result["peak_date"],
            estimated_lifespan_days=result["estimated_lifespan_days"],
            industry_baseline=industry_baseline,
            data_points=data_points,
        )

        return trend
