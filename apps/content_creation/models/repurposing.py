"""ContentRepurposingRule model — rules for format transformation.

Stores transformation rules that convert content from one format
to another (e.g. blog to Twitter thread, video to blog post).
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class ContentRepurposingRule(UUIDModel, TimeStampedModel, TenantModel):
    """A rule that transforms content from one format to another.

    Attributes:
        source_format: The input content format.
        target_formats: JSON list of supported output formats.
        transformation_rules: JSON rules for the transformation.
        name: Human-readable rule name.
        description: Optional explanation.
        is_active: Whether the rule is currently active.
    """

    class SourceFormat(models.TextChoices):
        BLOG = "blog", "Blog Post"
        VIDEO = "video", "Video"
        PODCAST = "podcast", "Podcast"
        NEWSLETTER = "newsletter", "Newsletter"
        SOCIAL = "social", "Social Post"
        EMAIL = "email", "Email"

    name = models.CharField(
        max_length=255,
        help_text="Human-readable rule name",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional explanation of the transformation",
    )
    source_format = models.CharField(
        max_length=32,
        choices=SourceFormat.choices,
        db_index=True,
        help_text="Input content format",
    )
    target_formats = models.JSONField(
        default=list,
        blank=True,
        help_text="Supported output formats [twitter, linkedin, instagram, ...]",
    )
    transformation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Transformation configuration rules",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the rule is currently active",
    )

    class Meta:
        db_table = "voyager_content_repurposing_rule"
        verbose_name = "Content Repurposing Rule"
        verbose_name_plural = "Content Repurposing Rules"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "source_format"]),
            models.Index(fields=["tenant_id", "is_active"]),
        ]

    def __str__(self) -> str:
        targets = ", ".join(self.target_formats) if self.target_formats else "none"
        return f"{self.source_format} -> {targets}"
