"""Initial migration for the Audit app.

Creates AuditLogEntry and AuditLogArchive models with SHA-256 hash chain
support, composite indexes, and unique constraints for compliance-ready
audit trail management.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration that bootstraps the Audit schema."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        # ── AuditLogEntry ─────────────────────────────────────────────────
        migrations.CreateModel(
            name="AuditLogEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="When the audited event occurred",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "actor_id",
                    models.CharField(
                        max_length=256,
                        db_index=True,
                        help_text="Keycloak subject identifier of the actor",
                    ),
                ),
                (
                    "actor_type",
                    models.CharField(
                        max_length=32,
                        choices=[
                            ("user", "User"),
                            ("service", "Service"),
                            ("agent", "AI Agent"),
                        ],
                        help_text="Kind of actor: user, service, or AI agent",
                    ),
                ),
                (
                    "actor_email",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        help_text="Optional email address of the actor",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="The action performed (e.g. 'content.created')",
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        max_length=64,
                        db_index=True,
                        help_text="Category of the affected resource (e.g. 'content_generation')",
                    ),
                ),
                (
                    "resource_id",
                    models.CharField(
                        max_length=256,
                        help_text="Identifier of the affected resource",
                    ),
                ),
                (
                    "outcome",
                    models.CharField(
                        max_length=32,
                        choices=[
                            ("success", "Success"),
                            ("failure", "Failure"),
                            ("denied", "Access Denied"),
                        ],
                        help_text="Result of the action: success, failure, or denied",
                    ),
                ),
                (
                    "details",
                    models.JSONField(
                        default=dict,
                        help_text="JSON payload with before/after values and extra context",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        null=True,
                        help_text="Optional IP address of the actor",
                    ),
                ),
                (
                    "user_agent",
                    models.TextField(
                        blank=True,
                        help_text="Optional HTTP user agent string",
                    ),
                ),
                (
                    "request_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Optional correlation ID for distributed tracing",
                    ),
                ),
                (
                    "session_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Optional session identifier",
                    ),
                ),
                (
                    "previous_hash",
                    models.CharField(
                        max_length=64,
                        blank=True,
                        help_text="SHA-256 hash of the preceding tenant log entry",
                    ),
                ),
                (
                    "entry_hash",
                    models.CharField(
                        max_length=64,
                        db_index=True,
                        help_text="SHA-256 hash of this entry (chain link)",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_audit_log",
                "verbose_name": "Audit Log Entry",
                "verbose_name_plural": "Audit Log Entries",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["tenant_id", "timestamp"],
                name="voyager_audit_tenant_ts_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["tenant_id", "actor_id", "timestamp"],
                name="voyager_audit_tenant_actor_ts_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["tenant_id", "action", "timestamp"],
                name="voyager_audit_tenant_action_ts_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["tenant_id", "resource_type", "resource_id"],
                name="voyager_audit_tenant_res_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["request_id"],
                name="voyager_audit_request_id_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["session_id"],
                name="voyager_audit_session_id_idx",
            ),
        ),
        # ── AuditLogArchive ───────────────────────────────────────────────
        migrations.CreateModel(
            name="AuditLogArchive",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "year_month",
                    models.CharField(
                        max_length=7,
                        db_index=True,
                        help_text="The archive month in YYYY-MM format",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "log_count",
                    models.IntegerField(
                        help_text="Number of log entries contained in the archive",
                    ),
                ),
                (
                    "archive_data",
                    models.BinaryField(
                        help_text="Compressed binary JSON containing the log entries",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the archive was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_audit_log_archive",
                "verbose_name": "Audit Log Archive",
                "verbose_name_plural": "Audit Log Archives",
                "ordering": ["-year_month", "tenant_id"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlogarchive",
            index=models.Index(
                fields=["tenant_id", "year_month"],
                name="voyager_archive_tenant_ym_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogarchive",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="voyager_archive_tenant_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="auditlogarchive",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "year_month"],
                name="audit_archive_tenant_month_uniq",
            ),
        ),
    ]
