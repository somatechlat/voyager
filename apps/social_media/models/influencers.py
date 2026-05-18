"""Influencer profile model.

Stores discovered influencer profiles with vetting data,
audience demographics, authenticity scoring, and outreach tracking.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class InfluencerProfile(UUIDModel, TenantModel, TimeStampedModel):
    """An influencer profile discovered and vetted across platforms.

    Attributes:
        platform: Primary platform.
        platform_user_id: Native user ID.
        name: Display name.
        avatar: Profile image URL.
        bio: Bio text.
        followers: Follower count.
        following: Following count.
        engagement_rate: Engagement rate (0-1.0).
        niche: List of niche/category tags.
        location: Geographic location.
        audience_demographics: JSON with audience breakdown.
        authenticity_score: Authenticity score (0-100).
        red_flags: JSON list of detected authenticity concerns.
        rate_estimate: Estimated cost per post in USD.
        content_quality_score: Content quality score (0-100).
        status: Pipeline status.
        outreach_status: Outreach tracking status.
        outreach_sent_at: When outreach was sent.
        responded_at: When influencer responded.
        notes: Internal notes.
        match_score: Composite match score (0-100).
        contact_email: Contact email if available.
        website: Website URL.
    """

    STATUSES = [
        ("discovered", "Discovered"),
        ("vetting", "Vetting"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("contacted", "Contacted"),
        ("negotiating", "Negotiating"),
        ("contracted", "Contracted"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    OUTREACH_STATUSES = [
        ("not_contacted", "Not Contacted"),
        ("email_sent", "Email Sent"),
        ("dm_sent", "DM Sent"),
        ("responded", "Responded"),
        ("no_response", "No Response"),
        ("interested", "Interested"),
        ("not_interested", "Not Interested"),
        ("follow_up", "Follow Up Needed"),
    ]

    PLATFORMS = [
        ("instagram", "Instagram"),
        ("linkedin", "LinkedIn"),
        ("twitter", "Twitter / X"),
        ("tiktok", "TikTok"),
        ("youtube", "YouTube"),
        ("pinterest", "Pinterest"),
    ]

    platform = models.CharField(max_length=50, choices=PLATFORMS, db_index=True)
    platform_user_id = models.CharField(max_length=255, blank=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, db_index=True)
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    niche = models.JSONField(default=list, blank=True)
    location = models.CharField(max_length=255, blank=True)
    audience_demographics = models.JSONField(default=dict, blank=True)
    authenticity_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    red_flags = models.JSONField(default=list, blank=True)
    rate_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    content_quality_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUSES, default="discovered", db_index=True)
    outreach_status = models.CharField(
        max_length=20, choices=OUTREACH_STATUSES, default="not_contacted", db_index=True
    )
    outreach_sent_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    match_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, db_index=True
    )
    contact_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        db_table = "sm_influencer_profiles"
        ordering = ["-match_score", "-engagement_rate"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "outreach_status"]),
            models.Index(fields=["tenant_id", "platform", "niche"]),
            models.Index(fields=["tenant_id", "authenticity_score"]),
            models.Index(fields=["tenant_id", "match_score"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.platform}) — {self.status}"
