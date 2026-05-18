"""Report models for custom report building and scheduling.

ReportTemplate defines a report configuration (metrics, dimensions,
filters, visualizations). ReportSchedule handles automated execution
and delivery.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.rbac.models import TenantScopedMixin


REPORT_FORMAT_CHOICES = [
    ("pdf", "PDF"),
    ("csv", "CSV"),
    ("excel", "Excel"),
    ("json", "JSON"),
]

SCHEDULE_FREQUENCY_CHOICES = [
    ("once", "Once"),
    ("hourly", "Hourly"),
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
]

DELIVERY_METHOD_CHOICES = [
    ("email", "Email"),
    ("slack", "Slack"),
    ("webhook", "Webhook"),
    ("s3", "S3"),
    ("download", "Download Only"),
]

REPORT_STATUS_CHOICES = [
    ("draft", "Draft"),
    ("ready", "Ready"),
    ("scheduled", "Scheduled"),
    ("generating", "Generating"),
    ("completed", "Completed"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
]


class ReportTemplate(TenantScopedMixin, models.Model):
    """A reusable report template defining metrics, dimensions, and filters.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Human-readable report name.
        description: Optional longer description.
        category: Report category (engagement, reach, conversion, etc.).
        config: Full report configuration (metrics, dimensions, filters, visualizations).
        format: Default output format.
        is_favorite: Whether the report is marked as favorite.
        created_by: User ID of the creator.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=64,
        default="general",
        db_index=True,
        help_text="Report category: engagement, reach, conversion, seo, email, etc.",
    )
    config = models.JSONField(
        default=dict,
        help_text="Metrics, dimensions, filters, visualizations, sorting",
    )
    format = models.CharField(
        max_length=16,
        choices=REPORT_FORMAT_CHOICES,
        default="pdf",
    )
    is_favorite = models.BooleanField(default=False)
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "analytics_report_template"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "category"]),
            models.Index(fields=["tenant_id", "-created_at"]),
            models.Index(fields=["tenant_id", "is_favorite"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_rpt_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ReportSchedule(TenantScopedMixin, models.Model):
    """Scheduled execution of a report template with delivery configuration.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        template: The report template to execute.
        name: Schedule name.
        frequency: How often the report runs.
        cron_expression: Optional cron expression for advanced scheduling.
        next_run_at: Next scheduled execution time.
        last_run_at: Last execution time.
        last_run_status: Status of the last execution.
        last_run_result: JSON result from the last execution.
        delivery: JSON delivery configuration (email, slack, webhook).
        timezone: Timezone for scheduling.
        is_active: Whether the schedule is currently active.
        created_by: User ID of the creator.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    name = models.CharField(max_length=255)
    frequency = models.CharField(
        max_length=16,
        choices=SCHEDULE_FREQUENCY_CHOICES,
        default="weekly",
    )
    cron_expression = models.CharField(
        max_length=128,
        blank=True,
        help_text="Optional cron for advanced scheduling",
    )
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(
        max_length=16,
        choices=REPORT_STATUS_CHOICES,
        default="draft",
    )
    last_run_result = models.JSONField(default=dict, blank=True)
    delivery = models.JSONField(
        default=dict,
        help_text="Delivery channels: email, slack, webhook, s3",
    )
    timezone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "analytics_report_schedule"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "is_active", "next_run_at"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.frequency})"
