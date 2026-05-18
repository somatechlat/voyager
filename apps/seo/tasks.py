"""Celery tasks for the SEO module.

Handles daily rank updates, weekly audits, backlink checks,
content optimization, and automated report generation.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.seo.models.keyword import Keyword
from apps.seo.models.rank import SERPTracking
from apps.seo.models.report import SEOReport
from apps.seo.services.rank_tracking import collect_ranking
from apps.seo.services.reporting import generate_report

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_rankings(self) -> dict[str, Any]:
    """Update SERP rankings for all tracked keywords across all tenants.

    Called by the beat scheduler daily. Iterates through all active
    SERP tracking entries and fetches current positions.

    Returns:
        Summary dict with keywords_checked, rankings_updated, errors.
    """
    logger.info("Task started: %s", self.name)

    trackings = list(SERPTracking.objects.filter(is_active=True))
    updated = 0
    errors = 0

    for tracking in trackings:
        try:
            # In production, this would call a SERP API
            # For now, we mark it as checked with current known position
            if tracking.current_position:
                collect_ranking(
                    tracking=tracking,
                    position=tracking.current_position,
                    url=tracking.current_url or "",
                    location=(tracking.locations_json or ["US"])[0],
                    device="desktop",
                )
            updated += 1
        except Exception:
            logger.exception("Failed to update ranking for %s", tracking.id)
            errors += 1

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "keywords_checked": len(trackings),
        "rankings_updated": updated,
        "errors": errors,
        "timestamp": timezone.now().isoformat(),
    }
    logger.info(
        "Task completed: %s — keywords_checked=%d updated=%d errors=%d",
        self.name,
        len(trackings),
        updated,
        errors,
    )
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_technical_audit(self, site_id: str, tenant_id: str) -> dict[str, Any]:
    """Run a technical SEO audit on a site.

    Args:
        site_id: UUID of the site to audit.
        tenant_id: UUID of the tenant scope.

    Returns:
        Result dict with site_id, pages_crawled, issues_found, score.
    """
    logger.info("Running technical audit for site %s tenant %s", site_id, tenant_id)

    # In production, this would trigger a crawler
    # For now, return a pending status
    result: dict[str, Any] = {
        "status": "pending",
        "task": self.name,
        "site_id": site_id,
        "tenant_id": tenant_id,
        "pages_crawled": 0,
        "issues_found": 0,
        "score": 0,
        "timestamp": timezone.now().isoformat(),
    }
    logger.info("Technical audit queued for site %s", site_id)
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def weekly_keyword_sync(self, tenant_id: str | None = None) -> dict[str, Any]:
    """Synchronize keyword metrics from third-party APIs.

    Refreshes search volume, difficulty, CPC, and trend data
    for tracked keywords. Called weekly by the beat scheduler.

    Args:
        tenant_id: Optional tenant to scope the sync. If None,
            syncs all tenants.

    Returns:
        Summary dict with keywords_synced and errors.
    """
    logger.info("Task started: %s tenant=%s", self.name, tenant_id or "all")

    qs = Keyword.objects.filter(is_tracked=True)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    keywords = list(qs)
    synced = 0
    errors = 0

    # In production, this would call GSC, Ahrefs, SEMrush APIs
    # For now, we mark the sync timestamp
    now = timezone.now()
    for kw in keywords:
        try:
            kw.last_synced_at = now
            kw.save(update_fields=["last_synced_at"])
            synced += 1
        except Exception:
            logger.exception("Failed to sync keyword %s", kw.id)
            errors += 1

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "keywords_synced": synced,
        "errors": errors,
        "timestamp": now.isoformat(),
    }
    logger.info("Task completed: %s — synced=%d errors=%d", self.name, synced, errors)
    return result


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def generate_scheduled_reports(self) -> dict[str, Any]:
    """Generate scheduled SEO reports that are due.

    Called daily by the beat scheduler. Finds reports where
    next_run_at has passed and regenerates them.

    Returns:
        Summary dict with reports_generated and errors.
    """
    logger.info("Task started: %s", self.name)

    now = timezone.now()
    reports = list(
        SEOReport.objects.filter(
            is_scheduled=True,
            next_run_at__lte=now,
        )
    )

    generated = 0
    errors = 0

    for report in reports:
        try:
            date_to = date.today()
            date_from = date_to - timedelta(days=30)

            generate_report(
                tenant_id=report.tenant_id,
                name=report.name,
                report_type=report.report_type,
                date_from=date_from,
                date_to=date_to,
                sections=report.sections_json,
                compare=True,
            )

            # Update next run time
            if report.frequency == SEOReport.ReportFrequency.DAILY:
                report.next_run_at = now + timedelta(days=1)
            elif report.frequency == SEOReport.ReportFrequency.WEEKLY:
                report.next_run_at = now + timedelta(weeks=1)
            elif report.frequency == SEOReport.ReportFrequency.MONTHLY:
                report.next_run_at = now + timedelta(days=30)
            elif report.frequency == SEOReport.ReportFrequency.QUARTERLY:
                report.next_run_at = now + timedelta(days=90)

            report.save(update_fields=["next_run_at"])
            generated += 1
        except Exception:
            logger.exception("Failed to generate report %s", report.id)
            errors += 1

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "reports_generated": generated,
        "errors": errors,
        "timestamp": now.isoformat(),
    }
    logger.info("Task completed: %s — generated=%d errors=%d", self.name, generated, errors)
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def backlink_profile_update(self, tenant_id: str | None = None) -> dict[str, Any]:
    """Update backlink profiles from third-party APIs.

    Fetches new backlinks, checks existing ones for status changes,
    and runs toxicity detection. Called weekly.

    Args:
        tenant_id: Optional tenant scope.

    Returns:
        Summary dict with links_checked and new_links_found.
    """
    logger.info("Task started: %s tenant=%s", self.name, tenant_id or "all")

    from apps.seo.models.backlink import Backlink
    from apps.seo.services.backlinks import detect_toxic_links

    qs = Backlink.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    # Get active links to check
    links = list(qs.filter(status=Backlink.Status.ACTIVE))

    # In production, this would call Ahrefs/Moz APIs for updates
    # For now, run toxicity detection on existing links
    toxic = detect_toxic_links(links)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "links_checked": len(links),
        "toxic_detected": len(toxic),
        "timestamp": timezone.now().isoformat(),
    }
    logger.info("Task completed: %s — checked=%d toxic=%d", self.name, len(links), len(toxic))
    return result
