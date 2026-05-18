"""Persona service — SP-001 business logic.

Handles persona CRUD, campaign linking, and persona aggregation
for campaign targeting.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.strategy.models import AudiencePersona, PersonaCampaignLink

logger = logging.getLogger(__name__)


class PersonaService:
    """Service for audience persona operations."""

    @staticmethod
    def create_persona(
        tenant_id: str,
        name: str,
        demographics: dict[str, Any],
        description: str = "",
        psychographics: dict[str, Any] | None = None,
        pain_points: list[str] | None = None,
        content_preferences: dict[str, Any] | None = None,
        channel_preferences: list[dict[str, Any]] | None = None,
        data_sources: list[dict[str, Any]] | None = None,
    ) -> AudiencePersona:
        """Create a new audience persona.

        Args:
            tenant_id: Tenant scope identifier.
            name: Persona name (3-100 chars).
            demographics: Required demographic data.
            description: Optional narrative description.
            psychographics: Optional psychographic data.
            pain_points: List of pain point strings.
            content_preferences: Content preference matrix.
            channel_preferences: Platform ranking array.
            data_sources: Derivation source descriptions.

        Returns:
            Created AudiencePersona instance.
        """
        if len(name) < 3 or len(name) > 100:
            raise ValueError("Name must be between 3 and 100 characters")
        pain_points = pain_points or []
        if len(pain_points) > 20:
            raise ValueError("Maximum 20 pain points allowed")

        persona = AudiencePersona.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            demographics=demographics,
            psychographics=psychographics or {},
            pain_points=pain_points[:20],
            content_preferences=content_preferences or {},
            channel_preferences=channel_preferences or [],
            data_sources=data_sources or [],
        )
        logger.info("Created persona %s for tenant %s", persona.id, tenant_id)
        return persona

    @staticmethod
    def update_persona(
        persona_id: str,
        tenant_id: str,
        **updates: Any,
    ) -> AudiencePersona:
        """Update an existing persona.

        Args:
            persona_id: UUID of the persona.
            tenant_id: Tenant scope for verification.
            **updates: Field updates.

        Returns:
            Updated AudiencePersona instance.

        Raises:
            AudiencePersona.DoesNotExist: If not found.
        """
        persona = AudiencePersona.objects.get(id=persona_id, tenant_id=tenant_id)
        if "pain_points" in updates:
            pps = updates["pain_points"]
            if len(pps) > 20:
                raise ValueError("Maximum 20 pain points allowed")
            updates["pain_points"] = pps[:20]
        for field, value in updates.items():
            if hasattr(persona, field):
                setattr(persona, field, value)
        persona.save()
        logger.info("Updated persona %s", persona.id)
        return persona

    @staticmethod
    def link_to_campaign(
        persona_id: str,
        campaign_id: str,
        weight: float = 0.5,
    ) -> PersonaCampaignLink:
        """Link a persona to a campaign with weight.

        Args:
            persona_id: UUID of the persona.
            campaign_id: UUID of the campaign.
            weight: Influence weight 0.0-1.0.

        Returns:
            Created or updated PersonaCampaignLink.
        """
        weight = max(0.0, min(1.0, float(weight)))
        link, created = PersonaCampaignLink.objects.update_or_create(
            persona_id=persona_id,
            campaign_id=campaign_id,
            defaults={"weight": weight},
        )
        action = "Created" if created else "Updated"
        logger.info("%s persona-campaign link: %s → %s", action, persona_id, campaign_id)
        return link

    @staticmethod
    def get_personas_for_campaign(campaign_id: str) -> list[dict[str, Any]]:
        """Get all personas linked to a campaign with weights.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            List of persona dicts with weight and name.
        """
        links = (
            PersonaCampaignLink.objects.filter(
                campaign_id=campaign_id,
            )
            .select_related("persona")
            .order_by("-weight")
        )
        return [
            {
                "persona_id": str(link.persona.id),
                "name": link.persona.name,
                "weight": float(link.weight),
                "demographics_summary": _summarize_demographics(link.persona.demographics),
            }
            for link in links
        ]

    @staticmethod
    def aggregate_targeting(persona_ids: list[str]) -> dict[str, Any]:
        """Aggregate demographic targeting from multiple personas.

        Args:
            persona_ids: List of persona UUIDs.

        Returns:
            Aggregated targeting profile.
        """
        personas = AudiencePersona.objects.filter(
            id__in=persona_ids,
            is_active=True,
        )
        if not personas:
            return {}

        all_genders: set[str] = set()
        all_languages: set[str] = set()
        age_mins: list[int] = []
        age_maxs: list[int] = []
        locations: list[dict[str, Any]] = []

        for p in personas:
            demo = p.demographics or {}
            age_range = demo.get("ageRange", {})
            if age_range.get("min"):
                age_mins.append(int(age_range["min"]))
            if age_range.get("max"):
                age_maxs.append(int(age_range["max"]))
            for g in demo.get("gender", []):
                all_genders.add(g)
            for l in demo.get("languages", []):
                all_languages.add(l)
            for loc in demo.get("locations", []):
                locations.append(loc)

        return {
            "age_range": {
                "min": min(age_mins) if age_mins else None,
                "max": max(age_maxs) if age_maxs else None,
            },
            "gender": sorted(all_genders),
            "languages": sorted(all_languages),
            "locations": locations[:5],
            "persona_count": personas.count(),
        }


def _summarize_demographics(demographics: dict[str, Any]) -> str:
    """Create a short summary string from demographics."""
    demo = demographics or {}
    age = demo.get("ageRange", {})
    age_str = f"{age.get('min', '?')}-{age.get('max', '?')}"
    genders = ", ".join(demo.get("gender", [])) or "any"
    return f"Age {age_str}, {genders}"
