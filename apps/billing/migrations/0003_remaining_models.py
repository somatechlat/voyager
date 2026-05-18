# Generated initial migration for billing


from django.db import migrations, models


class Dimension(models.TextChoices):
    CLIENT = "client", "Client"
    PROJECT = "project", "Project"
    SERVICE = "service", "Service"
    TEAM_MEMBER = "team_member", "Team Member"
    CHANNEL = "channel", "Channel"
    MONTH = "month", "Month"
    QUARTER = "quarter", "Quarter"


class RenewalType(models.TextChoices):
    AUTO = "auto", "Auto-Renew"
    MANUAL = "manual", "Manual"
    FIXED_TERM = "fixed_term", "Fixed Term"


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    FINAL = "final", "Final"
    ARCHIVED = "archived", "Archived"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("billing", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="ProfitabilityReport",
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
                    "dimension",
                    models.CharField(
                        max_length=20,
                        choices=Dimension.choices,
                        db_index=True,
                        help_text="Analysis dimension",
                    ),
                ),
                (
                    "dimension_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="ID of the entity being analyzed",
                    ),
                ),
                (
                    "dimension_name",
                    models.CharField(max_length=255, help_text="Human-readable name"),
                ),
                (
                    "period_start",
                    models.DateField(
                        db_index=True,
                        help_text="Start of reporting period",
                    ),
                ),
                (
                    "period_end",
                    models.DateField(db_index=True, help_text="End of reporting period"),
                ),
                (
                    "revenue",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Total revenue",
                    ),
                ),
                (
                    "labor_cost",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Labor costs",
                    ),
                ),
                (
                    "tool_cost",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Tool/subscription costs",
                    ),
                ),
                (
                    "expense_cost",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Expense costs",
                    ),
                ),
                (
                    "overhead_cost",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Overhead allocation",
                    ),
                ),
                (
                    "total_cost",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Sum of all costs",
                    ),
                ),
                (
                    "gross_profit",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Revenue - total cost",
                    ),
                ),
                (
                    "gross_margin_pct",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=2,
                        default=0,
                        help_text="Gross margin percentage",
                    ),
                ),
                (
                    "benchmark_margin_pct",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Benchmark margin for comparison",
                    ),
                ),
                (
                    "margin_vs_benchmark",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Difference from benchmark",
                    ),
                ),
                (
                    "breakdown",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Detailed P&L breakdown",
                    ),
                ),
                (
                    "trend_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Month-over-month trend",
                    ),
                ),
                (
                    "hours_billed",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        default=0,
                        help_text="Total hours billed",
                    ),
                ),
                (
                    "hours_logged",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        default=0,
                        help_text="Total hours logged",
                    ),
                ),
                (
                    "effective_hourly_rate",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Average effective hourly rate",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Report status",
                    ),
                ),
                (
                    "is_current",
                    models.BooleanField(
                        default=True,
                        db_index=True,
                        help_text="Whether this is the current report",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_profitability_report",
                "verbose_name": "Profitability Report",
                "verbose_name_plural": "Profitability Reports",
                "ordering": ["-period_end", "dimension", "-gross_margin_pct"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "dimension", "dimension_id", "period_end"],
                        name="voy_pr_tenant_dim_id_period_idx",
                    ),
                    models.Index(
                        fields=["tenant_id", "period_start", "period_end"],
                        name="voy_pr_tenant_period_range_idx",
                    ),
                    models.Index(
                        fields=["tenant_id", "dimension", "-gross_margin_pct"],
                        name="voy_pr_tenant_dim_margin_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=[
                            "tenant_id",
                            "dimension",
                            "dimension_id",
                            "period_start",
                            "period_end",
                        ],
                        name="voyager_pr_unique_period",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Retainer",
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
                    "client",
                    models.ForeignKey(
                        to="clients.Client",
                        on_delete=models.CASCADE,
                        related_name="retainers",
                        help_text="The client this retainer is for",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Retainer agreement name")),
                (
                    "monthly_amount",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        help_text="Monthly retainer amount",
                    ),
                ),
                (
                    "monthly_hours",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Hours included per month",
                    ),
                ),
                ("start_date", models.DateField(help_text="Retainer start date")),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        help_text="Retainer end date (null = ongoing)",
                    ),
                ),
                (
                    "renewal_type",
                    models.CharField(
                        max_length=20,
                        choices=RenewalType.choices,
                        default=RenewalType.AUTO,
                        help_text="How the retainer renews",
                    ),
                ),
                (
                    "renewal_term_months",
                    models.PositiveIntegerField(
                        default=12,
                        help_text="Renewal term in months",
                    ),
                ),
                (
                    "auto_invoice",
                    models.BooleanField(
                        default=True,
                        help_text="Auto-generate monthly invoice",
                    ),
                ),
                (
                    "invoice_day",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Day of month to generate invoice",
                    ),
                ),
                (
                    "rollover_policy",
                    models.JSONField(
                        default=dict,
                        help_text="Rollover rules: {type, maxRolloverHours, maxRolloverMonths, expiration}",
                    ),
                ),
                (
                    "overage_rate",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        blank=True,
                        null=True,
                        help_text="Hourly rate for overage hours",
                    ),
                ),
                (
                    "overage_billing_threshold",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        default=0,
                        help_text="Minimum overage hours before billing",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.ACTIVE,
                        db_index=True,
                        help_text="Retainer status",
                    ),
                ),
                (
                    "currency",
                    models.CharField(max_length=3, default="USD", help_text="Currency code"),
                ),
                (
                    "consumption_alert_thresholds",
                    models.JSONField(
                        default=list,
                        help_text="Alert thresholds: [75, 90, 100]",
                    ),
                ),
                (
                    "last_invoiced_month",
                    models.DateField(
                        blank=True,
                        null=True,
                        help_text="Last month that was invoiced",
                    ),
                ),
                (
                    "total_hours_consumed",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        default=0,
                        help_text="Total hours consumed",
                    ),
                ),
                (
                    "total_amount_invoiced",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        default=0,
                        help_text="Total amount invoiced",
                    ),
                ),
                ("notes", models.TextField(blank=True, help_text="Internal notes")),
                (
                    "contract_url",
                    models.URLField(
                        blank=True,
                        default="",
                        help_text="Link to contract document",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Extensible metadata",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_retainer",
                "verbose_name": "Retainer",
                "verbose_name_plural": "Retainers",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "client", "status"],
                        name="voy_ret_tenant_client_status_idx",
                    ),
                    models.Index(
                        fields=["tenant_id", "status", "start_date"],
                        name="voy_ret_tenant_status_start_idx",
                    ),
                    models.Index(
                        fields=["tenant_id", "auto_invoice", "status"],
                        name="voy_ret_tenant_auto_status_idx",
                    ),
                ],
            },
        ),
    ]
