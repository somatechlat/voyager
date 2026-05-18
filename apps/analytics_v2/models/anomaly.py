"""Anomaly detection models for automated metric monitoring.

Defines AnomalyAlert (configuration for anomaly detection rules) and
AnomalyEvent (recorded anomaly occurrences with statistical details).
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.rbac.models import TenantScopedMixin

ANOMALY_METHOD_CHOICES = [
    ("zscore", "Z-Score"),
    ("iqr", "Interquartile Range (IQR)"),
    ("seasonal_decomposition", "Seasonal Decomposition (STL)"),
    ("mad", "Median Absolute Deviation"),
    ("ewma", "Exponentially Weighted Moving Average"),
]

ANOMALY_TYPE_CHOICES = [
    ("spike", "Spike"),
    ("drop", "Drop"),
    ("trend_change", "Trend Change"),
    ("seasonal_shift", "Seasonal Shift"),
    ("level_shift", "Level Shift"),
    ("volatility_change", "Volatility Change"),
]

SEVERITY_CHOICES = [
    ("info", "Info"),
    ("warning", "Warning"),
    ("critical", "Critical"),
]

ALERT_CHANNEL_CHOICES = [
    ("email", "Email"),
    ("slack", "Slack"),
    ("in_app", "In-App Notification"),
    ("webhook", "Webhook"),
    ("pagerduty", "PagerDuty"),
]


class AnomalyAlert(TenantScopedMixin, models.Model):
    """Configuration for automated anomaly detection on a specific metric.

    An alert rule defines which metric to monitor, which statistical
    method to apply, the sensitivity threshold, and how to notify when
    an anomaly is detected.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Human-readable alert name.
        metric: Metric identifier to monitor (e.g. 'engagement_rate').
        platform: Optional platform filter.
        method: Statistical detection method.
        threshold: Sensitivity threshold (e.g. 3.0 for z-score).
        lookback_days: Days of historical data to analyze.
        comparison_mode: How to compare values (period_over_period, etc.).
        channels: JSON notification channel configuration.
        cooldown_minutes: Minimum minutes between repeat alerts.
        enabled: Whether the alert is active.
        last_triggered_at: When the alert last fired.
        trigger_count: Total number of times this alert has fired.
        created_by: User ID of the creator.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    metric = models.CharField(max_length=100, db_index=True)
    platform = models.CharField(max_length=64, blank=True, db_index=True)
    method = models.CharField(
        max_length=32,
        choices=ANOMALY_METHOD_CHOICES,
        default="zscore",
    )
    threshold = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=3.0,
        help_text="Sensitivity threshold (e.g. 3.0 for z-score, 1.5 for IQR)",
    )
    lookback_days = models.PositiveIntegerField(default=30)
    comparison_mode = models.CharField(
        max_length=32,
        default="absolute",
        help_text="Comparison: absolute, period_over_period, year_over_year",
    )
    channels = models.JSONField(
        default=list,
        help_text="Notification channels: [{type, recipients, channel, url}]",
    )
    cooldown_minutes = models.PositiveIntegerField(default=60)
    enabled = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    trigger_count = models.PositiveIntegerField(default=0)
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "analytics_anomaly_alert"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "metric"]),
            models.Index(fields=["tenant_id", "enabled"]),
            models.Index(fields=["tenant_id", "method"]),
            models.Index(fields=["tenant_id", "-last_triggered_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.metric} / {self.method})"


class AnomalyEvent(TenantScopedMixin, models.Model):
    """A recorded anomaly occurrence detected by an alert rule.

    Attributes:
        id: UUID primary key.
        alert: Parent alert configuration.
        tenant_id: Tenant scope identifier.
        metric: Metric that triggered the anomaly.
        anomaly_type: Classification of the anomaly.
        severity: Calculated severity level.
        expected_value: Expected (baseline) metric value.
        actual_value: Actual observed metric value.
        deviation: Absolute difference from expected.
        z_score: Statistical z-score of the anomaly.
        method: Method used to detect the anomaly.
        context: JSON additional context (platform, channel, campaign).
        detected_at: When the anomaly was detected.
        acknowledged_at: When the anomaly was acknowledged.
        acknowledged_by: User who acknowledged.
        resolved_at: When the anomaly was marked resolved.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert = models.ForeignKey(
        AnomalyAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    tenant_id = models.CharField(max_length=64, db_index=True)
    metric = models.CharField(max_length=100, db_index=True)
    anomaly_type = models.CharField(
        max_length=32,
        choices=ANOMALY_TYPE_CHOICES,
        blank=True,
    )
    severity = models.CharField(
        max_length=16,
        choices=SEVERITY_CHOICES,
        default="warning",
    )
    expected_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    actual_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    deviation = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    z_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    method = models.CharField(max_length=32, blank=True)
    context = models.JSONField(default=dict, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=128, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "analytics_anomaly_event"
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["tenant_id", "metric", "-detected_at"]),
            models.Index(fields=["tenant_id", "severity", "-detected_at"]),
            models.Index(fields=["tenant_id", "anomaly_type"]),
            models.Index(fields=["alert", "-detected_at"]),
        ]

    def __str__(self) -> str:
        return f"Anomaly: {self.metric} = {self.actual_value} ({self.severity})"
