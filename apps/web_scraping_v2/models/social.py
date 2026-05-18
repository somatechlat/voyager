"""SocialMention model — collected mentions with deduplication."""

from __future__ import annotations

import uuid

from django.db import models


class SocialMention(models.Model):
    """A brand/product/keyword mention from a social platform.

    Deduplicated via content fingerprint. Cross-posts are tracked
    across multiple platforms for the same content.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        brand: Brand or keyword that was mentioned.
        platform: Social platform name (e.g., twitter, reddit).
        author: Username or handle of the mention author.
        text: Full text content of the mention.
        url: Direct URL to the mention.
        fingerprint: SHA-256 hash for deduplication.
        sentiment: Sentiment label from analysis.
        sentiment_score: Numeric sentiment score.
        engagement: JSON with likes, shares, comments, reach.
        cross_platforms: Array of platforms where the same content appeared.
        published_at: Original publication time on the platform.
        collected_at: When the mention was ingested.
    """

    class SentimentLabel(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"
        NEUTRAL = "neutral", "Neutral"
        MIXED = "mixed", "Mixed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    brand = models.CharField(max_length=255, db_index=True)
    platform = models.CharField(max_length=50, db_index=True)
    author = models.CharField(max_length=255, blank=True, default="")
    text = models.TextField()
    url = models.URLField(max_length=2048, blank=True, default="")
    fingerprint = models.CharField(max_length=64, db_index=True)
    sentiment = models.CharField(
        max_length=20,
        choices=SentimentLabel.choices,
        blank=True,
        default="",
        db_index=True,
    )
    sentiment_score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    engagement = models.JSONField(default=dict, blank=True)
    cross_platforms = models.JSONField(default=list, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    collected_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ws_social_mentions"
        indexes = [
            models.Index(fields=["tenant_id", "collected_at"]),
            models.Index(fields=["brand", "collected_at"]),
            models.Index(fields=["sentiment"]),
            models.Index(fields=["fingerprint"]),
        ]
        ordering = ["-collected_at"]

    def __str__(self) -> str:
        text_preview = self.text[:50] if self.text else ""
        return f"Mention({self.platform}, {self.brand}, {text_preview}...)"
