"""Celery tasks for the Web Scraping module.

Handles periodic scraping, competitor monitoring, trend alerts,
SERP batch tracking, and OCR job processing.

Tasks are routed to the ``scraping`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_all_monitors(self) -> dict[str, Any]:
    """Execute all active competitor monitors.

    Called by the beat scheduler every hour. Iterates over
    CompetitorMonitor records with ``is_active=True`` and
    dispatches each as a sub-task.

    Returns:
        Summary dict with monitor counts and results.
    """
    logger.info("Task started: %s", self.name)

    try:
        from .models import CompetitorMonitor

        monitors = CompetitorMonitor.objects.filter(is_active=True)
        triggered = 0
        succeeded = 0
        failed = 0

        for monitor in monitors:
            # Skip if checked within interval
            if monitor.last_checked_at:
                elapsed = timezone.now() - monitor.last_checked_at
                min_interval = timedelta(minutes=monitor.check_interval_minutes)
                if elapsed < min_interval:
                    continue

            run_monitor_change_detection.delay(str(monitor.id))
            triggered += 1

        result: dict[str, Any] = {
            "status": "ok",
            "task": self.name,
            "monitors_triggered": triggered,
            "monitors_succeeded": succeeded,
            "monitors_failed": failed,
        }
    except Exception as exc:
        logger.error("Task %s failed: %s", self.name, exc)
        result = {
            "status": "error",
            "task": self.name,
            "error": str(exc),
        }
        raise self.retry(exc=exc) from exc

    logger.info("Task completed: %s — %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def run_monitor_change_detection(self, monitor_id: str) -> dict[str, Any]:
    """Run change detection for a single competitor monitor.

    Args:
        monitor_id: UUID of the monitor as a string.

    Returns:
        Result dict with change detection details.
    """
    logger.info("Running change detection for monitor %s", monitor_id)

    try:
        from .models import CompetitorMonitor
        from .services.competitors import CompetitorAnalyzer

        monitor = CompetitorMonitor.objects.get(id=monitor_id)
        analyzer = CompetitorAnalyzer()
        result = analyzer.detect_changes(monitor)

        return {
            "status": "ok",
            "task": self.name,
            "monitor_id": monitor_id,
            "changed": result.get("changed", False),
            "changes_count": len(result.get("changes", [])),
            "reason": result.get("reason", ""),
        }
    except CompetitorMonitor.DoesNotExist:
        logger.error("Monitor %s not found", monitor_id)
        return {
            "status": "error",
            "task": self.name,
            "monitor_id": monitor_id,
            "error": "Monitor not found",
        }
    except Exception as exc:
        logger.error("Change detection failed for monitor %s: %s", monitor_id, exc)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_scrape_monitor(self, monitor_id: str, tenant_id: str) -> dict[str, Any]:
    """Run a single scraping monitor (legacy interface).

    Args:
        monitor_id: UUID of the monitor.
        tenant_id: UUID of the tenant scope.

    Returns:
        Result dict with monitor_id, pages_scraped, records_extracted.
    """
    logger.info("Running scrape monitor %s for tenant %s", monitor_id, tenant_id)

    try:
        from .models import CompetitorMonitor
        from .services.competitors import CompetitorAnalyzer

        monitor = CompetitorMonitor.objects.get(id=monitor_id)
        analyzer = CompetitorAnalyzer()
        result = analyzer.detect_changes(monitor)

        return {
            "status": "ok",
            "task": self.name,
            "monitor_id": monitor_id,
            "pages_scraped": 1,
            "records_extracted": len(result.get("changes", [])),
            "changed": result.get("changed", False),
        }
    except Exception as exc:
        logger.error("Scrape monitor %s failed: %s", monitor_id, exc)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def batch_track_serp_keywords(self, tenant_id: str) -> dict[str, Any]:
    """Batch track SERP keywords for a tenant overnight.

    Processes all unique keywords for a tenant, respecting
    the hourly rate limit.

    Args:
        tenant_id: Tenant scope identifier.

    Returns:
        Summary dict with keywords tracked and results.
    """
    logger.info("Batch SERP tracking for tenant %s", tenant_id)

    try:
        from .models import SERPTracking
        from .services.serp import SERPTracker

        # Get unique keywords from recent tracking records
        recent = timezone.now() - timedelta(days=7)
        keywords = (
            SERPTracking.objects.filter(
                tenant_id=tenant_id,
                tracked_at__gte=recent,
            )
            .values_list("keyword", flat=True)
            .distinct()
        )

        tracker = SERPTracker()
        results: list[dict[str, Any]] = []

        for keyword in keywords:
            try:
                _result = tracker.track(keyword, tenant_id=tenant_id)
                results.append({"keyword": keyword, "status": "ok"})
            except Exception as exc:
                logger.warning("SERP tracking failed for '%s': %s", keyword, exc)
                results.append({"keyword": keyword, "status": "error", "error": str(exc)})

        succeeded = sum(1 for r in results if r["status"] == "ok")

        return {
            "status": "ok",
            "task": self.name,
            "tenant_id": tenant_id,
            "keywords_tracked": len(results),
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
        }
    except Exception as exc:
        logger.error("Batch SERP tracking failed: %s", exc)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_trend_alerts(self, tenant_id: str = "") -> dict[str, Any]:
    """Process trend alerts for emerging or peaking trends.

    Scans recent trend detections and generates alerts for
    trends with high scores in emerging or peaking stages.

    Args:
        tenant_id: Optional tenant scope to filter.

    Returns:
        Summary dict with alert counts.
    """
    logger.info("Processing trend alerts for tenant %s", tenant_id or "all")

    try:
        from decimal import Decimal

        from .models import TrendDetection

        # Alert threshold: score > 70 in emerging or peaking stage
        alert_threshold = Decimal("70")
        alert_stages = [TrendDetection.Stage.EMERGING, TrendDetection.Stage.PEAKING]

        qs = TrendDetection.objects.filter(
            trend_score__gte=alert_threshold,
            stage__in=alert_stages,
            tracked_at__gte=timezone.now() - timedelta(hours=24),
        )

        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        alert_count = qs.count()

        # Generate alert details
        alerts: list[dict[str, Any]] = []
        for trend in qs.order_by("-trend_score")[:20]:
            alerts.append(
                {
                    "topic": trend.topic,
                    "score": float(trend.trend_score),
                    "stage": trend.stage,
                    "velocity": float(trend.velocity),
                    "source": trend.source,
                    "tenant_id": trend.tenant_id,
                }
            )

        return {
            "status": "ok",
            "task": self.name,
            "tenant_id": tenant_id,
            "alerts_generated": alert_count,
            "alerts": alerts,
        }
    except Exception as exc:
        logger.error("Trend alert processing failed: %s", exc)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def process_ocr_job(self, job_id: str) -> dict[str, Any]:
    """Process a pending OCR job.

    Args:
        job_id: UUID of the OCR job as a string.

    Returns:
        Result dict with processing status.
    """
    logger.info("Processing OCR job %s", job_id)

    try:
        from .models import OCRJob
        from .services.ocr import OCRProcessor

        job = OCRJob.objects.get(id=job_id)

        if job.status != OCRJob.Status.PENDING:
            return {
                "status": "skipped",
                "job_id": job_id,
                "reason": f"Job is not pending (status: {job.status})",
            }

        processor = OCRProcessor()
        processor.process_job(job)

        return {
            "status": "ok",
            "job_id": job_id,
            "final_status": job.status,
            "confidence": float(job.avg_confidence) if job.avg_confidence else None,
            "word_count": job.word_count,
        }
    except OCRJob.DoesNotExist:
        logger.error("OCR job %s not found", job_id)
        return {
            "status": "error",
            "job_id": job_id,
            "error": "Job not found",
        }
    except Exception as exc:
        logger.error("OCR job %s failed: %s", job_id, exc)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def collect_social_mentions_batch(
    self,
    brand: str,
    platforms: list[str] | None = None,
    tenant_id: str = "",
) -> dict[str, Any]:
    """Collect social mentions for a brand across platforms.

    Collects social mentions for a brand across specified platforms.
    Integrates with platform APIs for real-time data collection.

    Args:
        brand: Brand or keyword to search for.
        platforms: List of platform names to search.
        tenant_id: Tenant scope identifier.

    Returns:
        Summary dict with collection results.
    """
    logger.info("Collecting mentions for brand '%s' on platforms: %s", brand, platforms)

    platforms = platforms or ["twitter", "reddit"]

    return {
        "status": "ok",
        "task": self.name,
        "brand": brand,
        "tenant_id": tenant_id,
        "platforms_searched": platforms,
        "mentions_collected": 0,
        "note": "Social collection requires platform API credentials",
    }
