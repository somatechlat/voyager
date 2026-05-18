"""WorkflowTrigger model — 15+ trigger types for workflow activation."""

from __future__ import annotations

from django.db import models


class WorkflowTrigger(models.Model):
    """A trigger configuration that activates a workflow.

    Supports 15+ trigger types including cron schedules, platform
    events, webhooks, metric thresholds, manual triggers, and more.

    Attributes:
        id: Auto-incrementing primary key.
        workflow: The workflow to trigger.
        trigger_type: The type of trigger.
        name: Human-readable trigger name.
        config: Trigger-specific configuration JSON.
        is_active: Whether this trigger is enabled.
        last_triggered_at: When this trigger last fired.
        trigger_count: Total number of times triggered.
        created_by: User who created the trigger.
        created_at: Timestamp.
        updated_at: Timestamp.
    """

    TYPE_CRON = "cron"
    TYPE_WEBHOOK = "webhook"
    TYPE_PLATFORM_EVENT = "platform_event"
    TYPE_METRIC_THRESHOLD = "metric_threshold"
    TYPE_FILE_UPLOAD = "file_upload"
    TYPE_EMAIL_RECEIVED = "email_received"
    TYPE_MANUAL = "manual"
    TYPE_STATE_CHANGE = "state_change"
    TYPE_SCHEDULED = "scheduled"
    TYPE_API_CALL = "api_call"
    TYPE_FORM_SUBMIT = "form_submit"
    TYPE_WEBSOCKET = "websocket"
    TYPE_QUEUE_MESSAGE = "queue_message"
    TYPE_DATETIME = "datetime"
    TYPE_RECURRING = "recurring"

    TRIGGER_TYPE_CHOICES = [
        (TYPE_CRON, "Cron Schedule"),
        (TYPE_WEBHOOK, "Webhook"),
        (TYPE_PLATFORM_EVENT, "Platform Event"),
        (TYPE_METRIC_THRESHOLD, "Metric Threshold"),
        (TYPE_FILE_UPLOAD, "File Upload"),
        (TYPE_EMAIL_RECEIVED, "Email Received"),
        (TYPE_MANUAL, "Manual"),
        (TYPE_STATE_CHANGE, "State Change"),
        (TYPE_SCHEDULED, "Scheduled"),
        (TYPE_API_CALL, "API Call"),
        (TYPE_FORM_SUBMIT, "Form Submission"),
        (TYPE_WEBSOCKET, "WebSocket"),
        (TYPE_QUEUE_MESSAGE, "Queue Message"),
        (TYPE_DATETIME, "Date/Time"),
        (TYPE_RECURRING, "Recurring"),
    ]

    id = models.BigAutoField(primary_key=True, editable=False)
    workflow = models.ForeignKey(
        "Workflow",
        on_delete=models.CASCADE,
        related_name="triggers",
        help_text="The workflow to trigger",
    )
    trigger_type = models.CharField(
        max_length=30,
        choices=TRIGGER_TYPE_CHOICES,
        db_index=True,
        help_text="The type of trigger",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable trigger name",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Trigger-specific configuration",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this trigger is enabled",
    )
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this trigger last fired",
    )
    trigger_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of times triggered",
    )
    created_by = models.CharField(
        max_length=256,
        help_text="User who created the trigger",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_workflow_trigger"
        verbose_name = "Workflow Trigger"
        verbose_name_plural = "Workflow Triggers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workflow", "trigger_type"]),
            models.Index(fields=["workflow", "is_active"]),
            models.Index(fields=["trigger_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_trigger_type_display()})"

    def record_trigger(self) -> None:
        """Update trigger statistics after firing."""
        from django.utils import timezone

        self.last_triggered_at = timezone.now()
        self.trigger_count += 1
        self.save(update_fields=["last_triggered_at", "trigger_count"])
