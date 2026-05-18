# Generated initial migration for integrations

import uuid

from django.db import migrations, models


class Direction(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"
    BIDIRECTIONAL = "bidirectional", "Bidirectional"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"
    DEAD_LETTER = "dead_letter", "Dead Letter"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("integrations", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="WebhookDelivery",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "webhook",
                    models.ForeignKey(
                        WebhookEndpoint,
                        on_delete=models.CASCADE,
                        related_name="deliveries",
                    ),
                ),
                ("event_type", models.CharField(max_length=128, blank=True)),
                ("payload_json", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                    ),
                ),
                ("response_status", models.IntegerField(null=True, blank=True)),
                ("response_body", models.TextField(blank=True)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("next_retry_at", models.DateTimeField(null=True, blank=True, db_index=True)),
                ("delivered_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_webhook_delivery",
                "verbose_name": "Webhook Delivery",
                "verbose_name_plural": "Webhook Deliveries",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["webhook", "status", "created_at"]),
                    models.Index(fields=["status", "next_retry_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="SyncLog",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "connection",
                    models.ForeignKey(
                        PlatformConnection,
                        on_delete=models.CASCADE,
                        related_name="sync_logs",
                    ),
                ),
                ("sync_type", models.CharField(max_length=128, db_index=True)),
                ("direction", models.CharField(max_length=16, choices=Direction.choices)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                    ),
                ),
                ("records_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("deleted_count", models.PositiveIntegerField(default=0)),
                ("conflict_count", models.PositiveIntegerField(default=0)),
                ("errors_json", models.JSONField(default=list, blank=True)),
                ("field_mappings_json", models.JSONField(default=dict, blank=True)),
                ("conflict_resolution", models.CharField(max_length=16, default="source_wins")),
                ("started_at", models.DateTimeField(null=True, blank=True)),
                ("completed_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_sync_log",
                "verbose_name": "Sync Log",
                "verbose_name_plural": "Sync Logs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["connection", "sync_type", "status"]),
                    models.Index(fields=["tenant_id"]),
                    models.Index(fields=["status", "started_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="PlatformHealth",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "connection",
                    models.ForeignKey(
                        PlatformConnection,
                        on_delete=models.CASCADE,
                        related_name="health_checks",
                    ),
                ),
                ("last_check_at", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.UNKNOWN,
                        db_index=True,
                    ),
                ),
                ("latency_ms", models.PositiveIntegerField(null=True, blank=True)),
                ("error_message", models.TextField(blank=True)),
                ("details_json", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "voyager_platform_health",
                "verbose_name": "Platform Health",
                "verbose_name_plural": "Platform Health Checks",
                "ordering": ["-last_check_at"],
                "indexes": [
                    models.Index(fields=["connection", "-last_check_at"]),
                    models.Index(fields=["status", "-last_check_at"]),
                ],
            },
        ),
    ]
