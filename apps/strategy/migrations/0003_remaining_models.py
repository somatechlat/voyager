# Generated initial migration for strategy


from django.db import migrations, models


class Confidence(models.TextChoices):
    ON_TRACK = "on_track", "On Track"
    AT_RISK = "at_risk", "At Risk"


class Direction(models.TextChoices):
    INCREASE = "increase", "Increase"
    DECREASE = "decrease", "Decrease"


class Level(models.TextChoices):
    COMPANY = "company", "Company"
    TEAM = "team", "Team"
    INDIVIDUAL = "individual", "Individual"


class Status(models.TextChoices):
    ON_TRACK = "on_track", "On Track"
    AT_RISK = "at_risk", "At Risk"
    BEHIND = "behind", "Behind"
    ACHIEVED = "achieved", "Achieved"
    MISSED = "missed", "Missed"


class Type(models.TextChoices):
    NUMERIC = "numeric", "Numeric"
    PERCENTAGE = "percentage", "Percentage"
    BINARY = "binary", "Binary"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("strategy", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="Objective",
            fields=[
                (
                    "parent",
                    models.ForeignKey(
                        to="self",
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="children",
                        help_text="Parent objective for hierarchical alignment",
                    ),
                ),
                (
                    "level",
                    models.CharField(
                        max_length=20,
                        choices=Level.choices,
                        db_index=True,
                        help_text="Scope level: company, team, or individual",
                    ),
                ),
                (
                    "team_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Team UUID (for team-level objectives)",
                    ),
                ),
                (
                    "owner_id",
                    models.UUIDField(db_index=True, help_text="Objective owner user UUID"),
                ),
                ("title", models.CharField(max_length=500, help_text="Objective title")),
                ("description", models.TextField(blank=True, help_text="Detailed description")),
                (
                    "quarter",
                    models.CharField(
                        max_length=10,
                        db_index=True,
                        help_text="Quarter identifier (e.g. '2026-Q2')",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.ON_TRACK,
                        db_index=True,
                        help_text="Current status",
                    ),
                ),
                (
                    "progress",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=0,
                        help_text="Overall progress (0.0 to 1.0)",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_okr_objective",
                "verbose_name": "OKR Objective",
                "verbose_name_plural": "OKR Objectives",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "level"]),
                    models.Index(fields=["tenant_id", "quarter"]),
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "owner_id"]),
                    models.Index(fields=["parent", "level"]),
                    models.Index(fields=["tenant_id", "team_id"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="KeyResult",
            fields=[
                (
                    "objective",
                    models.ForeignKey(
                        Objective,
                        on_delete=models.CASCADE,
                        related_name="key_results",
                        help_text="Parent objective",
                    ),
                ),
                ("title", models.CharField(max_length=500, help_text="Key result title")),
                (
                    "kr_type",
                    models.CharField(
                        max_length=20,
                        choices=Type.choices,
                        db_index=True,
                        help_text="Measurement type",
                    ),
                ),
                (
                    "target_value",
                    models.DecimalField(
                        max_digits=15,
                        decimal_places=4,
                        help_text="Target value to achieve",
                    ),
                ),
                (
                    "current_value",
                    models.DecimalField(
                        max_digits=15,
                        decimal_places=4,
                        default=0,
                        help_text="Current measured value",
                    ),
                ),
                (
                    "start_value",
                    models.DecimalField(
                        max_digits=15,
                        decimal_places=4,
                        default=0,
                        help_text="Starting baseline value",
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        max_length=10,
                        choices=Direction.choices,
                        default=Direction.INCREASE,
                        help_text="For numeric: whether to increase or decrease",
                    ),
                ),
                (
                    "unit",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        help_text="Unit of measurement (e.g. 'impressions', '%')",
                    ),
                ),
                (
                    "data_source",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Automated data source config: type, platform, metric, filters, refreshFrequency",
                    ),
                ),
                (
                    "progress",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=0,
                        help_text="Computed progress (0.0 to 1.0)",
                    ),
                ),
                (
                    "confidence",
                    models.CharField(
                        max_length=20,
                        choices=Confidence.choices,
                        default=Confidence.ON_TRACK,
                        help_text="On-track assessment",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_okr_key_result",
                "verbose_name": "OKR Key Result",
                "verbose_name_plural": "OKR Key Results",
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(fields=["objective", "kr_type"]),
                    models.Index(fields=["objective", "confidence"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="MarketResearch",
            fields=[
                (
                    "industry",
                    models.CharField(
                        max_length=255,
                        db_index=True,
                        help_text="Industry or vertical researched",
                    ),
                ),
                (
                    "trends",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Detected trends: name, velocity, acceleration, volume, trendScore, stage",
                    ),
                ),
                (
                    "market_size",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Market sizing: TAM, SAM, SOM with values and sources",
                    ),
                ),
                (
                    "audience_insights",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Audience insights: behaviors, preferences, segments",
                    ),
                ),
                (
                    "competitive_landscape",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Competitive landscape: positioning, market share, gaps",
                    ),
                ),
                (
                    "research_date",
                    models.DateField(
                        db_index=True,
                        help_text="Date the research was conducted",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_market_research",
                "verbose_name": "Market Research",
                "verbose_name_plural": "Market Research Entries",
                "ordering": ["-research_date"],
                "indexes": [
                    models.Index(fields=["tenant_id", "industry"]),
                    models.Index(fields=["tenant_id", "-research_date"]),
                ],
            },
        ),
    ]
