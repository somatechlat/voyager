"""On-page audit service.

Implements page crawling simulation, SEO issue detection,
scoring, and fix recommendation generation.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

from django.utils import timezone

from apps.seo.models.onpage import OnPageAudit

logger = logging.getLogger(__name__)

# Issue severity mapping
_SEVERITY_SCORES = {
    "critical": 15,
    "high": 10,
    "medium": 5,
    "low": 3,
}

# Generic anchor text patterns
_GENERIC_ANCHORS = {"click here", "read more", "learn more", "this link", "here"}


def count_words(text: str) -> int:
    """Count words in a text block.

    Args:
        text: Input text.

    Returns:
        Word count.
    """
    return len(re.findall(r"\b\w+\b", text))


def flesch_kincaid_score(text: str) -> float:
    """Calculate Flesch-Kincaid readability score.

    Args:
        text: Input text.

    Returns:
        Reading ease score (0-100, higher = easier).
    """
    words = count_words(text)
    if words == 0:
        return 0.0
    sentences = max(len(re.findall(r"[.!?]+", text)), 1)
    syllables = len(re.findall(r"[aeiouAEIOU]+", text))
    score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    return max(0.0, min(100.0, score))


def count_occurrences(text: str, keyword: str) -> int:
    """Count occurrences of a keyword in text (case-insensitive).

    Args:
        text: Text to search.
        keyword: Keyword to count.

    Returns:
        Number of occurrences.
    """
    return len(re.findall(rf"\b{re.escape(keyword.lower())}\b", text.lower()))


def validate_heading_hierarchy(headings: list[dict[str, Any]]) -> bool:
    """Check if heading hierarchy is valid.

    A valid hierarchy has no skipped levels (e.g., h1 -> h3).

    Args:
        headings: List of heading dicts with 'level' key.

    Returns:
        True if hierarchy is valid.
    """
    if not headings:
        return True
    levels = [h["level"] for h in headings if "level" in h]
    if not levels:
        return True
    prev = levels[0]
    for level in levels[1:]:
        if level > prev + 1:
            return False
        prev = level
    return True


def generate_fix_recommendation(issue: dict[str, Any]) -> dict[str, Any]:
    """Generate a fix recommendation for a detected issue.

    Args:
        issue: Issue dict with type and details.

    Returns:
        Recommendation dict with type, description, and priority.
    """
    issue_type = issue.get("type", "")
    recommendations: dict[str, dict[str, Any]] = {
        "missing_title": {
            "description": "Add a title tag between 30-60 characters.",
            "priority": "critical",
        },
        "title_too_short": {
            "description": "Expand the title to at least 30 characters.",
            "priority": "medium",
        },
        "title_too_long": {
            "description": "Shorten the title to 60 characters or less.",
            "priority": "low",
        },
        "title_missing_keyword": {
            "description": "Include the target keyword in the title tag.",
            "priority": "high",
        },
        "missing_meta_description": {
            "description": "Add a meta description between 120-160 characters.",
            "priority": "high",
        },
        "meta_desc_too_short": {
            "description": "Expand the meta description to at least 120 characters.",
            "priority": "low",
        },
        "meta_desc_too_long": {
            "description": "Shorten the meta description to 160 characters or less.",
            "priority": "low",
        },
        "missing_h1": {
            "description": "Add exactly one H1 tag.",
            "priority": "critical",
        },
        "multiple_h1": {
            "description": "Consolidate to a single H1 tag.",
            "priority": "medium",
        },
        "broken_heading_hierarchy": {
            "description": "Fix heading levels to avoid skipped levels.",
            "priority": "medium",
        },
        "missing_alt_text": {
            "description": "Add descriptive alt text to all images.",
            "priority": "medium",
        },
        "few_internal_links": {
            "description": "Add more internal links to related content.",
            "priority": "medium",
        },
        "thin_content": {
            "description": "Expand content to at least 1500 words.",
            "priority": "high",
        },
        "low_keyword_density": {
            "description": "Increase keyword usage naturally in the content.",
            "priority": "medium",
        },
        "keyword_stuffing": {
            "description": "Reduce keyword density below 3% for natural reading.",
            "priority": "high",
        },
        "low_readability": {
            "description": "Use shorter sentences and simpler vocabulary.",
            "priority": "medium",
        },
        "no_schema_markup": {
            "description": "Add relevant JSON-LD schema markup.",
            "priority": "medium",
        },
        "missing_canonical": {
            "description": "Add a canonical tag to prevent duplicate content.",
            "priority": "medium",
        },
        "canonical_mismatch": {
            "description": "Review canonical URL for correctness.",
            "priority": "low",
        },
        "missing_og_tags": {
            "description": "Add Open Graph meta tags for social sharing.",
            "priority": "low",
        },
    }
    return {
        "issue_type": issue_type,
        "description": recommendations.get(issue_type, {}).get(
            "description", f"Fix the {issue_type} issue."
        ),
        "priority": recommendations.get(issue_type, {}).get("priority", "medium"),
        "details": issue,
    }


def audit_page(
    tenant_id: str,
    url: str,
    title: str = "",
    meta_description: str = "",
    h1_tags: list[str] | None = None,
    headings: list[dict[str, Any]] | None = None,
    body_text: str = "",
    images: list[dict[str, Any]] | None = None,
    internal_links: int = 0,
    external_links: int = 0,
    canonical: str = "",
    og_tags: list[str] | None = None,
    schemas: list[dict[str, Any]] | None = None,
    target_keywords: list[str] | None = None,
) -> OnPageAudit:
    """Run a comprehensive on-page SEO audit.

    Args:
        tenant_id: Tenant scope identifier.
        url: The page URL.
        title: Page title tag content.
        meta_description: Meta description content.
        h1_tags: List of H1 tag contents.
        headings: List of heading dicts with level and text.
        body_text: Page body text content.
        images: List of image dicts with src and alt.
        internal_links: Count of internal links.
        external_links: Count of external links.
        canonical: Canonical URL.
        og_tags: List of Open Graph tag names.
        schemas: List of schema dicts.
        target_keywords: Keywords to check against.

    Returns:
        Created OnPageAudit instance.
    """
    h1_tags = h1_tags or []
    headings = headings or []
    images = images or []
    og_tags = og_tags or []
    schemas = schemas or []
    target_keywords = target_keywords or []

    score = 100.0
    issues: list[dict[str, Any]] = []

    # 1. Title tag analysis
    title_len = len(title)
    if not title:
        score -= _SEVERITY_SCORES["critical"]
        issues.append({"type": "missing_title", "severity": "critical"})
    else:
        if title_len < 30:
            score -= 5
            issues.append({"type": "title_too_short", "current": title_len, "recommended": "30-60"})
        if title_len > 60:
            score -= 3
            issues.append({"type": "title_too_long", "current": title_len, "recommended": "30-60"})
        if target_keywords and not any(kw.lower() in title.lower() for kw in target_keywords):
            score -= _SEVERITY_SCORES["high"]
            issues.append({"type": "title_missing_keyword", "severity": "high"})

    # 2. Meta description analysis
    desc_len = len(meta_description)
    if not meta_description:
        score -= _SEVERITY_SCORES["high"]
        issues.append({"type": "missing_meta_description", "severity": "high"})
    else:
        if desc_len < 120:
            score -= 3
            issues.append({"type": "meta_desc_too_short", "current": desc_len})
        if desc_len > 160:
            score -= 3
            issues.append({"type": "meta_desc_too_long", "current": desc_len})

    # 3. H1 tag analysis
    h1_count = len(h1_tags)
    if h1_count == 0:
        score -= 12
        issues.append({"type": "missing_h1", "severity": "critical"})
    elif h1_count > 1:
        score -= 5
        issues.append({"type": "multiple_h1", "count": h1_count})

    # 4. Heading hierarchy
    if not validate_heading_hierarchy(headings):
        score -= 5
        issues.append({"type": "broken_heading_hierarchy", "severity": "medium"})

    # 5. Image alt text
    images_without_alt = sum(1 for img in images if not img.get("alt"))
    if images_without_alt > 0:
        score -= min(images_without_alt * 2, 10)
        issues.append({"type": "missing_alt_text", "count": images_without_alt})

    # 6. Internal linking
    if internal_links < 3:
        score -= 5
        issues.append({"type": "few_internal_links", "count": internal_links, "recommended": "5+"})

    # 7. Content length
    word_count = count_words(body_text)
    if word_count < 300:
        score -= 10
        issues.append({"type": "thin_content", "word_count": word_count, "recommended": "1500+"})

    # 8. Keyword density
    keyword_density: dict[str, Any] = {}
    for kw in target_keywords:
        occurrences = count_occurrences(body_text, kw)
        density = (occurrences / max(word_count, 1)) * 100.0
        keyword_density[kw] = round(density, 2)
        if density < 0.5:
            score -= 3
            issues.append({"type": "low_keyword_density", "keyword": kw, "density": round(density, 2)})
        elif density > 3.0:
            score -= 5
            issues.append({"type": "keyword_stuffing", "keyword": kw, "density": round(density, 2)})

    # 9. Readability
    readability = flesch_kincaid_score(body_text)
    if readability < 30:
        score -= 5
        issues.append({"type": "low_readability", "score": round(readability, 2), "recommended": "60+"})

    # 10. Schema markup
    if not schemas:
        score -= 5
        issues.append({"type": "no_schema_markup", "severity": "medium"})

    # 11. Canonical
    if not canonical:
        score -= 3
        issues.append({"type": "missing_canonical"})

    # 12. Open Graph
    if not og_tags:
        score -= 2
        issues.append({"type": "missing_og_tags", "severity": "low"})

    # Generate recommendations
    recommendations = [generate_fix_recommendation(issue) for issue in issues]

    # Sort issues by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda i: severity_order.get(i.get("severity", "low"), 4))

    final_score = max(0.0, score)

    # Determine grade
    if final_score >= 90:
        grade = OnPageAudit.Grade.A
    elif final_score >= 75:
        grade = OnPageAudit.Grade.B
    elif final_score >= 60:
        grade = OnPageAudit.Grade.C
    elif final_score >= 45:
        grade = OnPageAudit.Grade.D
    else:
        grade = OnPageAudit.Grade.F

    audit = OnPageAudit.objects.create(
        tenant_id=tenant_id,
        url=url,
        target_keywords_json=target_keywords,
        score=round(final_score, 2),
        grade=grade,
        title=title,
        title_length=title_len,
        meta_description=meta_description,
        meta_description_length=desc_len,
        h1=h1_tags[0] if h1_tags else "",
        h1_count=h1_count,
        canonical=canonical,
        word_count=word_count,
        readability_score=round(readability, 2),
        keyword_density_json=keyword_density,
        internal_links=internal_links,
        external_links=external_links,
        images_total=len(images),
        images_with_alt=len(images) - images_without_alt,
        schema_count=len(schemas),
        schemas_json=schemas,
        issues_json=issues,
        recommendations_json=recommendations,
        og_tags_json={tag: True for tag in og_tags},
        headings_json=headings,
        audited_at=timezone.now(),
    )
    return audit
