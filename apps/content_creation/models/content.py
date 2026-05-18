"""ContentGeneration model — stores all AI-generated content.

Tracks text, image, and video generations with metadata about the model
used, token consumption, timing, brand kit, and template references.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class ContentGeneration(UUIDModel, TimeStampedModel, TenantModel):
    """A single AI content generation run.

    Attributes:
        title: Human-readable title for the generation.
        prompt: The raw prompt / brief submitted by the user.
        content_type: Type of content — text, image, or video.
        status: Lifecycle state of the generation.
        body_text: Generated text content (for text generations).
        media_urls: JSON list of URLs for generated images / videos.
        model_used: AI model that produced the content.
        tokens_used: Number of tokens consumed during generation.
        generation_time_ms: Wall-clock time for generation in milliseconds.
        brand_kit_id: Optional brand kit applied.
        template_id: Optional template used.
        created_by: UUID of the user who initiated the generation.
    """

    class ContentType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        GENERATING = "generating", "Generating"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"

    title = models.CharField(
        max_length=512,
        help_text="Human-readable title for the generation",
    )
    prompt = models.TextField(
        help_text="Raw prompt / brief submitted by the user",
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        db_index=True,
        help_text="Type of content generated",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Current lifecycle state",
    )
    body_text = models.TextField(
        blank=True,
        help_text="Generated text content",
    )
    media_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of URLs for generated images / videos",
    )
    model_used = models.CharField(
        max_length=50,
        blank=True,
        help_text="AI model that produced the content (e.g. gpt-4o)",
    )
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text="Tokens consumed during generation",
    )
    generation_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Wall-clock generation time in milliseconds",
    )
    brand_kit_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Brand kit applied to this generation",
    )
    template_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Template used as a base",
    )
    created_by = models.CharField(
        max_length=256,
        db_index=True,
        help_text="UUID of the user who initiated the generation",
    )

    # Scoring fields
    readability_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Flesch-Kincaid readability score",
    )
    engagement_prediction = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Predicted engagement score (0-100)",
    )
    brand_compliance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Brand compliance score (0-100)",
    )
    seo_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="SEO keyword density score (0-100)",
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="ISO 639-1 language code",
    )

    class Meta:
        db_table = "voyager_content_generation"
        verbose_name = "Content Generation"
        verbose_name_plural = "Content Generations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "content_type"]),
            models.Index(fields=["tenant_id", "created_by"]),
            models.Index(fields=["tenant_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.content_type}) — {self.status}"
