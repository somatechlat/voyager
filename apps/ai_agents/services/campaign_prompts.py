"""Campaign prompt builders for the creative agent.

Constructs detailed LLM prompts for campaign briefs, marketing content,
social media posts, and email copy from research data.
"""

from __future__ import annotations

from typing import Any


def build_creative_context(research: dict[str, Any]) -> dict[str, Any]:
    """Build creative context dict from research data."""
    competitors = research.get("competitors", {})
    trends = research.get("trends", {})
    audience = research.get("audience", {})
    keywords = research.get("keywords", {})

    context: dict[str, Any] = {}

    if isinstance(competitors, dict) and "error" not in competitors:
        context["competitors"] = competitors.get("landscape", {})
        context["positioning_gaps"] = competitors.get("gaps", [])

    if isinstance(trends, dict) and "error" not in trends:
        context["market_trends"] = trends.get("trends", [])
        context["emerging_topics"] = trends.get("emerging_topics", [])

    if isinstance(audience, dict) and "error" not in audience:
        context["personas"] = audience.get("personas", [])
        context["audience_preferences"] = audience.get("preferences", {})

    if isinstance(keywords, dict) and "error" not in keywords:
        context["keywords"] = keywords.get("keywords", [])

    return context


def build_brief_prompt(campaign_id: str, research: dict[str, Any]) -> str:
    """Build the prompt for campaign brief generation."""
    parts = [
        f"Create a comprehensive marketing campaign brief for campaign "
        f"'{campaign_id}'.",
        "",
        "Use the following research data to inform the brief:",
    ]

    competitors = research.get("competitors", {})
    if isinstance(competitors, dict) and "error" not in competitors:
        parts.append(f"\nCompetitive Landscape:\n{competitors}")

    trends = research.get("trends", {})
    if isinstance(trends, dict) and "error" not in trends:
        parts.append(f"\nMarket Trends:\n{trends}")

    audience = research.get("audience", {})
    if isinstance(audience, dict) and "error" not in audience:
        parts.append(f"\nAudience Insights:\n{audience}")

    parts.append("\nThe brief should include:")
    parts.append("1. Campaign objective and KPIs")
    parts.append("2. Target audience segments")
    parts.append("3. Key messaging pillars")
    parts.append("4. Channel strategy")
    parts.append("5. Content themes and angles")
    parts.append("6. Budget allocation recommendations")
    parts.append("7. Timeline and milestones")
    parts.append("8. Success metrics")

    return "\n".join(parts)


def build_content_prompt(
    campaign_id: str,
    brief: dict[str, Any],
    research: dict[str, Any],
) -> str:
    """Build the prompt for main marketing content generation."""
    brief_text = brief.get("text", "") if isinstance(brief, dict) else ""
    keywords = research.get("keywords", {})
    keyword_list = (
        keywords.get("keywords", []) if isinstance(keywords, dict) else []
    )

    parts = [
        f"Generate marketing content for campaign '{campaign_id}'.",
        "",
        f"Campaign Brief:\n{brief_text}",
        "",
        "Generate the following content assets:",
        "1. A compelling hero headline (max 60 characters)",
        "2. A primary body copy paragraph (100-150 words)",
        "3. Two call-to-action variations",
        "4. A meta description (max 160 characters)",
        "5. Three ad copy variations for different channels",
        "",
    ]
    if keyword_list:
        parts.append(
            f"Incorporate these keywords naturally: {keyword_list[:20]}"
        )

    return "\n".join(parts)


def build_social_prompt(
    campaign_id: str,
    brief: dict[str, Any],
    research: dict[str, Any],
) -> str:
    """Build the prompt for social media content generation."""
    brief_text = brief.get("text", "") if isinstance(brief, dict) else ""
    audience = research.get("audience", {})
    personas = (
        audience.get("personas", []) if isinstance(audience, dict) else []
    )

    parts = [
        f"Generate social media content for campaign '{campaign_id}'.",
        "",
        f"Brief:\n{brief_text}",
        "",
        "Create posts for each platform:",
        "1. LinkedIn — professional tone, industry insights, 150-200 words",
        "2. Twitter/X — concise, engaging, 280 chars max, include hashtags",
        (
            "3. Instagram — visual-first caption, 125-150 words, "
            "emojis okay"
        ),
        "4. Facebook — conversational, community-focused, 100-150 words",
        "",
        "For each post include:",
        "- The post text",
        "- 3-5 relevant hashtags",
        "- Best posting time recommendation",
        "- Engagement hook type",
    ]
    if personas:
        parts.append(f"\nAudience Personas: {personas}")

    return "\n".join(parts)


def build_email_prompt(
    campaign_id: str,
    brief: dict[str, Any],
    research: dict[str, Any],
) -> str:
    """Build the prompt for email marketing copy generation."""
    brief_text = brief.get("text", "") if isinstance(brief, dict) else ""
    audience = research.get("audience", {})
    preferences = (
        audience.get("preferences", {})
        if isinstance(audience, dict)
        else {}
    )

    parts = [
        f"Generate email marketing copy for campaign '{campaign_id}'.",
        "",
        f"Brief:\n{brief_text}",
        "",
        "Create the following email assets:",
        "1. Subject line — 5 variations (40-50 chars each), A/B test ready",
        "2. Preheader text — 5 variations (80-100 chars each)",
        "3. Email body — professional HTML-ready copy, 200-300 words",
        "4. CTA button text — 3 variations",
        "5. Postscript (P.S.) — 2 variations",
        "",
        "Best practices to follow:",
        "- Use power words and urgency triggers sparingly",
        "- Personalize with {{first_name}} placeholders",
        "- Keep paragraphs to 2-3 sentences",
        "- Include one clear primary CTA",
    ]
    if preferences:
        parts.append(f"\nAudience Preferences: {preferences}")

    return "\n".join(parts)
