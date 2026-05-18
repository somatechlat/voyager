"""Celery tasks for the Integrations module.

Background tasks for:
- OAuth token refresh (runs every 15 minutes)
- Integration health checks (runs every 5 minutes)
- Dead letter queue processing (runs every hour)
- Periodic sync triggers (runs every 10 minutes)
- Webhook delivery retries (runs every minute)
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.integrations.models import (
    PlatformConnection,
    PlatformHealth,
    SyncLog,
    WebhookDelivery,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_oauth_tokens(self) -> dict[str, Any]:
    """Refresh expired OAuth tokens for all active integrations.

    Scans for connections with tokens expiring within 30 minutes and
    refreshes them. Connections that fail refresh are marked expired.

    :returns: Dict with ``tokens_refreshed``, ``tokens_failed``,
        ``tokens_skipped``.
    """
    from apps.integrations.services.oauth import (
        get_expiring_connections,
        refresh_access_token,
    )

    connections = get_expiring_connections(minutes=30)
    refreshed = 0
    failed = 0
    skipped = 0

    logger.info("Token refresh task started: %d connections expiring soon", len(connections))

    for conn in connections:
        if not conn.refresh_token:
            skipped += 1
            continue
        try:
            refresh_access_token(conn)
            refreshed += 1
            logger.debug("Refreshed token for %s (%s)", conn.id, conn.platform)
        except Exception as exc:
            failed += 1
            conn.status = PlatformConnection.Status.EXPIRED
            conn.last_error = f"Refresh failed: {exc}"
            conn.save(update_fields=["status", "last_error", "updated_at"])
            logger.warning("Token refresh failed for %s (%s): %s", conn.id, conn.platform, exc)

    logger.info(
        "Token refresh task completed: refreshed=%d, failed=%d, skipped=%d",
        refreshed,
        failed,
        skipped,
    )
    return {
        "status": "ok",
        "task": self.name,
        "tokens_refreshed": refreshed,
        "tokens_failed": failed,
        "tokens_skipped": skipped,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def refresh_single_token(self, connection_id: str) -> dict[str, Any]:
    """Refresh the access token for a single connection.

    :param connection_id: UUID of the PlatformConnection.
    :returns: Dict with ``success`` and ``expires_at``.
    """
    from apps.integrations.services.oauth import refresh_access_token

    try:
        conn = PlatformConnection.objects.get(id=connection_id)
        result = refresh_access_token(conn)
        return {"success": True, "connection_id": connection_id, **result}
    except PlatformConnection.DoesNotExist:
        logger.error("Connection not found for refresh: %s", connection_id)
        return {"success": False, "connection_id": connection_id, "error": "Not found"}
    except Exception as exc:
        logger.error("Single token refresh failed for %s: %s", connection_id, exc)
        return {"success": False, "connection_id": connection_id, "error": str(exc)}


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def check_integration_health(self, connection_id: str | None = None) -> dict[str, Any]:
    """Check the health of a specific or all active integrations.

    :param connection_id: Optional UUID to check a single connection.
    :returns: Dict with ``total``, ``healthy``, ``degraded``, ``down``.
    """
    from apps.integrations.services.health import (
        check_all_connections,
        check_connection_health,
    )

    if connection_id:
        try:
            conn = PlatformConnection.objects.get(id=connection_id)
            health = check_connection_health(conn)
            return {
                "status": "ok",
                "task": self.name,
                "connection_id": connection_id,
                "platform": conn.platform,
                "health_status": health.status,
                "latency_ms": health.latency_ms,
                "error": health.error_message,
            }
        except PlatformConnection.DoesNotExist:
            return {
                "status": "error",
                "task": self.name,
                "connection_id": connection_id,
                "error": "Connection not found",
            }
        except Exception as exc:
            logger.error("Health check failed for %s: %s", connection_id, exc)
            return {
                "status": "error",
                "task": self.name,
                "connection_id": connection_id,
                "error": str(exc),
            }

    result = check_all_connections()
    logger.info(
        "Bulk health check: total=%d, healthy=%d, degraded=%d, down=%d",
        result["total"],
        result["healthy"],
        result["degraded"],
        result["down"],
    )
    return {"status": "ok", "task": self.name, **result}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def check_tenant_health(self, tenant_id: str) -> dict[str, Any]:
    """Check health for all connections in a tenant.

    :param tenant_id: The tenant ID to check.
    :returns: Dict with health results.
    """
    from apps.integrations.services.health import check_all_connections

    result = check_all_connections(tenant_id=tenant_id)
    return {"status": "ok", "task": self.name, "tenant_id": tenant_id, **result}


# ---------------------------------------------------------------------------
# Webhook delivery
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=5, default_retry_delay=10)
def deliver_webhook_task(self, delivery_id: str) -> dict[str, Any]:
    """Deliver a single webhook payload asynchronously.

    :param delivery_id: UUID of the WebhookDelivery.
    :returns: Dict with ``success``, ``status``, and ``attempts``.
    """
    from apps.integrations.services.webhooks import deliver_webhook

    try:
        delivery = WebhookDelivery.objects.select_related("webhook").get(id=delivery_id)
        result = deliver_webhook(delivery.webhook, delivery)
        return {"success": result["success"], "delivery_id": delivery_id, **result}
    except WebhookDelivery.DoesNotExist:
        logger.error("Webhook delivery not found: %s", delivery_id)
        return {"success": False, "delivery_id": delivery_id, "error": "Not found"}
    except Exception as exc:
        logger.error("Webhook delivery failed for %s: %s", delivery_id, exc)
        return {"success": False, "delivery_id": delivery_id, "error": str(exc)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_dead_letter_queue_task(self) -> dict[str, Any]:
    """Process the dead-letter queue for failed webhook deliveries.

    :returns: Dict with ``retried``, ``succeeded``, ``failed``.
    """
    from apps.integrations.services.webhooks import process_dead_letter_queue

    result = process_dead_letter_queue(max_age_minutes=60)
    logger.info(
        "Dead letter queue processed: retried=%d, succeeded=%d, failed=%d",
        result["retried"],
        result["succeeded"],
        result["failed"],
    )
    return {"status": "ok", "task": self.name, **result}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def retry_pending_webhooks(self) -> dict[str, Any]:
    """Retry webhook deliveries stuck in pending/retrying status.

    Scans for deliveries whose ``next_retry_at`` has passed and
    attempts delivery.

    :returns: Dict with ``retried`` and ``succeeded`` counts.
    """
    pending = WebhookDelivery.objects.filter(
        status__in=(WebhookDelivery.Status.PENDING, WebhookDelivery.Status.RETRYING),
        next_retry_at__lte=timezone.now(),
    ).select_related("webhook")

    retried = 0
    succeeded = 0

    for delivery in pending:
        retried += 1
        try:
            from apps.integrations.services.webhooks import deliver_webhook

            result = deliver_webhook(delivery.webhook, delivery)
            if result["success"]:
                succeeded += 1
        except Exception as exc:
            logger.warning("Retry failed for delivery %s: %s", delivery.id, exc)

    return {"status": "ok", "task": self.name, "retried": retried, "succeeded": succeeded}


# ---------------------------------------------------------------------------
# Periodic sync triggers
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def trigger_scheduled_syncs(self) -> dict[str, Any]:
    """Trigger scheduled sync operations for active connections.

    Scans for connections with pending scheduled syncs and enqueues
    them. This task runs every 10 minutes.

    :returns: Dict with ``triggered`` count.
    """
    active = PlatformConnection.objects.filter(
        status=PlatformConnection.Status.ACTIVE,
    )

    triggered = 0
    for conn in active:
        # Check if there's a recent incomplete sync log
        recent = SyncLog.objects.filter(
            connection=conn,
            status__in=(SyncLog.Status.PENDING, SyncLog.Status.RUNNING),
            started_at__gte=timezone.now() - timezone.timedelta(minutes=10),
        ).first()
        if not recent:
            # Enqueue a default sync
            try:
                run_sync_task.delay(str(conn.id), "auto_sync", "inbound")
                triggered += 1
            except Exception as exc:
                logger.warning("Failed to enqueue sync for %s: %s", conn.id, exc)

    logger.info("Scheduled syncs triggered: %d", triggered)
    return {"status": "ok", "task": self.name, "triggered": triggered}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_sync_task(
    self,
    connection_id: str,
    sync_type: str,
    direction: str = "inbound",
    conflict_resolution: str = "source_wins",
    field_mappings_json: list[dict[str, Any] | None] = None,
) -> dict[str, Any]:
    """Run a sync operation for a connection.

    :param connection_id: UUID of the PlatformConnection.
    :param sync_type: Type of sync (e.g. ``"contacts"``).
    :param direction: Sync direction.
    :param conflict_resolution: Conflict strategy.
    :param field_mappings_json: Field mapping rules.
    :returns: Dict with sync results.
    """
    from apps.integrations.services.sync import run_sync_for_connection

    try:
        conn = PlatformConnection.objects.get(id=connection_id)
        return run_sync_for_connection(
            connection=conn,
            sync_type=sync_type,
            direction=direction,
            conflict_resolution=conflict_resolution,
            field_mappings_json=field_mappings_json or [],
        )
    except PlatformConnection.DoesNotExist:
        logger.error("Connection not found for sync: %s", connection_id)
        return {"success": False, "sync_log_id": "", "error": "Connection not found"}
    except Exception as exc:
        logger.error("Sync task failed for %s: %s", connection_id, exc)
        return {"success": False, "sync_log_id": "", "error": str(exc)}


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def cleanup_old_deliveries(self, days: int = 30) -> dict[str, Any]:
    """Delete old webhook deliveries and health checks.

    :param days: Age threshold in days.
    :returns: Dict with ``deliveries_deleted`` and ``health_deleted``.
    """
    cutoff = timezone.now() - timezone.timedelta(days=days)
    delivery_count, _ = WebhookDelivery.objects.filter(created_at__lt=cutoff).delete()
    health_count, _ = PlatformHealth.objects.filter(created_at__lt=cutoff).delete()

    logger.info(
        "Cleanup completed: deleted %d old deliveries and %d old health checks",
        delivery_count,
        health_count,
    )
    return {
        "status": "ok",
        "task": self.name,
        "deliveries_deleted": delivery_count,
        "health_deleted": health_count,
    }
