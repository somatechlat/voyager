"""Audience segmentation service with dynamic rules and RFM scoring.

Handles dynamic segment evaluation, RFM score calculation,
predictive segmentation, and segment count refresh.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from django.db.models import Q

from apps.email_marketing.models.segment import AudienceSegment
from apps.email_marketing.models.subscriber import EmailSubscriber


def evaluate_dynamic_segment(
    segment: AudienceSegment,
    limit: int | None = None,
) -> list[int]:
    """Evaluate a dynamic segment's rules against active subscribers.

    Supports field-based filters on subscriber data including
    tags, engagement scores, dates, custom fields, and RFM scores.

    Args:
        segment: The audience segment with rules.
        limit: Max results to return.

    Returns:
        List of matching subscriber IDs.
    """
    rules = segment.rules or {}
    filters = rules.get("filters", [])
    match_type = rules.get("match_type", "all")
    queryset = EmailSubscriber.objects.filter(
        tenant_id=segment.tenant_id,
        status=EmailSubscriber.Status.ACTIVE,
    )
    q_objects = []
    for filt in filters:
        q = _build_filter_q(filt)
        if q:
            q_objects.append(q)
    if q_objects:
        if match_type == "all":
            for q in q_objects:
                queryset = queryset.filter(q)
        else:
            combined = q_objects[0]
            for q in q_objects[1:]:
                combined |= q
            queryset = queryset.filter(combined)
    if segment.rfm_enabled:
        queryset = _apply_rfm_filter(queryset, segment.rfm_config)
    if limit:
        queryset = queryset[:limit]
    return list(queryset.values_list("id", flat=True))


def _build_filter_q(filt: dict[str, Any]) -> Q | None:
    """Build a Django Q object from a filter dict.

    Args:
        filt: Filter with field, operator, value keys.

    Returns:
        Q object or None.
    """
    field = filt.get("field", "")
    operator = filt.get("operator", "eq")
    value = filt.get("value")
    if not field:
        return None
    if field == "tags":
        if operator == "contains":
            return Q(tags__contains=[value])
        if operator == "not_contains":
            return ~Q(tags__contains=[value])
    if field == "engagement_score":
        return _build_numeric_q("engagement_score", operator, value)
    if field == "status":
        return Q(status=value) if operator == "eq" else ~Q(status=value)
    if field == "source":
        return Q(source=value) if operator == "eq" else ~Q(source=value)
    if field == "subscribed_at":
        return _build_date_q("subscribed_at", operator, value)
    if field == "open_count":
        return _build_numeric_q("open_count", operator, value)
    if field == "click_count":
        return _build_numeric_q("click_count", operator, value)
    if field.startswith("custom_fields."):
        key = field.replace("custom_fields.", "")
        return Q(custom_fields__contains={key: value})
    return None


def _build_numeric_q(field: str, operator: str, value: Any) -> Q:
    """Build a Q object for numeric field comparison.

    Args:
        field: Model field name.
        operator: Comparison operator.
        value: Comparison value.

    Returns:
        Django Q object.
    """
    if operator == "eq":
        return Q(**{field: value})
    if operator == "gt":
        return Q(**{f"{field}__gt": value})
    if operator == "gte":
        return Q(**{f"{field}__gte": value})
    if operator == "lt":
        return Q(**{f"{field}__lt": value})
    if operator == "lte":
        return Q(**{f"{field}__lte": value})
    if operator == "between":
        low, high = value if isinstance(value, (list, tuple)) else (0, value)
        return Q(**{f"{field}__gte": low, f"{field}__lte": high})
    return Q(**{field: value})


def _build_date_q(field: str, operator: str, value: Any) -> Q:
    """Build a Q object for date field comparison.

    Args:
        field: Model field name.
        operator: Comparison operator.
        value: Date string or relative value.

    Returns:
        Django Q object.
    """
    now = datetime.now(UTC)
    if isinstance(value, str) and value.endswith("_days_ago"):
        days = int(value.split("_")[0])
        dt = now - timedelta(days=days)
        return Q(**{f"{field}__lte": dt})
    if operator == "before":
        return Q(**{f"{field}__lt": value})
    if operator == "after":
        return Q(**{f"{field}__gt": value})
    if operator == "within_days":
        dt = now - timedelta(days=int(value))
        return Q(**{f"{field}__gte": dt})
    return Q(**{field: value})


def _apply_rfm_filter(
    queryset: Any,
    rfm_config: dict[str, Any],
) -> Any:
    """Apply RFM score filtering to a queryset.

    Args:
        queryset: Django queryset.
        rfm_config: RFM thresholds and scoring config.

    Returns:
        Filtered queryset.
    """
    if not rfm_config:
        return queryset
    r_min = rfm_config.get("recency_min")
    r_max = rfm_config.get("recency_max")
    f_min = rfm_config.get("frequency_min")
    f_max = rfm_config.get("frequency_max")
    m_min = rfm_config.get("monetary_min")
    m_max = rfm_config.get("monetary_max")
    if r_min is not None:
        queryset = queryset.filter(rfm_recency__gte=r_min)
    if r_max is not None:
        queryset = queryset.filter(rfm_recency__lte=r_max)
    if f_min is not None:
        queryset = queryset.filter(rfm_frequency__gte=f_min)
    if f_max is not None:
        queryset = queryset.filter(rfm_frequency__lte=f_max)
    if m_min is not None:
        queryset = queryset.filter(rfm_monetary__gte=m_min)
    if m_max is not None:
        queryset = queryset.filter(rfm_monetary__lte=m_max)
    return queryset


def calculate_rfm_scores(subscriber: EmailSubscriber) -> dict[str, int]:
    """Calculate individual RFM scores for a subscriber.

    Scores range from 1-5 for each dimension.

    Args:
        subscriber: The email subscriber.

    Returns:
        Dict with r, f, m scores.
    """
    r = min(5, max(1, 6 - (subscriber.rfm_recency // 30)))
    f = min(5, max(1, 1 + subscriber.rfm_frequency // 5))
    m = min(5, max(1, 1 + int(subscriber.rfm_monetary) // 100))
    return {"recency": r, "frequency": f, "monetary": m, "combined": f"{r}{f}{m}"}


def evaluate_predictive_segment(
    segment: AudienceSegment,
    subscribers: list[EmailSubscriber] | None = None,
) -> list[int]:
    """Evaluate a predictive segment using heuristics.

    Uses engagement-based heuristics as a stand-in for ML models.
    In production, this integrates with a model serving system.

    Args:
        segment: The predictive segment.
        subscribers: Optional pre-filtered subscriber list.

    Returns:
        List of matching subscriber IDs.
    """
    if subscribers is None:
        subscribers = list(
            EmailSubscriber.objects.filter(
                tenant_id=segment.tenant_id,
                status=EmailSubscriber.Status.ACTIVE,
            )
        )
    ptype = segment.predictive_type
    matching_ids: list[int] = []
    if ptype == AudienceSegment.PredictiveType.CHURN_RISK:
        for sub in subscribers:
            score = float(sub.engagement_score)
            recency_days = sub.rfm_recency
            if score < 30 and recency_days > 60:
                matching_ids.append(sub.id)
    elif ptype == AudienceSegment.PredictiveType.HIGH_LTV:
        sorted_subs = sorted(
            subscribers,
            key=lambda s: float(s.rfm_monetary),
            reverse=True,
        )
        top_count = max(1, len(sorted_subs) // 10)
        matching_ids = [s.id for s in sorted_subs[:top_count]]
    elif ptype == AudienceSegment.PredictiveType.ENGAGEMENT_PROPENSITY:
        for sub in subscribers:
            score = float(sub.engagement_score)
            freq = sub.rfm_frequency
            if score > 70 and freq > 3:
                matching_ids.append(sub.id)
    return matching_ids


def refresh_segment_count(segment: AudienceSegment) -> int:
    """Recalculate and cache the subscriber count for a segment.

    Args:
        segment: The audience segment.

    Returns:
        Updated subscriber count.
    """
    if segment.segment_type == AudienceSegment.Type.STATIC:
        subscriber_ids = segment.rules.get("subscriber_ids", [])
        count = EmailSubscriber.objects.filter(
            tenant_id=segment.tenant_id,
            id__in=subscriber_ids,
            status=EmailSubscriber.Status.ACTIVE,
        ).count()
    elif segment.segment_type == AudienceSegment.Type.DYNAMIC:
        ids = evaluate_dynamic_segment(segment)
        count = len(ids)
    elif segment.segment_type == AudienceSegment.Type.BEHAVIORAL:
        ids = evaluate_dynamic_segment(segment)
        count = len(ids)
    elif segment.segment_type == AudienceSegment.Type.PREDICTIVE:
        ids = evaluate_predictive_segment(segment)
        count = len(ids)
    else:
        count = 0
    segment.subscriber_count = count
    segment.last_calculated = datetime.now(UTC)
    segment.save(update_fields=["subscriber_count", "last_calculated"])
    return count
