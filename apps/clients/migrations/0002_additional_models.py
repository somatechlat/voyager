# Generated initial migration for clients


from django.db import migrations, models


class CommType(models.TextChoices):
    EMAIL = "email", "Email"
    CALL = "call", "Call"
    MEETING = "meeting", "Meeting"
    NOTE = "note", "Note"


class Direction(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"
    INTERNAL = "internal", "Internal"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    MISSED = "missed", "Missed"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("clients", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ProjectMilestone",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "project",
                    models.ForeignKey(
                        Project,
                        on_delete=models.CASCADE,
                        related_name="milestones",
                        help_text="The parent project this milestone belongs to",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Milestone name")),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed milestone description",
                    ),
                ),
                (
                    "due_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        help_text="When the milestone is due",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                        help_text="Current milestone status",
                    ),
                ),
                (
                    "deliverables",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of deliverable items with name and status",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_project_milestone",
                "verbose_name": "Project Milestone",
                "verbose_name_plural": "Project Milestones",
                "ordering": ["due_date", "name"],
                "indexes": [
                    models.Index(fields=["project", "status"]),
                    models.Index(fields=["project", "due_date"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="CommunicationLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        Client,
                        on_delete=models.CASCADE,
                        related_name="communications",
                        help_text="The client this communication is with",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        Project,
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="communications",
                        help_text="Optional linked project",
                    ),
                ),
                (
                    "comm_type",
                    models.CharField(
                        max_length=20,
                        choices=CommType.choices,
                        db_index=True,
                        help_text="Type of communication",
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        max_length=10,
                        choices=Direction.choices,
                        default=Direction.OUTBOUND,
                        help_text="Direction of the communication",
                    ),
                ),
                (
                    "subject",
                    models.CharField(
                        max_length=500,
                        blank=True,
                        help_text="Subject line or brief title",
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        blank=True,
                        help_text="Full body content of the communication",
                    ),
                ),
                (
                    "participant_ids",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of participant user IDs",
                    ),
                ),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Duration in minutes (for calls/meetings)",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Extensible metadata (attachments, thread_id, etc.)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_communication_log",
                "verbose_name": "Communication Log",
                "verbose_name_plural": "Communication Logs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "client", "-created_at"]),
                    models.Index(fields=["tenant_id", "comm_type"]),
                    models.Index(fields=["tenant_id", "project"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ClientPortal",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "client",
                    models.OneToOneField(
                        Client,
                        on_delete=models.CASCADE,
                        related_name="portal",
                        help_text="The client this portal belongs to",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        max_length=255,
                        unique=True,
                        help_text="URL-safe portal slug",
                    ),
                ),
                (
                    "branding",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Branding config: colors, logo, fonts, custom CSS",
                    ),
                ),
                (
                    "custom_domain",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        help_text="Custom domain (e.g. portal.client.com)",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the portal is currently active",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_client_portal",
                "verbose_name": "Client Portal",
                "verbose_name_plural": "Client Portals",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["slug"]), models.Index(fields=["is_active"])],
            },
        ),
        migrations.CreateModel(
            name="ClientProfitability",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        Client,
                        on_delete=models.CASCADE,
                        related_name="profitability_records",
                        help_text="The client this profitability record is for",
                    ),
                ),
                ("period_start", models.DateField(help_text="Start of the reporting period")),
                ("period_end", models.DateField(help_text="End of the reporting period")),
                (
                    "revenue",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Total revenue for the period",
                    ),
                ),
                (
                    "costs",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Total costs for the period",
                    ),
                ),
                (
                    "margin_percent",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=2,
                        default=0,
                        help_text="Gross margin percentage",
                    ),
                ),
                (
                    "breakdown",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Detailed breakdown of revenue and cost components",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_client_profitability",
                "verbose_name": "Client Profitability",
                "verbose_name_plural": "Client Profitabilities",
                "ordering": ["-period_end", "client"],
                "indexes": [
                    models.Index(fields=["tenant_id", "client", "period_end"]),
                    models.Index(fields=["tenant_id", "period_start", "period_end"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "client", "period_start", "period_end"],
                        name="clients_profit_period_uniq",
                    )
                ],
            },
        ),
    ]
