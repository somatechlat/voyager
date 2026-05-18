# Generated initial migration for governance_v2


from django.db import migrations, models


class Action(models.TextChoices):
    BLOCK = "block", "Block"
    FLAG = "flag", "Flag for Review"
    WARN = "warn", "Warn Only"


class Industry(models.TextChoices):
    HEALTHCARE = "healthcare", "Healthcare"
    FINANCE = "finance", "Finance"
    ADVERTISING = "advertising", "Advertising"
    CHILDREN = "children", "Children's Content"
    ALCOHOL = "alcohol", "Alcohol"
    CANNABIS = "cannabis", "Cannabis"
    GENERAL = "general", "General"


class RuleType(models.TextChoices):
    PROFANITY = "profanity", "Profanity Filter"
    SENSITIVE_TOPIC = "sensitive_topic", "Sensitive Topic Filter"
    COMPETITOR = "competitor", "Competitor Mention Filter"
    MEDICAL_CLAIM = "medical_claim", "Medical Claim Check"
    FINANCIAL_PROMISE = "financial_promise", "Financial Promise Check"
    DISCLAIMER = "disclaimer", "Required Disclaimer Check"
    CUSTOM = "custom", "Custom Rule"


class Severity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BrandSafetyRule",
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
                ("name", models.CharField(max_length=255, help_text="Human-readable rule name")),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional explanation of the rule's purpose",
                    ),
                ),
                (
                    "rule_type",
                    models.CharField(
                        max_length=32,
                        choices=RuleType.choices,
                        help_text="Category of brand safety check",
                    ),
                ),
                (
                    "conditions",
                    models.JSONField(
                        default=dict,
                        help_text="JSON conditions (patterns, word lists, thresholds)",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        max_length=20,
                        choices=Action.choices,
                        default=Action.FLAG,
                        help_text="Response action when the rule triggers",
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        max_length=20,
                        choices=Severity.choices,
                        default=Severity.HIGH,
                        help_text="Severity level of violations from this rule",
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(default=True, help_text="Whether the rule is active"),
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
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_brand_safety_rule",
                "verbose_name": "Brand Safety Rule",
                "verbose_name_plural": "Brand Safety Rules",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "rule_type", "enabled"]),
                    models.Index(fields=["tenant_id", "severity", "enabled"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ComplianceRule",
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
                    "industry",
                    models.CharField(
                        max_length=32,
                        choices=Industry.choices,
                        help_text="Target industry sector",
                    ),
                ),
                (
                    "regulation",
                    models.CharField(
                        max_length=100,
                        help_text="Regulation code (e.g. 'FDA 21 CFR 202')",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Human-readable rule name")),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed explanation of the requirement",
                    ),
                ),
                (
                    "check_type",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        help_text="Mechanism used to validate compliance",
                    ),
                ),
                (
                    "check_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON configuration for the compliance check",
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        max_length=20,
                        choices=Severity.choices,
                        default=Severity.HIGH,
                        help_text="Severity level of violations",
                    ),
                ),
                (
                    "legal_reference",
                    models.TextField(
                        blank=True,
                        help_text="Citation to the legal text",
                    ),
                ),
                (
                    "remediation",
                    models.TextField(blank=True, help_text="Steps to resolve a violation"),
                ),
                (
                    "enabled",
                    models.BooleanField(default=True, help_text="Whether the rule is active"),
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
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_compliance_rule",
                "verbose_name": "Compliance Rule",
                "verbose_name_plural": "Compliance Rules",
                "ordering": ["industry", "regulation", "name"],
                "indexes": [
                    models.Index(fields=["tenant_id", "industry", "enabled"]),
                    models.Index(fields=["tenant_id", "regulation", "enabled"]),
                    models.Index(fields=["tenant_id", "severity", "enabled"]),
                ],
            },
        ),
    ]
