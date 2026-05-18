"""BrandKit model — stores brand voice, visual, and compliance guidelines.

Defines forbidden words, required phrases, color palettes, tone rules,
and competitor lists that all content must adhere to.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class BrandKit(UUIDModel, TimeStampedModel, TenantModel):
    """A brand kit defines voice, visual, and compliance guidelines.

    Attributes:
        name: Human-readable kit name.
        description: Optional longer explanation.
        voice: Primary voice descriptor.
        tone_rules: JSON tone enforcement rules.
        forbidden_words: JSON list of words to avoid.
        required_phrases: JSON list of phrases that must appear.
        color_palette: JSON color definitions.
        logo_url: URL to the brand logo asset.
        font_preferences: JSON font configuration.
        competitor_list: JSON list of competitor names to avoid mentioning.
        avoid_topics: JSON list of topics to avoid.
        target_audience: JSON audience demographic data.
    """

    class Voice(models.TextChoices):
        PROFESSIONAL = "professional", "Professional"
        CASUAL = "casual", "Casual"
        FRIENDLY = "friendly", "Friendly"
        HUMOROUS = "humorous", "Humorous"
        URGENT = "urgent", "Urgent"
        INSPIRATIONAL = "inspirational", "Inspirational"
        EDUCATIONAL = "educational", "Educational"
        PROVOCATIVE = "provocative", "Provocative"
        EMPATHETIC = "empathetic", "Empathetic"

    name = models.CharField(
        max_length=255,
        help_text="Brand kit name",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional longer explanation",
    )
    voice = models.CharField(
        max_length=32,
        choices=Voice.choices,
        default=Voice.PROFESSIONAL,
        help_text="Primary voice descriptor",
    )
    tone_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="Tone enforcement rules",
    )
    forbidden_words = models.JSONField(
        default=list,
        blank=True,
        help_text="Words that must not appear in content",
    )
    required_phrases = models.JSONField(
        default=list,
        blank=True,
        help_text="Phrases that must appear in content",
    )
    color_palette = models.JSONField(
        default=list,
        blank=True,
        help_text="Brand color definitions [{name, hex} ..]",
    )
    logo_url = models.URLField(
        blank=True,
        help_text="URL to brand logo asset",
    )
    font_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Font configuration {heading, body, sizes}",
    )
    competitor_list = models.JSONField(
        default=list,
        blank=True,
        help_text="Competitor names to avoid mentioning",
    )
    avoid_topics = models.JSONField(
        default=list,
        blank=True,
        help_text="Topics to avoid in content",
    )
    target_audience = models.JSONField(
        default=dict,
        blank=True,
        help_text="Target audience demographics and psychographics",
    )
    min_readability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=60.0,
        help_text="Minimum Flesch reading ease score",
    )
    min_compliance_score = models.IntegerField(
        default=75,
        help_text="Minimum compliance score to pass (0-100)",
    )

    class Meta:
        db_table = "voyager_brand_kit"
        verbose_name = "Brand Kit"
        verbose_name_plural = "Brand Kits"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "name"]),
        ]

    def __str__(self) -> str:
        return self.name
