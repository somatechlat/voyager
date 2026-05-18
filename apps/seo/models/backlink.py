"""Backlink model.

Defines Backlink for backlink profile storage with quality scoring,
anchor text analysis, and toxic link detection.
"""

from __future__ import annotations

import uuid

from django.db import models


class Backlink(models.Model):
    """A backlink with quality metrics and toxicity detection.

    Stores source/target URLs, anchor text, domain authority,
    spam score, and toxicity assessment for backlink analysis.
    """

    class LinkType(models.TextChoices):
        """Type of link relationship."""

        DOFOLLOW = "dofollow", "Dofollow"
        NOFOLLOW = "nofollow", "Nofollow"
        UGC = "ugc", "UGC"
        SPONSORED = "sponsored", "Sponsored"

    class Status(models.TextChoices):
        """Lifecycle status of the backlink."""

        ACTIVE = "active", "Active"
        LOST = "lost", "Lost"
        NEW = "new", "New"
        DISAVOWED = "disavowed", "Disavowed"

    class Action(models.TextChoices):
        """Recommended action for toxic links."""

        NONE = "none", "No Action"
        REVIEW = "review", "Review"
        DISAVOW = "disavow", "Disavow"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    source_url = models.URLField(max_length=2048, help_text="URL of the linking page")
    target_url = models.URLField(max_length=2048, help_text="URL of the linked page")
    anchor_text = models.TextField(blank=True, help_text="Link anchor text")
    referring_domain = models.CharField(
        max_length=255, db_index=True, blank=True, help_text="Domain of the linking page"
    )

    # Authority scores
    domain_authority = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    page_authority = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    spam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Spam score 0-100",
    )

    # Toxicity
    is_toxic = models.BooleanField(default=False, db_index=True)
    toxicity_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0, help_text="Toxicity score 0-100"
    )
    toxicity_reasons_json = models.JSONField(
        default=list, blank=True, help_text="Reasons for toxicity flag"
    )
    recommended_action = models.CharField(
        max_length=16, choices=Action.choices, default=Action.NONE
    )

    # Link properties
    link_type = models.CharField(max_length=16, choices=LinkType.choices, default=LinkType.DOFOLLOW)
    is_sitewide = models.BooleanField(default=False, help_text="Whether this is a site-wide link")
    source_outbound_links = models.PositiveIntegerField(
        default=0, help_text="Total outbound links from source page"
    )
    source_language = models.CharField(max_length=10, blank=True)

    # Status tracking
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    first_seen = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_backlink"
        verbose_name = "Backlink"
        verbose_name_plural = "Backlinks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "referring_domain"]),
            models.Index(fields=["tenant_id", "is_toxic"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "link_type"]),
            models.Index(fields=["target_url", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.referring_domain} -> {self.target_url} [{self.link_type}]"
