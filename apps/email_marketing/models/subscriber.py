"""Email subscriber model for list management."""

from __future__ import annotations

from django.db import models


class EmailSubscriber(models.Model):
    """An email subscriber within a tenant-scoped list.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        email: Subscriber email address.
        first_name: Optional first name.
        last_name: Optional last name.
        status: Subscriber status (active, unsubscribed, bounced, complained).
        source: Acquisition source (e.g. "website", "import", "api").
        tags: Array of string tags for segmentation.
        custom_fields: JSON key-value pairs for extra subscriber data.
        engagement_score: Normalized engagement score (0-100).
        subscribed_at: When the subscriber joined.
        unsubscribed_at: When the subscriber opted out (if applicable).
        last_opened_at: Timestamp of last email open.
        last_clicked_at: Timestamp of last email click.
        open_count: Total emails opened.
        click_count: Total email clicks.
        rfm_recency: Days since last engagement (for RFM scoring).
        rfm_frequency: Number of engagements (for RFM scoring).
        rfm_monetary: Revenue attributed (for RFM scoring).
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class Status(models.TextChoices):
        """Subscriber lifecycle statuses."""

        ACTIVE = "active", "Active"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
        BOUNCED = "bounced", "Bounced"
        COMPLAINED = "complained", "Complained"
        SUPPRESSED = "suppressed", "Suppressed"

    class Source(models.TextChoices):
        """Acquisition sources."""

        WEBSITE = "website", "Website"
        IMPORT = "import", "Import"
        API = "api", "API"
        FORM = "form", "Signup Form"
        INTEGRATION = "integration", "Integration"
        MANUAL = "manual", "Manual"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    email = models.EmailField(
        max_length=255,
        help_text="Subscriber email address",
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="First name",
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Last name",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text="Subscriber status",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
        help_text="Acquisition source",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for segmentation",
    )
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom field key-value pairs",
    )
    engagement_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        help_text="Normalized engagement score 0-100",
    )
    subscribed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the subscriber joined",
    )
    unsubscribed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscriber opted out",
    )
    last_opened_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last email open",
    )
    last_clicked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last email click",
    )
    open_count = models.PositiveIntegerField(
        default=0,
        help_text="Total emails opened",
    )
    click_count = models.PositiveIntegerField(
        default=0,
        help_text="Total email clicks",
    )
    rfm_recency = models.PositiveIntegerField(
        default=0,
        help_text="Days since last engagement (RFM recency)",
    )
    rfm_frequency = models.PositiveIntegerField(
        default=0,
        help_text="Number of engagements (RFM frequency)",
    )
    rfm_monetary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Revenue attributed (RFM monetary)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_email_subscriber"
        verbose_name = "Email Subscriber"
        verbose_name_plural = "Email Subscribers"
        ordering = ["-subscribed_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "email"]),
            models.Index(fields=["tenant_id", "engagement_score"]),
            models.Index(fields=["tenant_id", "subscribed_at"]),
            models.Index(fields=["tenant_id", "status", "engagement_score"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "email"],
                name="%(app_label)s_subscriber_tenant_email_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.status})"

    @property
    def full_name(self) -> str:
        """Return full name from first and last name fields."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else self.email

    @property
    def is_mailable(self) -> bool:
        """Return whether this subscriber can receive emails."""
        return self.status == self.Status.ACTIVE

    @property
    def rfm_score(self) -> str:
        """Calculate RFM score as a 3-digit string (e.g. '555')."""
        r = min(5, max(1, 6 - (self.rfm_recency // 30)))
        f = min(5, max(1, 1 + self.rfm_frequency // 5))
        m = min(5, max(1, 1 + int(self.rfm_monetary) // 100))
        return f"{r}{f}{m}"
