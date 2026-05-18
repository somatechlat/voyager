"""OKR/KPI Tracking models — SP-005.

Hierarchical OKR system with objectives and key results supporting
numeric, percentage, and binary progress tracking with automated
data source linking.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class Objective(UUIDModel, TimeStampedModel, TenantModel):
    """An OKR objective at company, team, or individual level.

    Attributes:
        parent: Parent objective for hierarchical alignment.
        level: Scope level (company, team, individual).
        team_id: Optional team UUID.
        owner_id: UUID of the objective owner.
        title: Objective title.
        description: Detailed description.
        quarter: Quarter identifier (e.g. '2026-Q2').
        status: Current status (on_track, at_risk, behind, achieved, missed).
        progress: Overall progress percentage (0.0-1.0).
    """

    class Level(models.TextChoices):
        COMPANY = "company", "Company"
        TEAM = "team", "Team"
        INDIVIDUAL = "individual", "Individual"

    class Status(models.TextChoices):
        ON_TRACK = "on_track", "On Track"
        AT_RISK = "at_risk", "At Risk"
        BEHIND = "behind", "Behind"
        ACHIEVED = "achieved", "Achieved"
        MISSED = "missed", "Missed"

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent objective for hierarchical alignment",
    )
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        db_index=True,
        help_text="Scope level: company, team, or individual",
    )
    team_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Team UUID (for team-level objectives)",
    )
    owner_id = models.UUIDField(
        db_index=True,
        help_text="Objective owner user UUID",
    )
    title = models.CharField(
        max_length=500,
        help_text="Objective title",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description",
    )
    quarter = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Quarter identifier (e.g. '2026-Q2')",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ON_TRACK,
        db_index=True,
        help_text="Current status",
    )
    progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Overall progress (0.0 to 1.0)",
    )

    class Meta:
        db_table = "voyager_okr_objective"
        verbose_name = "OKR Objective"
        verbose_name_plural = "OKR Objectives"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "level"]),
            models.Index(fields=["tenant_id", "quarter"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "owner_id"]),
            models.Index(fields=["parent", "level"]),
            models.Index(fields=["tenant_id", "team_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.level})"

    def recalculate_progress(self) -> None:
        """Recalculate aggregate progress from child key results."""
        krs = self.key_results.all()
        if not krs:
            self.progress = 0
            return
        total = sum(kr.progress for kr in krs)
        self.progress = total / krs.count()
        # Update status based on progress
        if self.progress >= 1.0:
            self.status = self.Status.ACHIEVED
        elif self.progress >= 0.7:
            self.status = self.Status.ON_TRACK
        elif self.progress >= 0.4:
            self.status = self.Status.AT_RISK
        else:
            self.status = self.Status.BEHIND


class KeyResult(UUIDModel, TimeStampedModel):
    """A measurable Key Result tied to an Objective.

    Supports numeric (with increase/decrease direction), percentage,
    and binary completion tracking. Links to external data sources
    for automated progress updates.

    Attributes:
        objective: Parent objective.
        title: Key result title.
        kr_type: Measurement type (numeric, percentage, binary).
        target_value: Target value to achieve.
        current_value: Current measured value.
        start_value: Starting baseline value.
        direction: For numeric type: 'increase' or 'decrease'.
        unit: Unit of measurement (e.g. 'impressions', '%').
        data_source: JSON describing automated data source.
        progress: Computed progress (0.0-1.0).
        confidence: On-track assessment (on_track, at_risk).
    """

    class Type(models.TextChoices):
        NUMERIC = "numeric", "Numeric"
        PERCENTAGE = "percentage", "Percentage"
        BINARY = "binary", "Binary"

    class Direction(models.TextChoices):
        INCREASE = "increase", "Increase"
        DECREASE = "decrease", "Decrease"

    class Confidence(models.TextChoices):
        ON_TRACK = "on_track", "On Track"
        AT_RISK = "at_risk", "At Risk"

    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name="key_results",
        help_text="Parent objective",
    )
    title = models.CharField(
        max_length=500,
        help_text="Key result title",
    )
    kr_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        db_index=True,
        help_text="Measurement type",
    )
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Target value to achieve",
    )
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=0,
        help_text="Current measured value",
    )
    start_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=0,
        help_text="Starting baseline value",
    )
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        default=Direction.INCREASE,
        help_text="For numeric: whether to increase or decrease",
    )
    unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unit of measurement (e.g. 'impressions', '%')",
    )
    data_source = models.JSONField(
        default=dict,
        blank=True,
        help_text="Automated data source config: type, platform, metric, filters, refreshFrequency",
    )
    progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Computed progress (0.0 to 1.0)",
    )
    confidence = models.CharField(
        max_length=20,
        choices=Confidence.choices,
        default=Confidence.ON_TRACK,
        help_text="On-track assessment",
    )

    class Meta:
        db_table = "voyager_okr_key_result"
        verbose_name = "OKR Key Result"
        verbose_name_plural = "OKR Key Results"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["objective", "kr_type"]),
            models.Index(fields=["objective", "confidence"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.current_value}/{self.target_value} {self.unit}"

    def calculate_progress(self) -> dict[str, object]:
        """Calculate progress, confidence, and projection.

        Returns:
            Dict with progress, progressPercent, currentValue, targetValue,
            confidence, velocity, projectedCompletion.
        """
        current = float(self.current_value)
        target = float(self.target_value)
        start = float(self.start_value)

        if self.kr_type == self.Type.NUMERIC:
            if self.direction == self.Direction.INCREASE:
                if target - start != 0:
                    prog = (current - start) / (target - start)
                else:
                    prog = 1.0 if current >= target else 0.0
            else:
                if start - target != 0:
                    prog = (start - current) / (start - target)
                else:
                    prog = 1.0 if current <= target else 0.0
        elif self.kr_type == self.Type.PERCENTAGE:
            prog = current / target if target != 0 else 0.0
        elif self.kr_type == self.Type.BINARY:
            prog = 1.0 if current >= target else 0.0
        else:
            prog = 0.0

        prog = max(0.0, min(1.0, prog))
        self.progress = prog

        # Confidence based on velocity (simplified)
        velocity = current - start  # per-period change
        if self.direction == self.Direction.INCREASE:
            confidence = (
                self.Confidence.ON_TRACK
                if (current + velocity) >= target
                else self.Confidence.AT_RISK
            )
        else:
            confidence = (
                self.Confidence.ON_TRACK
                if (current + velocity) <= target
                else self.Confidence.AT_RISK
            )

        self.confidence = confidence
        self.save(update_fields=["progress", "confidence", "updated_at"])

        return {
            "progress": round(prog, 4),
            "progressPercent": round(prog * 100, 2),
            "currentValue": current,
            "targetValue": target,
            "confidence": confidence,
            "velocity": round(velocity, 4),
            "projectedCompletion": round(current + velocity, 4),
        }
