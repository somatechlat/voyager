# Generated initial migration for billing


from django.db import migrations, models


class AlertLevel(models.TextChoices):
    NONE = "none", "None"
    LOW = "low", "50%"
    MEDIUM = "medium", "75%"
    HIGH = "high", "90%"
    CRITICAL = "critical", "100%"


class BudgetType(models.TextChoices):
    FIXED = "fixed", "Fixed Price"
    HOURLY = "hourly", "Hourly"
    RETAINER = "retainer", "Retainer"
    HYBRID = "hybrid", "Hybrid"


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


class TrackingMode(models.TextChoices):
    TIMER = "timer", "Timer"
    MANUAL = "manual", "Manual"
    AUTOMATIC = "automatic", "Automatic"
    CALENDAR = "calendar", "Calendar"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TimeEntry",
            fields=[
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier",
                    ),
                ),
                (
                    "user_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="User who logged time",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        to="clients.Client",
                        on_delete=models.CASCADE,
                        related_name="time_entries",
                        help_text="The client this time is for",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        to="clients.Project",
                        on_delete=models.CASCADE,
                        related_name="time_entries",
                        blank=True,
                        null=True,
                        help_text="The project this time is for",
                    ),
                ),
                (
                    "task_name",
                    models.CharField(
                        max_length=500,
                        blank=True,
                        help_text="Name of the task worked on",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, help_text="Detailed description of work"),
                ),
                (
                    "tracking_mode",
                    models.CharField(
                        max_length=20,
                        choices=TrackingMode.choices,
                        default=TrackingMode.MANUAL,
                        db_index=True,
                        help_text="How the time was tracked",
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        db_index=True,
                        help_text="When the work session started",
                    ),
                ),
                (
                    "ended_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="When the work session ended",
                    ),
                ),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(
                        help_text="Actual duration in minutes",
                    ),
                ),
                (
                    "rounded_minutes",
                    models.PositiveIntegerField(
                        help_text="Duration after rounding rules applied",
                    ),
                ),
                (
                    "rounding_mode",
                    models.CharField(
                        max_length=20,
                        choices=RoundingMode.choices,
                        default=RoundingMode.NEAREST,
                        help_text="Rounding mode applied",
                    ),
                ),
                (
                    "rounding_increment",
                    models.PositiveIntegerField(
                        default=15,
                        help_text="Rounding increment in minutes",
                    ),
                ),
                (
                    "billing_rate",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Hourly billing rate for this entry",
                    ),
                ),
                (
                    "billable_amount",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Calculated billable amount",
                    ),
                ),
                (
                    "is_billable",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this entry is billable",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Approval status",
                    ),
                ),
                (
                    "timesheet_week",
                    models.DateField(
                        blank=True,
                        null=True,
                        db_index=True,
                        help_text="Week this entry belongs to",
                    ),
                ),
                (
                    "approver_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        default="",
                        help_text="User who approved/rejected",
                    ),
                ),
                (
                    "approved_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="When the entry was approved",
                    ),
                ),
                (
                    "rejection_reason",
                    models.TextField(blank=True, help_text="Reason for rejection"),
                ),
                (
                    "source_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Source data for automatic entries (git commits, etc.)",
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        to="billing.Invoice",
                        on_delete=models.SET_NULL,
                        related_name="time_entries",
                        blank=True,
                        null=True,
                        help_text="Invoice this entry was billed on",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_time_entry",
                "verbose_name": "Time Entry",
                "verbose_name_plural": "Time Entries",
                "ordering": ["-started_at"],
                "indexes": [
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
                ],
            },
        ),
        migrations.CreateModel(
            name="ProjectBudget",
            fields=[
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier",
                    ),
                ),
                (
                    "project",
                    models.OneToOneField(
                        to="clients.Project",
                        on_delete=models.CASCADE,
                        related_name="budget_detail",
                        help_text="The project this budget is for",
                    ),
                ),
                (
                    "budget_type",
                    models.CharField(
                        max_length=20,
                        choices=BudgetType.choices,
                        default=BudgetType.FIXED,
                        db_index=True,
                        help_text="How the project is budgeted",
                    ),
                ),
                (
                    "total_budget",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        help_text="Total budget amount",
                    ),
                ),
                (
                    "hours_allocated",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Hours allocated (for hourly/retainer types)",
                    ),
                ),
                (
                    "hourly_rate",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Hourly rate (for hourly/hybrid types)",
                    ),
                ),
                (
                    "monthly_retainer",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Monthly retainer amount (for retainer type)",
                    ),
                ),
                (
                    "base_retainer",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Base retainer (for hybrid type)",
                    ),
                ),
                (
                    "overage_rate",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Rate for hours beyond allocation",
                    ),
                ),
                (
                    "budget_consumed",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Amount consumed so far",
                    ),
                ),
                (
                    "hours_consumed",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        default=0,
                        help_text="Hours consumed so far",
                    ),
                ),
                (
                    "alert_level",
                    models.CharField(
                        max_length=20,
                        choices=AlertLevel.choices,
                        default=AlertLevel.NONE,
                        db_index=True,
                        help_text="Current budget alert level",
                    ),
                ),
                (
                    "alert_thresholds",
                    models.JSONField(
                        default=dict,
                        help_text="Custom alert thresholds (JSON with pct -> level mapping)",
                    ),
                ),
                (
                    "last_alert_sent_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="When the last alert was sent",
                    ),
                ),
                (
                    "forecast_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Pre-computed forecast data",
                    ),
                ),
                ("start_date", models.DateField(help_text="Budget period start")),
                (
                    "end_date",
                    models.DateField(blank=True, null=True, help_text="Budget period end"),
                ),
                (
                    "currency",
                    models.CharField(
                        max_length=3,
                        default="USD",
                        help_text="Currency code (ISO 4217)",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_project_budget",
                "verbose_name": "Project Budget",
                "verbose_name_plural": "Project Budgets",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "budget_type", "alert_level"],
                        name="voy_pb_tenant_type_alert_idx",
                    ),
                    models.Index(
                        fields=["tenant_id", "start_date", "end_date"],
                        name="voy_pb_tenant_date_range_idx",
                    ),
                ],
            },
        ),
    ]
