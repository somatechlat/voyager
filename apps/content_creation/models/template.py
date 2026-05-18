"""ContentTemplate model — Jinja2-based content templates.

Stores reusable templates with variable definitions, default values,
and optional brand kit associations for consistent content creation.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class ContentTemplate(UUIDModel, TimeStampedModel, TenantModel):
    """A reusable Jinja2 content template.

    Attributes:
        name: Human-readable template name.
        description: Optional longer explanation.
        category: Content category.
        content_type: Type of content this template produces.
        body: Jinja2 template body.
        variables: JSON list of variable definitions.
        default_values: JSON default values for variables.
        brand_kit_id: Optional default brand kit.
        usage_count: Number of times this template has been used.
        is_public: Whether this is a system-wide public template.
        created_by: UUID of the user who created the template.
    """

    class Category(models.TextChoices):
        SOCIAL = "social", "Social Media"
        BLOG = "blog", "Blog"
        EMAIL = "email", "Email"
        AD = "ad", "Advertisement"
        PRODUCT = "product", "Product Description"
        NEWSLETTER = "newsletter", "Newsletter"
        PRESS = "press", "Press Release"

    class ContentType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    name = models.CharField(
        max_length=255,
        help_text="Human-readable template name",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional longer explanation",
    )
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        db_index=True,
        help_text="Content category",
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.TEXT,
        help_text="Type of content this template produces",
    )
    body = models.TextField(
        help_text="Jinja2 template body",
    )
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text="Variable definitions [{name, type, required, default}]",
    )
    default_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default values for template variables",
    )
    brand_kit_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Optional default brand kit",
    )
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been rendered",
    )
    is_public = models.BooleanField(
        default=False,
        help_text="System-wide public template flag",
    )
    created_by = models.CharField(
        max_length=256,
        blank=True,
        help_text="UUID of the user who created the template",
    )

    class Meta:
        db_table = "voyager_content_template"
        verbose_name = "Content Template"
        verbose_name_plural = "Content Templates"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "category"]),
            models.Index(fields=["is_public"]),
            models.Index(fields=["tenant_id", "usage_count"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"
