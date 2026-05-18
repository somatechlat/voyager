"""Audience Persona models — SP-001.

Stores detailed audience personas with demographic, psychographic,
behavioral, and preference data. Personas link to campaigns for
targeted strategy execution.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class AudiencePersona(UUIDModel, TimeStampedModel, TenantModel):
    """A detailed audience persona for targeting and content strategy.

    Attributes:
        name: Persona name (e.g. "Marketing Mary").
        description: Detailed persona narrative.
        demographics: JSON with age, gender, location, income, education, etc.
        psychographics: JSON with values, interests, lifestyle, personality.
        pain_points: Array of pain point strings.
        content_preferences: JSON with format preferences, topics, tone.
        channel_preferences: JSON array of platform rankings with metrics.
        data_sources: JSON describing how this persona was derived.
        is_active: Whether the persona is currently usable.
    """

    name = models.CharField(
        max_length=255,
        help_text="Persona name (e.g. 'Marketing Mary')",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed persona narrative and background",
    )
    demographics = models.JSONField(
        default=dict,
        help_text="Demographic data: ageRange, gender, locations, incomeRange, education, occupation, familyStatus, languages",
    )
    psychographics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Psychographic data: values, interests, lifestyle, personality, motivations, frustrations",
    )
    pain_points = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of pain point strings (max 20)",
    )
    content_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Content preference matrix: formats, topics, tonePreference, contentLength, visualPreference",
    )
    channel_preferences = models.JSONField(
        default=list,
        blank=True,
        help_text="Channel ranking array with platform, rank, engagementRate, timeSpent",
    )
    data_sources = models.JSONField(
        default=list,
        blank=True,
        help_text="Sources used to derive this persona: surveys, analytics, interviews, etc.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the persona is currently active",
    )

    class Meta:
        db_table = "voyager_audience_persona"
        verbose_name = "Audience Persona"
        verbose_name_plural = "Audience Personas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "is_active"]),
            models.Index(fields=["tenant_id", "name"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_persona_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class PersonaCampaignLink(UUIDModel, TimeStampedModel):
    """Links a persona to a campaign with a weight factor.

    The weight determines how much the persona influences campaign
    strategy: 0.0 = reference only, 1.0 = primary target.

    Attributes:
        persona: The linked persona.
        campaign_id: UUID of the linked campaign.
        weight: Influence weight from 0.0 to 1.0.
    """

    persona = models.ForeignKey(
        AudiencePersona,
        on_delete=models.CASCADE,
        related_name="campaign_links",
        help_text="The linked persona",
    )
    campaign_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the linked campaign",
    )
    weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.5,
        help_text="Influence weight: 0.0 = reference, 1.0 = primary target",
    )

    class Meta:
        db_table = "voyager_persona_campaign_link"
        verbose_name = "Persona Campaign Link"
        verbose_name_plural = "Persona Campaign Links"
        unique_together = [["persona", "campaign_id"]]
        indexes = [
            models.Index(fields=["campaign_id", "weight"]),
            models.Index(fields=["persona", "weight"]),
        ]

    def __str__(self) -> str:
        return f"{self.persona.name} → campaign {self.campaign_id} (w={self.weight})"
