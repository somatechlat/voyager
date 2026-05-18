"""Backlink analysis service.

Implements backlink profile analysis, quality scoring,
anchor text distribution, and toxic link detection.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from apps.seo.models.backlink import Backlink

logger = logging.getLogger(__name__)

# Generic anchor text patterns indicating low quality
_GENERIC_ANCHORS = {
    "click here",
    "read more",
    "learn more",
    "this link",
    "here",
    "website",
    "link",
    "more info",
    "more information",
    "check this out",
}

# Known penalized TLDs
_PENALIZED_TLDS = {".tk", ".ml", ".ga", ".cf", ".top", ".xyz"}


def is_generic_anchor(anchor_text: str) -> bool:
    """Check if anchor text is generic/low quality.

    Args:
        anchor_text: The anchor text to evaluate.

    Returns:
        True if the anchor is generic.
    """
    return anchor_text.lower().strip() in _GENERIC_ANCHORS


def is_penalized_tld(domain: str) -> bool:
    """Check if domain uses a known penalized TLD.

    Args:
        domain: The domain to check.

    Returns:
        True if the TLD is in the penalized list.
    """
    domain_lower = domain.lower()
    return any(domain_lower.endswith(tld) for tld in _PENALIZED_TLDS)


def calculate_toxicity_score(backlink: Backlink, all_backlinks: list[Backlink]) -> dict[str, Any]:
    """Calculate toxicity score for a single backlink.

    Evaluates spam score, anchor quality, penalized domains,
    outbound link ratio, sitewide status, and exact match overuse.

    Args:
        backlink: The backlink to evaluate.
        all_backlinks: Full backlink list for context.

    Returns:
        Dict with score, reasons, and recommended action.
    """
    score = 0
    reasons: list[str] = []

    # 1. Spam score of referring domain
    if backlink.spam_score and float(backlink.spam_score) > 70:
        score += 30
        reasons.append("High spam score on referring domain")

    # 2. Generic anchor text
    if is_generic_anchor(backlink.anchor_text):
        score += 10
        reasons.append("Generic anchor text")

    # 3. Penalized domain TLD
    if is_penalized_tld(backlink.referring_domain):
        score += 40
        reasons.append("Link from penalized domain TLD")

    # 4. Excessive outbound links from source page
    if backlink.source_outbound_links and backlink.source_outbound_links > 100:
        score += 15
        reasons.append("Excessive outbound links from source page")

    # 5. Sitewide links
    if backlink.is_sitewide:
        score += 15
        reasons.append("Sitewide link detected")

    # 6. Foreign language mismatch
    if backlink.source_language and backlink.source_language != "en":
        score += 10
        reasons.append("Language mismatch")

    # 7. Exact match anchor text overuse
    domain_exact_count = sum(
        1
        for bl in all_backlinks
        if bl.referring_domain == backlink.referring_domain
        and bl.anchor_text.lower() == backlink.anchor_text.lower()
        and len(backlink.anchor_text) > 3
    )
    if domain_exact_count > 3:
        score += 20
        reasons.append("Exact match anchor text overuse from domain")

    # 8. Very low domain authority
    if backlink.domain_authority and float(backlink.domain_authority) < 10:
        score += 10
        reasons.append("Very low domain authority")

    action = Backlink.Action.NONE
    if score >= 70:
        action = Backlink.Action.DISAVOW
    elif score >= 50:
        action = Backlink.Action.REVIEW

    return {
        "score": score,
        "reasons": reasons,
        "action": action,
    }


def detect_toxic_links(backlinks: list[Backlink]) -> list[Backlink]:
    """Detect and flag toxic links in a backlink profile.

    Args:
        backlinks: List of backlinks to analyze.

    Returns:
        List of backlinks that have been flagged as toxic.
    """
    toxic: list[Backlink] = []
    for bl in backlinks:
        result = calculate_toxicity_score(bl, backlinks)
        bl.toxicity_score = result["score"]
        bl.is_toxic = result["score"] >= 50
        bl.toxicity_reasons_json = result["reasons"]
        bl.recommended_action = result["action"]
        bl.save(
            update_fields=[
                "toxicity_score",
                "is_toxic",
                "toxicity_reasons_json",
                "recommended_action",
            ]
        )
        if bl.is_toxic:
            toxic.append(bl)
    return toxic


def analyze_backlink_profile(
    tenant_id: str,
    target_url: str | None = None,
) -> dict[str, Any]:
    """Analyze a backlink profile with full metrics.

    Args:
        tenant_id: Tenant scope identifier.
        target_url: Optional URL to filter by target.

    Returns:
        Dict with profile summary, anchor distribution, toxic links,
        and referring domain breakdown.
    """
    queryset = Backlink.objects.filter(tenant_id=tenant_id)
    if target_url:
        queryset = queryset.filter(target_url=target_url)

    backlinks = list(queryset)
    total = len(backlinks)

    if total == 0:
        return {
            "total_backlinks": 0,
            "referring_domains": 0,
            "dofollow_count": 0,
            "nofollow_count": 0,
            "toxic_count": 0,
            "avg_domain_authority": 0.0,
            "avg_page_authority": 0.0,
            "anchor_distribution": {},
            "domain_distribution": [],
            "toxic_links": [],
        }

    # Run toxicity detection
    toxic = detect_toxic_links(backlinks)

    # Aggregate metrics
    domains = Counter(bl.referring_domain for bl in backlinks if bl.referring_domain)
    link_types = Counter(bl.link_type for bl in backlinks)
    anchors = Counter(bl.anchor_text for bl in backlinks if bl.anchor_text)

    da_values = [float(bl.domain_authority) for bl in backlinks if bl.domain_authority is not None]
    pa_values = [float(bl.page_authority) for bl in backlinks if bl.page_authority is not None]

    avg_da = round(sum(da_values) / len(da_values), 2) if da_values else 0.0
    avg_pa = round(sum(pa_values) / len(pa_values), 2) if pa_values else 0.0

    # Per-domain breakdown
    domain_breakdown: list[dict[str, Any]] = []
    for domain, count in domains.most_common(20):
        domain_links = [bl for bl in backlinks if bl.referring_domain == domain]
        avg_dom_da = round(
            sum(float(bl.domain_authority) for bl in domain_links if bl.domain_authority)
            / max(len(domain_links), 1),
            2,
        )
        domain_breakdown.append(
            {
                "domain": domain,
                "backlink_count": count,
                "domain_authority": avg_dom_da,
                "toxic_count": sum(1 for bl in domain_links if bl.is_toxic),
            }
        )

    return {
        "total_backlinks": total,
        "referring_domains": len(domains),
        "dofollow_count": link_types.get(Backlink.LinkType.DOFOLLOW, 0),
        "nofollow_count": link_types.get(Backlink.LinkType.NOFOLLOW, 0),
        "ugc_count": link_types.get(Backlink.LinkType.UGC, 0),
        "sponsored_count": link_types.get(Backlink.LinkType.SPONSORED, 0),
        "toxic_count": len(toxic),
        "toxic_percentage": round(len(toxic) / total * 100, 2) if total else 0,
        "avg_domain_authority": avg_da,
        "avg_page_authority": avg_pa,
        "avg_toxicity_score": round(sum(float(bl.toxicity_score) for bl in backlinks) / total, 2),
        "anchor_distribution": dict(anchors.most_common(20)),
        "domain_distribution": domain_breakdown,
        "toxic_links": [
            {
                "id": str(bl.id),
                "source_url": bl.source_url,
                "anchor_text": bl.anchor_text,
                "toxicity_score": float(bl.toxicity_score),
                "reasons": bl.toxicity_reasons_json,
                "action": bl.recommended_action,
            }
            for bl in toxic
        ],
    }
