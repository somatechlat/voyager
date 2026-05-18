# Generated initial migration for publishing


from django.db import migrations, models


class Action(models.TextChoices):
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    REQUEST_CHANGES = "request_changes", "Request Changes"


class ErrorType(models.TextChoices):
    RATE_LIMIT = "rate_limit", "Rate Limit"
    SERVER_ERROR = "server_error", "Server Error"
    TIMEOUT = "timeout", "Timeout"
    AUTH_EXPIRED = "auth_expired", "Auth Expired"
    NETWORK = "network", "Network Error"
    INVALID_CREDENTIALS = "invalid_credentials", "Invalid Credentials"
    CONTENT_REJECTED = "content_rejected", "Content Rejected"
    ACCOUNT_SUSPENDED = "account_suspended", "Account Suspended"
    QUOTA_EXCEEDED = "quota_exceeded", "Quota Exceeded"
    UNKNOWN = "unknown", "Unknown"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("publishing", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="ApprovalInstance",
            fields=[
                (
                    "workflow",
                    models.ForeignKey(
                        ApprovalWorkflow,
                        on_delete=models.CASCADE,
                        related_name="instances",
                        db_index=True,
                    ),
                ),
                (
                    "scheduled_post",
                    models.OneToOneField(
                        to="ScheduledPost",
                        on_delete=models.CASCADE,
                        related_name="approval_instance",
                        db_index=True,
                    ),
                ),
                (
                    "current_step",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Current step number (1-indexed)",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                    ),
                ),
                (
                    "step_started_at",
                    models.DateTimeField(
                        default=timezone.now,
                        help_text="When current step started",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When instance was completed",
                    ),
                ),
                (
                    "escalated_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When escalation happened",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_approval_instance",
                "verbose_name": "Approval Instance",
                "verbose_name_plural": "Approval Instances",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["workflow", "status"]),
                    models.Index(fields=["scheduled_post", "status"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ApprovalAction",
            fields=[
                (
                    "instance",
                    models.ForeignKey(
                        ApprovalInstance,
                        on_delete=models.CASCADE,
                        related_name="actions",
                        db_index=True,
                    ),
                ),
                ("step", models.PositiveIntegerField(help_text="Step number")),
                (
                    "approver_id",
                    models.CharField(max_length=256, db_index=True, help_text="User UUID"),
                ),
                ("action", models.CharField(max_length=32, choices=Action.choices, db_index=True)),
                ("comment", models.TextField(blank=True)),
            ],
            options={
                "db_table": "voyager_approval_action",
                "verbose_name": "Approval Action",
                "verbose_name_plural": "Approval Actions",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["instance", "step"]),
                    models.Index(fields=["approver_id", "action"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="PublishRetry",
            fields=[
                (
                    "scheduled_post",
                    models.ForeignKey(
                        to="ScheduledPost",
                        on_delete=models.CASCADE,
                        related_name="retries",
                        db_index=True,
                    ),
                ),
                (
                    "attempt_number",
                    models.PositiveIntegerField(
                        default=1,
                        db_index=True,
                        help_text="Retry attempt number",
                    ),
                ),
                (
                    "error_type",
                    models.CharField(
                        max_length=32,
                        choices=ErrorType.choices,
                        db_index=True,
                        help_text="Classified error type",
                    ),
                ),
                ("error_message", models.TextField(help_text="Full error message")),
                (
                    "platform_response_status",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="HTTP status from platform",
                    ),
                ),
                (
                    "platform_response_body",
                    models.TextField(
                        blank=True,
                        help_text="Response body from platform",
                    ),
                ),
                (
                    "delay_seconds",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Calculated delay before retry",
                    ),
                ),
                (
                    "retried_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When retry was executed",
                    ),
                ),
                (
                    "successful",
                    models.BooleanField(
                        default=False,
                        db_index=True,
                        help_text="Whether retry succeeded",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_publish_retry",
                "verbose_name": "Publish Retry",
                "verbose_name_plural": "Publish Retries",
                "ordering": ["scheduled_post", "attempt_number"],
                "indexes": [
                    models.Index(fields=["scheduled_post", "attempt_number"]),
                    models.Index(fields=["error_type", "created_at"]),
                    models.Index(fields=["successful", "created_at"]),
                ],
            },
        ),
    ]
