"""Competitor analysis models — SP-002.

Stores competitor profiles, their digital presence, scraped content,
and NLP-extracted themes for competitive intelligence.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class CompetitorProfile(UUIDModel, TimeStampedModel, TenantModel):
    """A competitor profile with digital presence and SWOT data.

    Attributes:
        name: Competitor company name.
        website: Competitor website URL.
        social_profiles: JSON with platform handles, followers, URLs.
        scraping_config: JSON with frequency, sources, settings.
        last_scraped_at: Timestamp of last successful scrape.
        is_active: Whether this competitor is being tracked.
        swot_analysis: Auto-generated SWOT analysis JSON.
    """

    name = models.CharField(
        max_length=255,
        help_text="Competitor company name",
    )
    website = models.URLField(
        blank=True,
        help_text="Competitor website URL",
    )
    social_profiles = models.JSONField(
        default=dict,
        blank=True,
        help_text="Social presence: instagram, linkedin, twitter, tiktok, youtube handles and followers",
    )
    scraping_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Scraping config: frequency, sources, settings",
    )
    last_scraped_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last successful data scrape",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this competitor is actively tracked",
    )
    swot_analysis = models.JSONField(
        default=dict,
        blank=True,
        help_text="Auto-generated SWOT: strengths, weaknesses, opportunities, threats",
    )

    class Meta:
        db_table = "voyager_competitor_profile"
        verbose_name = "Competitor Profile"
        verbose_name_plural = "Competitor Profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "is_active"]),
            models.Index(fields=["tenant_id", "name"]),
            models.Index(fields=["tenant_id", "-last_scraped_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_competitor_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class CompetitorContent(UUIDModel, TimeStampedModel):
    """Scraped competitor content for NLP analysis.

    Stores individual content pieces (posts, articles, ads) discovered
    during competitor scraping, with engagement metrics and extracted topics.

    Attributes:
        competitor: The competitor who published this content.
        platform: Source platform (e.g. 'instagram', 'linkedin').
        content_type: Type of content (e.g. 'post', 'article', 'ad').
        text: The content text body.
        media_urls: Array of media URLs in the content.
        engagement_metrics: JSON with likes, shares, comments, reach.
        published_at: Original publication timestamp.
        topics: Extracted topic tags.
        sentiment: Sentiment score (-1.0 to 1.0).
    """

    competitor = models.ForeignKey(
        CompetitorProfile,
        on_delete=models.CASCADE,
        related_name="contents",
        help_text="The competitor who published this content",
    )
    platform = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Source platform (e.g. 'instagram', 'linkedin')",
    )
    content_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Content type (e.g. 'post', 'article', 'ad')",
    )
    text = models.TextField(
        blank=True,
        help_text="Content text body",
    )
    media_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of media URLs in the content",
    )
    engagement_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Engagement data: likes, shares, comments, reach",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Original publication timestamp",
    )
    topics = models.JSONField(
        default=list,
        blank=True,
        help_text="Extracted topic tags from NLP analysis",
    )
    sentiment = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sentiment score from -1.0 (negative) to 1.0 (positive)",
    )

    class Meta:
        db_table = "voyager_competitor_content"
        verbose_name = "Competitor Content"
        verbose_name_plural = "Competitor Contents"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["competitor", "platform"]),
            models.Index(fields=["competitor", "published_at"]),
            models.Index(fields=["competitor", "topics"]),
        ]

    def __str__(self) -> str:
        return f"{self.competitor.name} — {self.platform} ({self.content_type})"
