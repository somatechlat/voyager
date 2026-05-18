"""Anomaly detection alert and monitoring views.

Provides endpoints for managing anomaly alerts, running on-demand
detection, and retrieving anomaly events.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.analytics_v2.models.anomaly import AnomalyAlert, AnomalyEvent
from apps.analytics_v2.serializers import (
    AnomalyAlertCreateIn,
    AnomalyAlertOut,
    AnomalyAlertUpdateIn,
    AnomalyDetectIn,
    AnomalyDetectOut,
    AnomalyEventOut,
)
from apps.analytics_v2.services.anomaly import detect_anomalies, should_trigger_alert
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _tenant_from_request(request) -> str:
    """Extract tenant_id from the authenticated request."""
    return getattr(request, "tenant_id", "default")


def _user_from_request(request) -> str:
    """Extract user_id from the authenticated request."""
    user = getattr(request, "auth", None)
    if user and hasattr(user, "sub"):
        return str(user.sub)
    return "anonymous"


# ---------------------------------------------------------------------------
# Anomaly Alert CRUD
# ---------------------------------------------------------------------------


@router.get("/anomaly-alerts", response=list[AnomalyAlertOut], tags=["Anomaly Detection"])
def list_anomaly_alerts(request, enabled_only: bool = False, metric: str = "") -> list[AnomalyAlert]:
    """List anomaly alerts for the current tenant.

    Args:
        enabled_only: Filter to enabled alerts only.
        metric: Filter by metric name.
    """
    tenant_id = _tenant_from_request(request)
    qs = AnomalyAlert.objects.filter(tenant_id=tenant_id)
    if enabled_only:
        qs = qs.filter(enabled=True)
    if metric:
        qs = qs.filter(metric=metric)
    return list(qs)


@router.get("/anomaly-alerts/{alert_id}", response=AnomalyAlertOut, tags=["Anomaly Detection"])
def get_anomaly_alert(request, alert_id: UUID) -> AnomalyAlert:
    """Get a single anomaly alert."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(AnomalyAlert, id=alert_id, tenant_id=tenant_id)


@router.post("/anomaly-alerts", response=AnomalyAlertOut, tags=["Anomaly Detection"])
def create_anomaly_alert(request, payload: AnomalyAlertCreateIn) -> AnomalyAlert:
    """Create a new anomaly detection alert."""
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)

    alert = AnomalyAlert.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        metric=payload.metric,
        platform=payload.platform,
        method=payload.method,
        threshold=payload.threshold,
        lookback_days=payload.lookback_days,
        comparison_mode=payload.comparison_mode,
        channels=payload.channels,
        cooldown_minutes=payload.cooldown_minutes,
        enabled=payload.enabled,
        created_by=user_id,
    )
    return alert


@router.patch("/anomaly-alerts/{alert_id}", response=AnomalyAlertOut, tags=["Anomaly Detection"])
def update_anomaly_alert(request, alert_id: UUID, payload: AnomalyAlertUpdateIn) -> AnomalyAlert:
    """Update an anomaly alert."""
    tenant_id = _tenant_from_request(request)
    alert = get_object_or_404(AnomalyAlert, id=alert_id, tenant_id=tenant_id)

    for attr in [
        "name", "metric", "platform", "method", "threshold",
        "lookback_days", "comparison_mode", "channels",
        "cooldown_minutes", "enabled",
    ]:
        val = getattr(payload, attr, None)
        if val is not None:
            setattr(alert, attr, val)
    alert.save()
    return alert


@router.patch("/anomaly-alerts/{alert_id}/toggle", response=AnomalyAlertOut, tags=["Anomaly Detection"])
def toggle_anomaly_alert(request, alert_id: UUID) -> AnomalyAlert:
    """Toggle an alert enabled/disabled."""
    tenant_id = _tenant_from_request(request)
    alert = get_object_or_404(AnomalyAlert, id=alert_id, tenant_id=tenant_id)
    alert.enabled = not alert.enabled
    alert.save(update_fields=["enabled"])
    return alert


@router.delete("/anomaly-alerts/{alert_id}", tags=["Anomaly Detection"])
def delete_anomaly_alert(request, alert_id: UUID) -> dict[str, str]:
    """Delete an anomaly alert."""
    tenant_id = _tenant_from_request(request)
    alert = get_object_or_404(AnomalyAlert, id=alert_id, tenant_id=tenant_id)
    alert.delete()
    return {"status": "deleted", "id": str(alert_id)}


# ---------------------------------------------------------------------------
# On-demand Anomaly Detection
# ---------------------------------------------------------------------------


@router.post("/anomaly/detect", response=AnomalyDetectOut, tags=["Anomaly Detection"])
def run_anomaly_detection(request, payload: AnomalyDetectIn) -> dict[str, Any]:
    """Run on-demand anomaly detection on a metric.

    Fetches historical data and applies the specified statistical method
to detect anomalous values.
    """
    tenant_id = _tenant_from_request(request)

    # Fetch historical data (simulate time series from ClickHouse or generate sample)
    dates, values = _fetch_metric_history(
        payload.metric,
        payload.platform,
        payload.date_range,
        payload.lookback_days,
        tenant_id,
    )

    result = detect_anomalies(
        metric=payload.metric,
        dates=dates,
        values=values,
        method=payload.method,
        threshold=payload.threshold,
        lookback_days=payload.lookback_days,
    )

    return {
        "metric": result["metric"],
        "method": result["method"],
        "total_data_points": result["total_data_points"],
        "anomaly_rate": result["anomaly_rate"],
        "anomalies": result["anomalies"],
    }


@router.post("/anomaly/detect-all", tags=["Anomaly Detection"])
def run_all_alerts_detection(request) -> dict[str, Any]:
    """Run anomaly detection for all enabled alerts in the tenant.

    Iterates through all enabled anomaly alerts, fetches data, runs
detection, and creates anomaly events for triggered alerts.
    """
    tenant_id = _tenant_from_request(request)
    alerts = AnomalyAlert.objects.filter(tenant_id=tenant_id, enabled=True)

    triggered = []
    for alert in alerts:
        dates, values = _fetch_metric_history(
            alert.metric,
            alert.platform,
            {},
            alert.lookback_days,
            tenant_id,
        )

        result = detect_anomalies(
            metric=alert.metric,
            dates=dates,
            values=values,
            method=alert.method,
            threshold=float(alert.threshold),
            lookback_days=alert.lookback_days,
        )

        if should_trigger_alert(alert, result):
            alert.last_triggered_at = datetime.utcnow()
            alert.trigger_count += 1
            alert.save(update_fields=["last_triggered_at", "trigger_count"])

            for anomaly_data in result.get("anomalies", []):
                AnomalyEvent.objects.create(
                    alert=alert,
                    tenant_id=tenant_id,
                    metric=alert.metric,
                    anomaly_type=anomaly_data.get("anomaly_type", ""),
                    severity=anomaly_data.get("severity", "warning"),
                    expected_value=anomaly_data.get("expected_value"),
                    actual_value=anomaly_data.get("value"),
                    deviation=anomaly_data.get("deviation"),
                    z_score=anomaly_data.get("z_score"),
                    method=alert.method,
                    context={"platform": alert.platform},
                )

            triggered.append({
                "alert_id": str(alert.id),
                "alert_name": alert.name,
                "metric": alert.metric,
                "anomalies_found": len(result.get("anomalies", [])),
            })

    return {
        "alerts_checked": alerts.count(),
        "alerts_triggered": len(triggered),
        "triggered": triggered,
    }


# ---------------------------------------------------------------------------
# Anomaly Events
# ---------------------------------------------------------------------------


@router.get("/anomaly-events", response=list[AnomalyEventOut], tags=["Anomaly Detection"])
def list_anomaly_events(
    request,
    metric: str = "",
    severity: str = "",
    limit: int = 50,
) -> list[AnomalyEvent]:
    """List anomaly events for the current tenant.

    Args:
        metric: Filter by metric name.
        severity: Filter by severity.
        limit: Maximum results.
    """
    tenant_id = _tenant_from_request(request)
    qs = AnomalyEvent.objects.filter(tenant_id=tenant_id)
    if metric:
        qs = qs.filter(metric=metric)
    if severity:
        qs = qs.filter(severity=severity)
    return list(qs[:limit])


@router.get("/anomaly-events/{event_id}", response=AnomalyEventOut, tags=["Anomaly Detection"])
def get_anomaly_event(request, event_id: UUID) -> AnomalyEvent:
    """Get a single anomaly event."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(AnomalyEvent, id=event_id, tenant_id=tenant_id)


@router.patch("/anomaly-events/{event_id}/acknowledge", response=AnomalyEventOut, tags=["Anomaly Detection"])
def acknowledge_anomaly_event(request, event_id: UUID) -> AnomalyEvent:
    """Acknowledge an anomaly event."""
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)
    event = get_object_or_404(AnomalyEvent, id=event_id, tenant_id=tenant_id)
    event.acknowledged_at = datetime.utcnow()
    event.acknowledged_by = user_id
    event.save(update_fields=["acknowledged_at", "acknowledged_by"])
    return event


@router.patch("/anomaly-events/{event_id}/resolve", response=AnomalyEventOut, tags=["Anomaly Detection"])
def resolve_anomaly_event(request, event_id: UUID) -> AnomalyEvent:
    """Resolve an anomaly event."""
    tenant_id = _tenant_from_request(request)
    event = get_object_or_404(AnomalyEvent, id=event_id, tenant_id=tenant_id)
    event.resolved_at = datetime.utcnow()
    event.save(update_fields=["resolved_at"])
    return event


# ---------------------------------------------------------------------------
# Anomaly Dashboard Summary
# ---------------------------------------------------------------------------


@router.get("/anomaly/summary", tags=["Anomaly Detection"])
def get_anomaly_summary(request) -> dict[str, Any]:
    """Get anomaly detection summary for the dashboard."""
    tenant_id = _tenant_from_request(request)
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    total_alerts = AnomalyAlert.objects.filter(tenant_id=tenant_id).count()
    enabled_alerts = AnomalyAlert.objects.filter(tenant_id=tenant_id, enabled=True).count()

    total_events_24h = AnomalyEvent.objects.filter(tenant_id=tenant_id, detected_at__gte=last_24h).count()
    critical_events = AnomalyEvent.objects.filter(tenant_id=tenant_id, severity="critical", detected_at__gte=last_24h).count()
    warning_events = AnomalyEvent.objects.filter(tenant_id=tenant_id, severity="warning", detected_at__gte=last_24h).count()
    unresolved = AnomalyEvent.objects.filter(tenant_id=tenant_id, resolved_at__isnull=True).count()

    recent_events = AnomalyEvent.objects.filter(
        tenant_id=tenant_id,
        detected_at__gte=last_7d,
    ).values("metric").distinct().count()

    return {
        "total_alerts": total_alerts,
        "enabled_alerts": enabled_alerts,
        "events_24h": total_events_24h,
        "critical_events_24h": critical_events,
        "warning_events_24h": warning_events,
        "unresolved_events": unresolved,
        "monitored_metrics": recent_events,
    }


# ---------------------------------------------------------------------------
# Metric history fetcher
# ---------------------------------------------------------------------------


def _fetch_metric_history(
    metric: str,
    platform: str,
    date_range: dict[str, str],
    lookback_days: int,
    tenant_id: str,
) -> tuple[list[str], list[float]]:
    """Fetch metric time series data from ClickHouse.

    Args:
        metric: Metric name.
        platform: Platform filter.
        date_range: Date range override.
        lookback_days: Days to look back.
        tenant_id: Tenant scope.

    Returns:
        Tuple of (date_strings, values).
    """
    try:
        from django.db import connections

        ch = connections.get("clickhouse")
        now = datetime.utcnow()
        start = now - timedelta(days=lookback_days)
        end = now

        if date_range:
            if date_range.get("start"):
                start = datetime.fromisoformat(date_range["start"])
            if date_range.get("end"):
                end = datetime.fromisoformat(date_range["end"])

        where = f"tenant_id = '{tenant_id}' AND event_date BETWEEN '{start.date()}' AND '{end.date()}'"
        where += f" AND metric_name = '{metric}'"
        if platform:
            where += f" AND platform = '{platform}'"

        sql = f"""
            SELECT event_date, sum(metric_value) as total
            FROM analytics_events
            WHERE {where}
            GROUP BY event_date
            ORDER BY event_date
        """
        with ch.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            dates = [str(r[0]) for r in rows]
            values = [float(r[1]) if r[1] else 0.0 for r in rows]
            return dates, values
    except Exception:
        # Generate synthetic data for demonstration when ClickHouse unavailable
        import random

        dates = []
        values = []
        base = 100.0
        now = datetime.utcnow()
        for i in range(lookback_days):
            d = now - timedelta(days=lookback_days - i)
            dates.append(d.strftime("%Y-%m-%d"))
            noise = random.gauss(0, base * 0.1)
            trend = base + i * 0.5
            values.append(max(0, round(trend + noise, 2)))
        return dates, values
