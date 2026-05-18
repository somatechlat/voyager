"""Technical crawl service.

Implements site crawling, Core Web Vitals assessment,
error detection, and technical SEO issue identification.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from django.utils import timezone

from apps.seo.models.technical import TechnicalCrawl

logger = logging.getLogger(__name__)

# Core Web Vitals thresholds (in milliseconds or score)
_LCP_GOOD = 2500
_LCP_NEEDS_IMPROVEMENT = 4000
_FID_GOOD = 100
_FID_NEEDS_IMPROVEMENT = 300
_CLS_GOOD = 0.1
_CLS_NEEDS_IMPROVEMENT = 0.25
_TTFB_GOOD = 600


def check_cwv(lcp_ms: int | None, fid_ms: int | None, cls_score: float | None) -> dict[str, str]:
    """Assess Core Web Vitals status.

    Args:
        lcp_ms: Largest Contentful Paint in ms.
        fid_ms: First Input Delay in ms.
        cls_score: Cumulative Layout Shift score.

    Returns:
        Dict with status for each metric ("good", "needs_improvement", "poor").
    """
    result: dict[str, str] = {}
    if lcp_ms is not None:
        if lcp_ms <= _LCP_GOOD:
            result["lcp"] = "good"
        elif lcp_ms <= _LCP_NEEDS_IMPROVEMENT:
            result["lcp"] = "needs_improvement"
        else:
            result["lcp"] = "poor"
    if fid_ms is not None:
        if fid_ms <= _FID_GOOD:
            result["fid"] = "good"
        elif fid_ms <= _FID_NEEDS_IMPROVEMENT:
            result["fid"] = "needs_improvement"
        else:
            result["fid"] = "poor"
    if cls_score is not None:
        if cls_score <= _CLS_GOOD:
            result["cls"] = "good"
        elif cls_score <= _CLS_NEEDS_IMPROVEMENT:
            result["cls"] = "needs_improvement"
        else:
            result["cls"] = "poor"
    return result


def check_technical_issues(
    url: str,
    status_code: int | None,
    canonical: str,
    hreflangs: list[dict[str, Any]],
    structured_data: list[dict[str, Any]],
    lcp_ms: int | None,
    fid_ms: int | None,
    cls_score: float | None,
    ttfb_ms: int | None,
    robots_meta: str,
    is_mobile_friendly: bool | None,
    title: str,
    meta_description: str,
    h1_count: int,
    word_count: int,
    internal_links: list[dict[str, Any]],
    external_links: list[dict[str, Any]],
    broken_links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check a page for technical SEO issues.

    Args:
        url: Page URL.
        status_code: HTTP response code.
        canonical: Canonical URL.
        hreflangs: Hreflang declarations.
        structured_data: JSON-LD schemas.
        lcp_ms: LCP in ms.
        fid_ms: FID in ms.
        cls_score: CLS score.
        ttfb_ms: TTFB in ms.
        robots_meta: Robots meta tag value.
        is_mobile_friendly: Mobile-friendly status.
        title: Page title.
        meta_description: Meta description.
        h1_count: Number of H1 tags.
        word_count: Word count.
        internal_links: Internal link list.
        external_links: External link list.
        broken_links: Broken link list.

    Returns:
        List of issue dicts with type, severity, and details.
    """
    issues: list[dict[str, Any]] = []

    # HTTP status
    if status_code and status_code >= 400:
        severity = "critical" if status_code >= 500 else "high"
        issues.append({"type": "http_error", "status_code": status_code, "severity": severity})
    elif status_code and status_code >= 300:
        issues.append({"type": "redirect", "status_code": status_code, "severity": "low"})

    # Core Web Vitals
    cwv = check_cwv(lcp_ms, fid_ms, cls_score)
    if cwv.get("lcp") == "poor":
        issues.append(
            {"type": "slow_lcp", "value": lcp_ms, "threshold": _LCP_GOOD, "severity": "high"}
        )
    elif cwv.get("lcp") == "needs_improvement":
        issues.append(
            {"type": "slow_lcp", "value": lcp_ms, "threshold": _LCP_GOOD, "severity": "medium"}
        )

    if cwv.get("fid") == "poor":
        issues.append(
            {"type": "high_fid", "value": fid_ms, "threshold": _FID_GOOD, "severity": "medium"}
        )

    if cwv.get("cls") == "poor":
        issues.append(
            {"type": "high_cls", "value": cls_score, "threshold": _CLS_GOOD, "severity": "medium"}
        )

    if ttfb_ms and ttfb_ms > _TTFB_GOOD:
        issues.append(
            {"type": "slow_ttfb", "value": ttfb_ms, "threshold": _TTFB_GOOD, "severity": "medium"}
        )

    # Canonical
    if not canonical:
        issues.append({"type": "missing_canonical", "severity": "medium"})
    elif canonical != url:
        issues.append(
            {"type": "canonical_mismatch", "canonical": canonical, "url": url, "severity": "low"}
        )

    # Hreflang
    if hreflangs:
        seen = set()
        for hl in hreflangs:
            lang = hl.get("lang", "")
            if not lang or not re.match(r"^[a-zA-Z]{2}(-[a-zA-Z]{2})?$", lang):
                issues.append({"type": "invalid_hreflang", "lang": lang, "severity": "medium"})
            href = hl.get("href", "")
            if href in seen:
                issues.append({"type": "duplicate_hreflang", "href": href, "severity": "low"})
            seen.add(href)

    # Structured data
    if not structured_data:
        issues.append({"type": "missing_structured_data", "severity": "medium"})

    # Robots meta
    if "noindex" in robots_meta.lower():
        issues.append({"type": "noindex_tag", "robots": robots_meta, "severity": "high"})

    # Mobile
    if is_mobile_friendly is False:
        issues.append({"type": "not_mobile_friendly", "severity": "high"})

    # Content basics
    if not title:
        issues.append({"type": "missing_title", "severity": "critical"})
    if not meta_description:
        issues.append({"type": "missing_meta_description", "severity": "high"})
    if h1_count == 0:
        issues.append({"type": "missing_h1", "severity": "critical"})
    elif h1_count > 1:
        issues.append({"type": "multiple_h1", "count": h1_count, "severity": "medium"})
    if word_count < 300:
        issues.append({"type": "thin_content", "word_count": word_count, "severity": "medium"})

    # Links
    broken_count = len(broken_links)
    if broken_count > 0:
        severity = "high" if broken_count > 10 else "medium"
        issues.append({"type": "broken_links", "count": broken_count, "severity": severity})

    if len(internal_links) < 3:
        issues.append(
            {"type": "few_internal_links", "count": len(internal_links), "severity": "low"}
        )

    return issues


def crawl_page(
    tenant_id: str,
    crawl_job_id: str,
    url: str,
    status_code: int | None = 200,
    title: str = "",
    meta_description: str = "",
    h1: str = "",
    h1_count: int = 0,
    canonical: str = "",
    hreflangs: list[dict[str, Any]] | None = None,
    structured_data: list[dict[str, Any]] | None = None,
    lcp_ms: int | None = None,
    fid_ms: int | None = None,
    cls_score: float | None = None,
    ttfb_ms: int | None = None,
    page_size_kb: int | None = None,
    load_time_ms: int | None = None,
    robots_meta: str = "",
    is_mobile_friendly: bool | None = None,
    is_indexable: bool = True,
    word_count: int = 0,
    internal_links: list[dict[str, Any]] | None = None,
    external_links: list[dict[str, Any]] | None = None,
    broken_links: list[dict[str, Any]] | None = None,
) -> TechnicalCrawl:
    """Crawl and analyze a single page for technical SEO issues.

    Args:
        tenant_id: Tenant scope identifier.
        crawl_job_id: Parent crawl job ID.
        url: Page URL.
        status_code: HTTP response code.
        title: Page title.
        meta_description: Meta description.
        h1: H1 tag content.
        h1_count: Number of H1 tags.
        canonical: Canonical URL.
        hreflangs: Hreflang declarations.
        structured_data: JSON-LD schemas.
        lcp_ms: LCP in ms.
        fid_ms: FID in ms.
        cls_score: CLS score.
        ttfb_ms: TTFB in ms.
        page_size_kb: Page size in KB.
        load_time_ms: Page load time in ms.
        robots_meta: Robots meta tag.
        is_mobile_friendly: Mobile-friendly status.
        is_indexable: Whether page is indexable.
        word_count: Word count.
        internal_links: Internal link list.
        external_links: External link list.
        broken_links: Broken link list.

    Returns:
        Created TechnicalCrawl instance.
    """
    hreflangs = hreflangs or []
    structured_data = structured_data or []
    internal_links = internal_links or []
    external_links = external_links or []
    broken_links = broken_links or []

    issues = check_technical_issues(
        url=url,
        status_code=status_code,
        canonical=canonical,
        hreflangs=hreflangs,
        structured_data=structured_data,
        lcp_ms=lcp_ms,
        fid_ms=fid_ms,
        cls_score=cls_score,
        ttfb_ms=ttfb_ms,
        robots_meta=robots_meta,
        is_mobile_friendly=is_mobile_friendly,
        title=title,
        meta_description=meta_description,
        h1_count=h1_count,
        word_count=word_count,
        internal_links=internal_links,
        external_links=external_links,
        broken_links=broken_links,
    )

    # Calculate SEO score (100 - penalties)
    severity_penalties = {"critical": 15, "high": 8, "medium": 4, "low": 1}
    penalty = sum(severity_penalties.get(issue.get("severity", "low"), 1) for issue in issues)
    seo_score = max(0.0, 100.0 - penalty)

    crawl = TechnicalCrawl.objects.create(
        tenant_id=tenant_id,
        crawl_job_id=crawl_job_id,
        url=url,
        status_code=status_code,
        is_indexable=is_indexable,
        word_count=word_count,
        title=title,
        meta_description=meta_description,
        h1=h1,
        h1_count=h1_count,
        canonical=canonical,
        robots_meta=robots_meta,
        hreflangs_json=hreflangs,
        lcp_ms=lcp_ms,
        fid_ms=fid_ms,
        cls_score=cls_score,
        ttfb_ms=ttfb_ms,
        page_size_kb=page_size_kb,
        load_time_ms=load_time_ms,
        structured_data_json=structured_data,
        issues_json=issues,
        seo_score=round(seo_score, 2),
        is_mobile_friendly=is_mobile_friendly,
        internal_links_json=internal_links,
        external_links_json=external_links,
        broken_links_json=broken_links,
        crawled_at=timezone.now(),
    )
    return crawl


def get_crawl_summary(tenant_id: str, crawl_job_id: str) -> dict[str, Any]:
    """Get summary statistics for a crawl job.

    Args:
        tenant_id: Tenant scope identifier.
        crawl_job_id: The crawl job ID.

    Returns:
        Dict with pages_crawled, critical_issues, warning_issues,
        avg_load_time, broken_links, and avg_seo_score.
    """
    pages = list(TechnicalCrawl.objects.filter(tenant_id=tenant_id, crawl_job_id=crawl_job_id))
    total = len(pages)

    if total == 0:
        return {
            "pages_crawled": 0,
            "critical_issues": 0,
            "warning_issues": 0,
            "avg_load_time_ms": 0,
            "broken_links": 0,
            "avg_seo_score": 0.0,
        }

    all_issues: list[dict[str, Any]] = []
    for page in pages:
        all_issues.extend(page.issues_json or [])

    load_times = [p.load_time_ms for p in pages if p.load_time_ms]
    scores = [float(p.seo_score) for p in pages if p.seo_score]
    broken = sum(len(p.broken_links_json or []) for p in pages)

    return {
        "pages_crawled": total,
        "critical_issues": sum(1 for i in all_issues if i.get("severity") == "critical"),
        "warning_issues": sum(1 for i in all_issues if i.get("severity") in ("high", "medium")),
        "avg_load_time_ms": round(sum(load_times) / len(load_times), 2) if load_times else 0,
        "broken_links": broken,
        "avg_seo_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
    }
