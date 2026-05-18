"""Email template model with drag-drop block support."""

from __future__ import annotations

from django.db import models


class EmailTemplate(models.Model):
    """An email template built from draggable content blocks.

    Supports responsive design, JSON-based block definitions,
    inline-CSS generation for email-client compatibility, and
    AMP for Email markup.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Template name.
        category: Template category (e.g. "newsletter", "promotional").
        html: Rendered HTML with inline CSS for compatibility.
        json_design: JSON block definitions for the drag-drop builder.
        thumbnail: URL/path to a thumbnail preview image.
        is_amp: Whether the template includes AMP for Email markup.
        brand_kit: JSON brand colors, fonts, logo URL.
        preheader_text: Preheader/preview text shown in inboxes.
        compatibility_score: Compatibility score across email clients.
        compatibility_results: JSON detailed compatibility test results.
        plain_text: Auto-generated plain text fallback.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class Category(models.TextChoices):
        """Template categories."""

        NEWSLETTER = "newsletter", "Newsletter"
        PROMOTIONAL = "promotional", "Promotional"
        WELCOME = "welcome", "Welcome"
        ABANDONED_CART = "abandoned_cart", "Abandoned Cart"
        TRANSACTIONAL = "transactional", "Transactional"
        RE_ENGAGEMENT = "re_engagement", "Re-engagement"
        EVENT = "event", "Event"
        ANNOUNCEMENT = "announcement", "Announcement"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(
        max_length=255,
        help_text="Template name",
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.CUSTOM,
        db_index=True,
        help_text="Template category",
    )
    html = models.TextField(
        help_text="Rendered HTML with inline CSS",
    )
    json_design = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON block definitions for drag-drop builder",
    )
    thumbnail = models.URLField(
        blank=True,
        help_text="Thumbnail preview URL",
    )
    is_amp = models.BooleanField(
        default=False,
        help_text="Whether template includes AMP markup",
    )
    brand_kit = models.JSONField(
        default=dict,
        blank=True,
        help_text="Brand colors, fonts, logo URL",
    )
    preheader_text = models.CharField(
        max_length=150,
        blank=True,
        help_text="Preview text shown in email clients",
    )
    compatibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Overall compatibility score (0-100)",
    )
    compatibility_results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed compatibility test results per client",
    )
    plain_text = models.TextField(
        blank=True,
        help_text="Auto-generated plain text fallback",
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
        db_table = "voyager_email_template"
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "category"]),
            models.Index(fields=["tenant_id", "name"]),
            models.Index(fields=["tenant_id", "is_amp"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"
