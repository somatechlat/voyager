# Generated initial migration for campaigns


from django.db import migrations, models


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CHANGES_REQUESTED = "changes_requested", "Changes Requested"


class AttributionModel(models.TextChoices):
    FIRST_TOUCH = "first_touch", "First Touch"
    LAST_TOUCH = "last_touch", "Last Touch"
    LINEAR = "linear", "Linear"
    TIME_DECAY = "time_decay", "Time Decay"


class ChannelType(models.TextChoices):
    ORGANIC_SOCIAL = "organic_social", "Organic Social"
    PAID_SEARCH = "paid_search", "Paid Search"
    PAID_SOCIAL = "paid_social", "Paid Social"
    EMAIL = "email", "Email"
    SEO = "seo", "SEO"
    INFLUENCER = "influencer", "Influencer"
    DISPLAY = "display", "Display"
    VIDEO = "video", "Video"


class Objective(models.TextChoices):
    AWARENESS = "awareness", "Awareness"
    ENGAGEMENT = "engagement", "Engagement"
    CONVERSION = "conversion", "Conversion"
    RETENTION = "retention", "Retention"


class PacingType(models.TextChoices):
    EVEN = "even", "Even"
    ACCELERATED = "accelerated", "Accelerated"
    FRONT_LOADED = "front_loaded", "Front Loaded"
    PERFORMANCE = "performance", "Performance"


class Stage(models.TextChoices):
    PLANNING = "planning", "Planning"
    BRIEF = "brief", "Brief"
    CREATIVE = "creative", "Creative"
    APPROVAL = "approval", "Approval"
    LAUNCH = "launch", "Launch"
    MONITORING = "monitoring", "Monitoring"
    OPTIMIZATION = "optimization", "Optimization"
    REPORTING = "reporting", "Reporting"


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"
    CANCELLED = "cancelled", "Cancelled"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Campaign",
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
                        related_name="campaigns",
                        help_text="The client this campaign belongs to",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Campaign name")),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed campaign description",
                    ),
                ),
                (
                    "objective",
                    models.CharField(
                        max_length=20,
                        choices=Objective.choices,
                        default=Objective.AWARENESS,
                        db_index=True,
                        help_text="Campaign objective type",
                    ),
                ),
                (
                    "stage",
                    models.CharField(
                        max_length=20,
                        choices=Stage.choices,
                        default=Stage.PLANNING,
                        db_index=True,
                        help_text="Current lifecycle stage",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Campaign status",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        help_text="Campaign start date",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(null=True, blank=True, help_text="Campaign end date"),
                ),
                (
                    "budget",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Total campaign budget",
                    ),
                ),
                (
                    "current_spend",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Total amount spent so far",
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        max_length=3,
                        default="USD",
                        help_text="Three-letter currency code",
                    ),
                ),
                (
                    "pacing_type",
                    models.CharField(
                        max_length=20,
                        choices=PacingType.choices,
                        default=PacingType.EVEN,
                        help_text="Budget pacing algorithm",
                    ),
                ),
                (
                    "attribution_model",
                    models.CharField(
                        max_length=20,
                        choices=AttributionModel.choices,
                        default=AttributionModel.LAST_TOUCH,
                        help_text="Revenue attribution model",
                    ),
                ),
                (
                    "channels",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of configured channel types",
                    ),
                ),
                (
                    "target_audience",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Audience targeting configuration",
                    ),
                ),
                (
                    "kpis",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Key performance indicators configuration",
                    ),
                ),
                (
                    "alerts_sent",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Tracking of budget alerts already sent",
                    ),
                ),
                (
                    "parent_campaign",
                    models.ForeignKey(
                        to="self",
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="child_campaigns",
                        help_text="Parent campaign for hierarchies",
                    ),
                ),
                (
                    "cloned_from",
                    models.ForeignKey(
                        to="self",
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="clones",
                        help_text="Original campaign if this is a clone",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        db_index=True,
                        help_text="User ID of the campaign creator",
                    ),
                ),
                (
                    "brief_approved",
                    models.BooleanField(
                        default=False,
                        help_text="Whether the brief has been approved",
                    ),
                ),
                (
                    "all_creatives_approved",
                    models.BooleanField(
                        default=False,
                        help_text="Whether all creative assets are approved",
                    ),
                ),
                (
                    "approval_status",
                    models.CharField(
                        max_length=20,
                        choices=ApprovalStatus.choices,
                        default=ApprovalStatus.PENDING,
                        help_text="Stakeholder approval status",
                    ),
                ),
                (
                    "all_platforms_published",
                    models.BooleanField(
                        default=False,
                        help_text="Whether all platform content is live",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_campaign",
                "verbose_name": "Campaign",
                "verbose_name_plural": "Campaigns",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "stage"]),
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "client", "stage"]),
                    models.Index(fields=["tenant_id", "start_date", "end_date"]),
                    models.Index(fields=["tenant_id", "objective"]),
                    models.Index(fields=["tenant_id", "created_by"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="CampaignChannel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "campaign",
                    models.ForeignKey(
                        Campaign,
                        on_delete=models.CASCADE,
                        related_name="channel_configs",
                        help_text="Parent campaign",
                    ),
                ),
                (
                    "channel_type",
                    models.CharField(
                        max_length=30,
                        choices=ChannelType.choices,
                        db_index=True,
                        help_text="Type of marketing channel",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        max_length=50,
                        help_text="Platform name (e.g. google_ads, meta_ads)",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Channel-specific configuration",
                    ),
                ),
                (
                    "daily_budget",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Daily spend limit for this channel",
                    ),
                ),
                (
                    "total_spend",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Total spend on this channel",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                        help_text="Channel status",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        help_text="Channel-specific start date",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        help_text="Channel-specific end date",
                    ),
                ),
                (
                    "dependencies",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of channel IDs this channel depends on",
                    ),
                ),
                (
                    "lead_time_days",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Days needed before this channel can launch",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_campaign_channel",
                "verbose_name": "Campaign Channel",
                "verbose_name_plural": "Campaign Channels",
                "ordering": ["channel_type", "-created_at"],
                "indexes": [
                    models.Index(fields=["campaign", "channel_type"]),
                    models.Index(fields=["campaign", "status"]),
                    models.Index(fields=["channel_type", "platform"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["campaign", "channel_type", "platform"],
                        name="campaign_channel_uniq",
                    )
                ],
            },
        ),
    ]
