"""TimeEntry model for multi-mode time tracking.

Supports timer, manual, automatic, and calendar entry modes with
rounding rules and billing calculations.
"""

from __future__ import annotations

from django.db import models

from .base import TimestampedModel


class TimeEntry(TimestampedModel):
    """A single time-tracking entry."""

    class TrackingMode(models.TextChoices):
        TIMER = "timer", "Timer"
        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automatic"
        CALENDAR = "calendar", "Calendar"

    class RoundingMode(models.TextChoices):
        NEAREST = "nearest", "Nearest"
        UP = "up", "Up"
        DOWN = "down", "Down"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        INVOICED = "invoiced", "Invoiced"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    user_id = models.CharField(max_length=128, db_index=True, help_text="User who logged time")
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="time_entries",
        help_text="The client this time is for",
    )
    project = models.ForeignKey(
        "clients.Project",
        on_delete=models.CASCADE,
        related_name="time_entries",
        blank=True,
        null=True,
        help_text="The project this time is for",
    )
    task_name = models.CharField(max_length=500, blank=True, help_text="Name of the task worked on")
    description = models.TextField(blank=True, help_text="Detailed description of work")
    tracking_mode = models.CharField(
        max_length=20,
        choices=TrackingMode.choices,
        default=TrackingMode.MANUAL,
        db_index=True,
        help_text="How the time was tracked",
    )
    started_at = models.DateTimeField(db_index=True, help_text="When the work session started")
    ended_at = models.DateTimeField(blank=True, null=True, help_text="When the work session ended")
    duration_minutes = models.PositiveIntegerField(help_text="Actual duration in minutes")
    rounded_minutes = models.PositiveIntegerField(help_text="Duration after rounding rules applied")
    rounding_mode = models.CharField(
        max_length=20,
        choices=RoundingMode.choices,
        default=RoundingMode.NEAREST,
        help_text="Rounding mode applied",
    )
    rounding_increment = models.PositiveIntegerField(
        default=15, help_text="Rounding increment in minutes"
    )
    billing_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Hourly billing rate for this entry",
    )
    billable_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Calculated billable amount",
    )
    is_billable = models.BooleanField(default=True, help_text="Whether this entry is billable")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Approval status",
    )
    timesheet_week = models.DateField(
        blank=True, null=True, db_index=True, help_text="Week this entry belongs to"
    )
    approver_id = models.CharField(
        max_length=128, blank=True, default="", help_text="User who approved/rejected"
    )
    approved_at = models.DateTimeField(
        blank=True, null=True, help_text="When the entry was approved"
    )
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection")
    source_data = models.JSONField(
        blank=True,
        default=dict,
        help_text="Source data for automatic entries (git commits, etc.)",
    )
    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.SET_NULL,
        related_name="time_entries",
        blank=True,
        null=True,
        help_text="Invoice this entry was billed on",
    )

    class Meta:
        db_table = "voyager_time_entry"
        verbose_name = "Time Entry"
        verbose_name_plural = "Time Entries"
        ordering = ["-started_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "user_id", "-started_at"],
                name="voy_te_tenant_user_started_idx",
            ),
            models.Index(
                fields=["tenant_id", "client", "-started_at"],
                name="voy_te_tenant_client_started_idx",
            ),
            models.Index(
                fields=["tenant_id", "project", "status"],
                name="voy_te_tenant_project_status_idx",
            ),
            models.Index(
                fields=["tenant_id", "timesheet_week", "status"],
                name="voy_te_tenant_week_status_idx",
            ),
            models.Index(
                fields=["tenant_id", "is_billable", "status"],
                name="voy_te_tenant_billable_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.task_name} ({self.duration_minutes}m)"
