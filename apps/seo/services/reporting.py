"""SEO reporting service.

Implements automated report generation with white-label support,
section assembly, and period-over-period comparison.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from django.utils import timezone

from apps.seo.models.backlink import Backlink
from apps.seo.models.content import ContentOptimization
from apps.seo.models.keyword import Keyword
from apps.seo.models.onpage import OnPageAudit
from apps.seo.models.rank import SERPTracking
from apps.seo.models.report import SEOReport
from apps.seo.models.technical import TechnicalCrawl
from apps.seo.services.rank_tracking import get_ranking_distribution

logger = logging.getLogger(__name__)


def generate_executive_summary(
    tenant_id: str, date_from: date, date_to: date
) -> dict[str, Any]:
    """Generate executive summary metrics.

    Args:
        tenant_id: Tenant scope identifier.
        date_from: Period start date.
        date_to: Period end date.

    Returns:
        Dict with summary metrics.
    """
    total_keywords = Keyword.objects.filter(tenant_id=tenant_id).count()
    tracked_keywords = Keyword.objects.filter(tenant_id=tenant_id, is_tracked=True).count()
    distribution = get_ranking_distribution(tenant_id)

    avg_position = Keyword.objects.filter(
        tenant_id=tenant_id,
        current_position__isnull=False,
    )
    avg_pos = (
        sum(k.current_position for k in avg_position) / avg_position.count()
        if avg_position.exists()
        else 0
    )

    total_backlinks = Backlink.objects.filter(tenant_id=tenant_id).count()
    toxic_backlinks = Backlink.objects.filter(tenant_id=tenant_id, is_toxic=True).count()

    crawl_count = TechnicalCrawl.objects.filter(
        tenant_id=tenant_id,
        crawled_at__date__gte=date_from,
        crawled_at__date__lte=date_to,
    ).count()

    audit_count = OnPageAudit.objects.filter(
        tenant_id=tenant_id,
        audited_at__date__gte=date_from,
        audited_at__date__lte=date_to,
    ).count()

    avg_audit_score = OnPageAudit.objects.filter(
        tenant_id=tenant_id,
        score__isnull=False,
    )
    avg_score = (
        sum(float(a.score) for a in avg_audit_score) / avg_audit_score.count()
        if avg_audit_score.exists()
        else 0
    )

    return {
        "total_keywords": total_keywords,
        "tracked_keywords": tracked_keywords,
        "ranking_distribution": distribution,
        "avg_position": round(avg_pos, 2),
        "total_backlinks": total_backlinks,
        "toxic_backlinks": toxic_backlinks,
        "toxic_percentage": round(toxic_backlinks / total_backlinks * 100, 2) if total_backlinks else 0,
        "pages_crawled": crawl_count,
        "pages_audited": audit_count,
        "avg_audit_score": round(avg_score, 2),
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
    }


def generate_keyword_section(
    tenant_id: str, date_from: date, date_to: date
) -> dict[str, Any]:
    """Generate keyword rankings report section.

    Args:
        tenant_id: Tenant scope identifier.
        date_from: Period start.
        date_to: Period end.

    Returns:
        Dict with keyword ranking data.
    """
    keywords = list(Keyword.objects.filter(tenant_id=tenant_id, is_tracked=True))

    movers: list[dict[str, Any]] = []
    for kw in keywords:
        if kw.position_change and abs(kw.position_change) >= 3:
            movers.append({
                "keyword": kw.keyword,
                "current_position": kw.current_position,
                "previous_position": kw.previous_position,
                "change": kw.position_change,
            })

    movers.sort(key=lambda m: abs(m["change"]), reverse=True)

    return {
        "top_movers": {
            "improved": [m for m in movers if m["change"] > 0][:10],
            "declined": [m for m in movers if m["change"] < 0][:10],
        },
        "distribution": get_ranking_distribution(tenant_id),
        "total_tracked": len(keywords),
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
    }


def generate_backlink_section(
    tenant_id: str, date_from: date, date_to: date
) -> dict[str, Any]:
    """Generate backlink profile report section.

    Args:
        tenant_id: Tenant scope identifier.
        date_from: Period start.
        date_to: Period end.

    Returns:
        Dict with backlink profile data.
    """
    all_links = Backlink.objects.filter(tenant_id=tenant_id)
    total = all_links.count()
    new_links = all_links.filter(
        first_seen__date__gte=date_from,
        first_seen__date__lte=date_to,
    ).count()
    lost_links = all_links.filter(
        status=Backlink.Status.LOST,
        last_seen__date__gte=date_from,
    ).count()
    toxic = all_links.filter(is_toxic=True).count()
    domains = all_links.values("referring_domain").distinct().count()

    # Anchor distribution
    anchors: dict[str, int] = {}
    for bl in all_links:
        if bl.anchor_text:
            anchors[bl.anchor_text] = anchors.get(bl.anchor_text, 0) + 1

    return {
        "total_backlinks": total,
        "new_backlinks": new_links,
        "lost_backlinks": lost_links,
        "referring_domains": domains,
        "toxic_links": toxic,
        "toxic_percentage": round(toxic / total * 100, 2) if total else 0,
        "anchor_distribution": dict(
            sorted(anchors.items(), key=lambda x: x[1], reverse=True)[:15]
        ),
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
    }


def generate_technical_section(
    tenant_id: str, date_from: date, date_to: date
) -> dict[str, Any]:
    """Generate technical health report section.

    Args:
        tenant_id: Tenant scope identifier.
        date_from: Period start.
        date_to: Period end.

    Returns:
        Dict with technical health data.
    """
    pages = TechnicalCrawl.objects.filter(
        tenant_id=tenant_id,
        crawled_at__date__gte=date_from,
        crawled_at__date__lte=date_to,
    )

    all_issues: list[dict[str, Any]] = []
    for page in pages:
        all_issues.extend(page.issues_json or [])

    by_severity: dict[str, int] = {}
    for issue in all_issues:
        sev = issue.get("severity", "low")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    # CWV averages
    lcp_values = [p.lcp_ms for p in pages if p.lcp_ms]
    cls_values = [float(p.cls_score) for p in pages if p.cls_score]

    return {
        "pages_crawled": pages.count(),
        "issues_by_severity": by_severity,
        "total_issues": len(all_issues),
        "avg_lcp_ms": round(sum(lcp_values) / len(lcp_values), 2) if lcp_values else None,
        "avg_cls": round(sum(cls_values) / len(cls_values), 4) if cls_values else None,
        "mobile_unfriendly": pages.filter(is_mobile_friendly=False).count(),
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
    }


def generate_content_section(
    tenant_id: str, date_from: date, date_to: date
) -> dict[str, Any]:
    """Generate content score report section.

    Args:
        tenant_id: Tenant scope identifier.
        date_from: Period start.
        date_to: Period end.

    Returns:
        Dict with content score data.
    """
    audits = ContentOptimization.objects.filter(
        tenant_id=tenant_id,
        analyzed_at__date__gte=date_from,
        analyzed_at__date__lte=date_to,
    )

    scores = [float(a.content_score) for a in audits if a.content_score]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0

    # Common recommendations
    all_recs: list[dict[str, Any]] = []
    for audit in audits:
        all_recs.extend(audit.recommendations_json or [])

    rec_types: dict[str, int] = {}
    for rec in all_recs:
        rt = rec.get("type", "unknown")
        rec_types[rt] = rec_types.get(rt, 0) + 1

    return {
        "pages_audited": audits.count(),
        "avg_score": avg_score,
        "top_recommendations": dict(
            sorted(rec_types.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
    }


def generate_report(
    tenant_id: str,
    name: str,
    report_type: str,
    date_from: date,
    date_to: date,
    sections: list[str] | None = None,
    compare: bool = True,
    **branding: Any,
) -> SEOReport:
    """Generate a comprehensive SEO report.

    Args:
        tenant_id: Tenant scope identifier.
        name: Report name.
        report_type: Type of report.
        date_from: Period start.
        date_to: Period end.
        sections: List of section names to include.
        compare: Whether to compare with previous period.
        **branding: White-label branding options.

    Returns:
        Created SEOReport instance.
    """
    sections = sections or [
        "executive_summary",
        "keyword_rankings",
        "backlink_profile",
        "technical_health",
        "content_score",
    ]

    report = SEOReport.objects.create(
        tenant_id=tenant_id,
        name=name,
        report_type=report_type,
        frequency=SEOReport.ReportFrequency.ONE_TIME,
        status=SEOReport.Status.GENERATING,
        sections_json=sections,
        date_from=date_from,
        date_to=date_to,
        compare_with_previous=compare,
        brand_name=branding.get("brand_name", ""),
        brand_primary_color=branding.get("brand_primary_color", ""),
        brand_logo_url=branding.get("brand_logo_url", ""),
        custom_header=branding.get("custom_header", ""),
        custom_footer=branding.get("custom_footer", ""),
        recipients_json=branding.get("recipients", []),
    )

    # Generate each section
    if "executive_summary" in sections:
        report.executive_summary_json = generate_executive_summary(
            tenant_id, date_from, date_to
        )

    if "keyword_rankings" in sections:
        report.keyword_rankings_json = generate_keyword_section(
            tenant_id, date_from, date_to
        )

    if "backlink_profile" in sections:
        report.backlink_profile_json = generate_backlink_section(
            tenant_id, date_from, date_to
        )

    if "technical_health" in sections:
        report.technical_health_json = generate_technical_section(
            tenant_id, date_from, date_to
        )

    if "content_score" in sections:
        report.content_score_json = generate_content_section(
            tenant_id, date_from, date_to
        )

    # Previous period comparison
    if compare:
        period_days = (date_to - date_from).days
        prev_from = date_from - timedelta(days=period_days)
        prev_to = date_from - timedelta(days=1)
        report.previous_period_json = {
            "executive_summary": generate_executive_summary(tenant_id, prev_from, prev_to),
            "keyword_rankings": generate_keyword_section(tenant_id, prev_from, prev_to),
            "period": {"from": prev_from.isoformat(), "to": prev_to.isoformat()},
        }

    report.status = SEOReport.Status.COMPLETED
    report.generated_at = timezone.now()
    report.save()

    logger.info("Generated SEO report %s for tenant %s", report.id, tenant_id)
    return report
