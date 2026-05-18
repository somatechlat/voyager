"""Market Research model — SP-006.

Aggregates trend data, market size estimates, audience insights,
and competitive landscape analysis.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class MarketResearch(UUIDModel, TimeStampedModel, TenantModel):
    """Market research snapshot with trends, sizing, and competitive landscape.

    Attributes:
        industry: Industry or vertical researched.
        trends: JSON array of detected trends with scores and lifecycle stage.
        market_size: JSON with TAM, SAM, SOM estimates and sources.
        audience_insights: JSON with audience behavior and preference findings.
        competitive_landscape: JSON with competitor positioning data.
        research_date: Date the research was conducted.
    """

    industry = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Industry or vertical researched",
    )
    trends = models.JSONField(
        default=list,
        blank=True,
        help_text="Detected trends: name, velocity, acceleration, volume, trendScore, stage",
    )
    market_size = models.JSONField(
        default=dict,
        blank=True,
        help_text="Market sizing: TAM, SAM, SOM with values and sources",
    )
    audience_insights = models.JSONField(
        default=dict,
        blank=True,
        help_text="Audience insights: behaviors, preferences, segments",
    )
    competitive_landscape = models.JSONField(
        default=dict,
        blank=True,
        help_text="Competitive landscape: positioning, market share, gaps",
    )
    research_date = models.DateField(
        db_index=True,
        help_text="Date the research was conducted",
    )

    class Meta:
        db_table = "voyager_market_research"
        verbose_name = "Market Research"
        verbose_name_plural = "Market Research Entries"
        ordering = ["-research_date"]
        indexes = [
            models.Index(fields=["tenant_id", "industry"]),
            models.Index(fields=["tenant_id", "-research_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.industry} — {self.research_date}"
