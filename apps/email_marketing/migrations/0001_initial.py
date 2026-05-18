# Generated initial migration for email_marketing


from django.db import migrations, models


class Category(models.TextChoices):
    NEWSLETTER = "newsletter", "Newsletter"
    PROMOTIONAL = "promotional", "Promotional"
    WELCOME = "welcome", "Welcome"
    ABANDONED_CART = "abandoned_cart", "Abandoned Cart"
    TRANSACTIONAL = "transactional", "Transactional"
    RE_ENGAGEMENT = "re_engagement", "Re-engagement"
    EVENT = "event", "Event"
    ANNOUNCEMENT = "announcement", "Announcement"
    CUSTOM = "custom", "Custom"


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    SENDING = "sending", "Sending"
    SENT = "sent", "Sent"
    PAUSED = "paused", "Paused"
    ARCHIVED = "archived", "Archived"
    CANCELLED = "cancelled", "Cancelled"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailTemplate",
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
                ("name", models.CharField(max_length=255, help_text="Template name")),
                (
                    "category",
                    models.CharField(
                        max_length=30,
                        choices=Category.choices,
                        default=Category.CUSTOM,
                        db_index=True,
                        help_text="Template category",
                    ),
                ),
                ("html", models.TextField(help_text="Rendered HTML with inline CSS")),
                (
                    "json_design",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="JSON block definitions for drag-drop builder",
                    ),
                ),
                ("thumbnail", models.URLField(blank=True, help_text="Thumbnail preview URL")),
                (
                    "is_amp",
                    models.BooleanField(
                        default=False,
                        help_text="Whether template includes AMP markup",
                    ),
                ),
                (
                    "brand_kit",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Brand colors, fonts, logo URL",
                    ),
                ),
                (
                    "preheader_text",
                    models.CharField(
                        max_length=150,
                        blank=True,
                        help_text="Preview text shown in email clients",
                    ),
                ),
                (
                    "compatibility_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Overall compatibility score (0-100)",
                    ),
                ),
                (
                    "compatibility_results",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Detailed compatibility test results per client",
                    ),
                ),
                (
                    "plain_text",
                    models.TextField(
                        blank=True,
                        help_text="Auto-generated plain text fallback",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
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
                "db_table": "voyager_email_template",
                "verbose_name": "Email Template",
                "verbose_name_plural": "Email Templates",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "category"]),
                    models.Index(fields=["tenant_id", "name"]),
                    models.Index(fields=["tenant_id", "is_amp"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="EmailCampaign",
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
                ("name", models.CharField(max_length=255, help_text="Campaign name")),
                (
                    "subject_line",
                    models.CharField(
                        max_length=200,
                        blank=True,
                        help_text="Email subject line",
                    ),
                ),
                (
                    "preview_text",
                    models.CharField(
                        max_length=150,
                        blank=True,
                        help_text="Preview text shown in inbox",
                    ),
                ),
                (
                    "from_name",
                    models.CharField(
                        max_length=100,
                        blank=True,
                        help_text="Display name for the sender",
                    ),
                ),
                (
                    "from_email",
                    models.EmailField(
                        max_length=255,
                        blank=True,
                        help_text="Sender email address",
                    ),
                ),
                (
                    "reply_to",
                    models.EmailField(
                        max_length=255,
                        blank=True,
                        help_text="Reply-to email address",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        EmailTemplate,
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="campaigns",
                        help_text="Linked email template",
                    ),
                ),
                (
                    "segment_id_ref",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Foreign key reference to audience segment",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Campaign lifecycle status",
                    ),
                ),
                (
                    "scheduled_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the campaign should be sent",
                    ),
                ),
                (
                    "sent_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the campaign was actually sent",
                    ),
                ),
                (
                    "total_recipients",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of recipients targeted",
                    ),
                ),
                (
                    "delivered",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of emails delivered",
                    ),
                ),
                ("opens", models.PositiveIntegerField(default=0, help_text="Total opens")),
                ("unique_opens", models.PositiveIntegerField(default=0, help_text="Unique opens")),
                ("clicks", models.PositiveIntegerField(default=0, help_text="Total clicks")),
                (
                    "unique_clicks",
                    models.PositiveIntegerField(default=0, help_text="Unique clicks"),
                ),
                ("bounces", models.PositiveIntegerField(default=0, help_text="Total bounces")),
                (
                    "hard_bounces",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of hard bounces",
                    ),
                ),
                (
                    "spam_complaints",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of spam complaints",
                    ),
                ),
                (
                    "unsubscribes",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of unsubscribes",
                    ),
                ),
                (
                    "revenue",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        default=0.0,
                        help_text="Revenue attributed to the campaign",
                    ),
                ),
                (
                    "send_progress_pct",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=0.0,
                        help_text="Send progress percentage",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
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
                "db_table": "voyager_email_campaign",
                "verbose_name": "Email Campaign",
                "verbose_name_plural": "Email Campaigns",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "scheduled_at"]),
                    models.Index(fields=["tenant_id", "status", "scheduled_at"]),
                    models.Index(fields=["tenant_id", "sent_at"]),
                ],
            },
        ),
    ]
