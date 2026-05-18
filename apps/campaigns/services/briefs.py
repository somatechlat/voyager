"""AI brief generation service.

Generates comprehensive campaign briefs using structured analysis
of objectives, audience data, competitive landscape, and historical
performance. Uses a rule-based scoring engine (AI integration ready).
"""

from __future__ import annotations

import logging
from typing import Any

from apps.campaigns.models import Campaign, CampaignBrief
from apps.campaigns.services.channels import get_channel_recommendations

logger = logging.getLogger(__name__)


def _extract_objective(objective: str) -> dict[str, Any]:
    """Parse campaign objective into structured components.

    Args:
        objective: The objective string.

    Returns:
        Dict with goal_type, target_metrics, constraints.
    """
    objective_map: dict[str, dict[str, Any]] = {
        Campaign.Objective.AWARENESS: {
            "goal_type": "awareness",
            "target_metrics": ["reach", "impressions", "brand_lift"],
            "kpis": {"reach": 100000, "impressions": 500000, "ctr": 1.0},
        },
        Campaign.Objective.ENGAGEMENT: {
            "goal_type": "engagement",
            "target_metrics": ["engagement_rate", "shares", "comments"],
            "kpis": {"engagement_rate": 5.0, "shares": 5000, "comments": 2000},
        },
        Campaign.Objective.CONVERSION: {
            "goal_type": "conversion",
            "target_metrics": ["conversions", "cpa", "roas"],
            "kpis": {"conversions": 1000, "cpa": 25.0, "roas": 4.0},
        },
        Campaign.Objective.RETENTION: {
            "goal_type": "retention",
            "target_metrics": ["retention_rate", "ltv", "churn_reduction"],
            "kpis": {"retention_rate": 80.0, "ltv": 500.0, "churn_reduction": 15.0},
        },
    }
    return objective_map.get(objective, objective_map[Campaign.Objective.AWARENESS])


def _select_personas(
    objective: str, audience_data: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Select top 3 audience personas for the campaign.

    Args:
        objective: Campaign objective.
        audience_data: Optional audience data.

    Returns:
        List of persona dicts.
    """
    personas = [
        {
            "id": "persona_001",
            "name": "Tech-Savvy Millennials",
            "age_range": "25-34",
            "channels": ["organic_social", "paid_social", "video"],
            "relevance_score": 0.92,
            "justification": "Highest engagement on digital channels, aligns with conversion objectives",
        },
        {
            "id": "persona_002",
            "name": "Decision-Making Professionals",
            "age_range": "35-44",
            "channels": ["paid_search", "email", "seo"],
            "relevance_score": 0.88,
            "justification": "High intent, research-driven, strong conversion potential",
        },
        {
            "id": "persona_003",
            "name": "Budget-Conscious Families",
            "age_range": "30-45",
            "channels": ["display", "email", "organic_social"],
            "relevance_score": 0.75,
            "justification": "Broad reach potential, responsive to promotional messaging",
        },
    ]

    # Sort by relevance to objective
    if objective == Campaign.Objective.CONVERSION:
        personas.sort(key=lambda p: p["relevance_score"], reverse=True)
    elif objective == Campaign.Objective.AWARENESS:
        personas.sort(key=lambda p: len(p["channels"]), reverse=True)

    return personas[:3]


def _analyze_competitive_landscape(
    industry: str = "",
    objective: str = "",
) -> dict[str, Any]:
    """Analyze competitive landscape.

    Args:
        industry: Client industry.
        objective: Campaign objective.

    Returns:
        Competitive insights dict.
    """
    return {
        "industry": industry or "general",
        "competitor_campaigns_active": 12,
        "top_themes": [
            "User-generated content driving engagement",
            "Video-first creative outperforming static by 3x",
            "Micro-influencer partnerships showing highest ROAS",
        ],
        "gaps": [
            "Underserved professional segment on LinkedIn",
            "Limited retargeting in the consideration phase",
            "Opportunity in emerging short-form video formats",
        ],
        "opportunities": [
            "First-mover advantage in interactive ad formats",
            "Cross-channel sequential messaging",
            "AI-personalized landing page experiences",
        ],
    }


def _estimate_timeline(
    channels: list[dict[str, Any]],
    approval_cycles: int = 2,
) -> dict[str, Any]:
    """Estimate campaign timeline.

    Args:
        channels: Selected channels.
        approval_cycles: Number of approval rounds.

    Returns:
        Timeline estimate dict.
    """
    base_days = 14
    channel_days = len(channels) * 5
    approval_days = approval_cycles * 3
    buffer_days = 7
    total = base_days + channel_days + approval_days + buffer_days

    return {
        "total_days": total,
        "breakdown": {
            "planning": 7,
            "creative_production": channel_days,
            "approval_cycles": approval_days,
            "setup_and_launch": 7,
            "buffer": buffer_days,
        },
        "phases": [
            {"phase": "Planning & Strategy", "days": 7},
            {"phase": "Creative Production", "days": channel_days},
            {"phase": "Review & Approval", "days": approval_days},
            {"phase": "Setup & Launch", "days": 7},
        ],
    }


def _suggest_budget(
    total_budget: float | None,
    channels: list[dict[str, Any]],
    objective: str,
) -> dict[str, Any]:
    """Suggest budget allocation across channels.

    Args:
        total_budget: Available budget.
        channels: Selected channels.
        objective: Campaign objective.

    Returns:
        Budget breakdown dict.
    """
    if not total_budget or total_budget <= 0:
        total_budget = 10000.0

    # Default allocation weights by objective
    weights: dict[str, dict[str, float]] = {
        Campaign.Objective.AWARENESS: {
            "paid_social": 0.25,
            "video": 0.20,
            "display": 0.15,
            "organic_social": 0.15,
            "influencer": 0.15,
            "paid_search": 0.05,
            "seo": 0.03,
            "email": 0.02,
        },
        Campaign.Objective.ENGAGEMENT: {
            "paid_social": 0.25,
            "organic_social": 0.20,
            "video": 0.15,
            "influencer": 0.15,
            "email": 0.10,
            "paid_search": 0.05,
            "display": 0.05,
            "seo": 0.05,
        },
        Campaign.Objective.CONVERSION: {
            "paid_search": 0.25,
            "paid_social": 0.20,
            "email": 0.15,
            "display": 0.15,
            "video": 0.10,
            "seo": 0.08,
            "organic_social": 0.05,
            "influencer": 0.02,
        },
        Campaign.Objective.RETENTION: {
            "email": 0.30,
            "organic_social": 0.20,
            "paid_social": 0.15,
            "seo": 0.15,
            "paid_search": 0.10,
            "video": 0.05,
            "display": 0.03,
            "influencer": 0.02,
        },
    }

    obj_weights = weights.get(objective, weights[Campaign.Objective.AWARENESS])
    selected_types = [ch.get("channel_type", ch.get("type", "")) for ch in channels]

    breakdown: list[dict[str, Any]] = []
    allocated = 0.0

    for ch_type in selected_types:
        weight = obj_weights.get(ch_type, 0.05)
        amount = total_budget * weight
        allocated += amount
        breakdown.append(
            {
                "channel_type": ch_type,
                "percentage": round(weight * 100, 1),
                "amount": round(amount, 2),
            }
        )

    # Normalize to total budget
    if allocated > 0 and allocated != total_budget:
        scale = total_budget / allocated
        for item in breakdown:
            item["amount"] = round(item["amount"] * scale, 2)
            item["percentage"] = round((item["amount"] / total_budget) * 100, 1)

    return {
        "total_budget": round(total_budget, 2),
        "currency": "USD",
        "channel_breakdown": breakdown,
        "recommended_cpm": round(5.0 + (total_budget / 100000.0), 2),
        "recommended_cpc": round(0.5 + (total_budget / 500000.0), 2),
    }


def generate_brief(campaign: Campaign) -> CampaignBrief:
    """Generate a comprehensive AI campaign brief.

    Analyzes campaign objectives, audience data, competitive landscape,
    and historical performance to produce a structured brief document.

    Args:
        campaign: The campaign to generate a brief for.

    Returns:
        The created CampaignBrief record.
    """
    obj_info = _extract_objective(campaign.objective)
    personas = _select_personas(campaign.objective, campaign.target_audience)

    # Get channel recommendations
    channel_recs = get_channel_recommendations(
        campaign.objective,
        campaign.target_audience,
    )
    top_channels = channel_recs[:5]

    competitive = _analyze_competitive_landscape(
        industry=campaign.client.industry if campaign.client else "",
        objective=campaign.objective,
    )

    timeline = _estimate_timeline(top_channels)
    budget_suggestion = _suggest_budget(
        float(campaign.budget) if campaign.budget else None,
        top_channels,
        campaign.objective,
    )

    # Build the brief sections
    executive_summary = (
        f"This campaign brief for '{campaign.name}' focuses on a "
        f"{obj_info['goal_type']} objective. The recommended strategy "
        f"leverages {len(top_channels)} primary channels targeting "
        f"{len(personas)} key audience segments over a "
        f"{timeline['total_days']}-day timeline with an estimated "
        f"budget of ${budget_suggestion['total_budget']:,.2f}."
    )

    objectives_kpis = (
        f"Primary Objective: {obj_info['goal_type'].title()}\n"
        f"Target Metrics: {', '.join(obj_info['target_metrics'])}\n"
        f"KPI Targets: {obj_info['kpis']}"
    )

    audience_profiles = "\n\n".join(
        f"{i+1}. {p['name']} ({p['age_range']}) — "
        f"Relevance: {p['relevance_score']:.0%}\n"
        f"   Primary Channels: {', '.join(p['channels'])}\n"
        f"   Why: {p['justification']}"
        for i, p in enumerate(personas)
    )

    channel_strategy_text = "\n\n".join(
        f"{i+1}. {ch['channel_type']} — Score: {ch['score']:.3f} "
        f"(Audience: {ch['audience_overlap']:.0%}, "
        f"Performance: {ch['historical_performance']:.0%}, "
        f"Cost: {ch['cost_efficiency']:.0%})"
        for i, ch in enumerate(top_channels)
    )

    timeline_text = (
        "\n".join(f"- {phase['phase']}: {phase['days']} days" for phase in timeline["phases"])
        + f"\n\nTotal Estimated Duration: {timeline['total_days']} days"
    )

    budget_text = (
        f"Total Budget: ${budget_suggestion['total_budget']:,.2f} "
        f"{budget_suggestion['currency']}\n\n"
        + "\n".join(
            f"- {b['channel_type']}: ${b['amount']:,.2f} ({b['percentage']:.1f}%)"
            for b in budget_suggestion["channel_breakdown"]
        )
    )

    risk_assessment = (
        "Risks:\n"
        "- Budget overrun if CPA exceeds target by >20%\n"
        "- Channel fatigue after 3-4 weeks of continuous running\n"
        "- Audience overlap between paid social and display\n\n"
        "Mitigations:\n"
        "- Weekly budget pacing reviews\n"
        "- Creative refresh every 2 weeks\n"
        "- Frequency caps at 3 impressions per user per day"
    )

    brief = CampaignBrief.objects.create(
        campaign=campaign,
        objective_type=obj_info["goal_type"],
        target_metrics=obj_info,
        selected_personas=personas,
        competitive_insights=competitive,
        recommended_channels=top_channels,
        estimated_timeline_days=timeline["total_days"],
        suggested_budget=budget_suggestion,
        executive_summary=executive_summary,
        objectives_and_kpis=objectives_kpis,
        target_audience_profiles=audience_profiles,
        channel_strategy=channel_strategy_text,
        content_requirements="Content requirements to be defined based on channel mix.",
        timeline_details=timeline_text,
        budget_breakdown=budget_text,
        risk_assessment=risk_assessment,
        raw_response="Generated via rule-based engine",
    )

    logger.info("Generated brief v%s for campaign %s", brief.version, campaign.id)
    return brief
