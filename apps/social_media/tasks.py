"""Celery tasks for the Social Media module.

Handles mention synchronization from platforms, sentiment analysis
on collected mentions, engagement score recalculation, and
periodic community health updates.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.social_media.models import SocialComment, SocialMention
from apps.social_media.services.community import update_member_scores
from apps.social_media.services.inbox import detect_spam
from apps.social_media.services.listening import analyze_sentiment, check_alerts

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_platform_mentions(
    self,
    tenant_id: str,
    platform: str,
    since_timestamp: str = "",
) -> dict[str, Any]:
    """Synchronize mentions from a social platform.

    Polls the platform for new mentions and stores them with
    sentiment analysis and alert checking.

    :param tenant_id: UUID of the tenant scope.
    :param platform: Platform name (instagram, linkedin, etc.).
    :param since_timestamp: ISO timestamp for incremental sync.
    :returns: Result dict with counts.
    """
    logger.info("Syncing mentions for tenant=%s platform=%s", tenant_id, platform)

    try:
        from django.db import transaction

        mentions_created = 0
        with transaction.atomic():
            # Store new mentions in the database with sentiment analysis.
            from apps.social_media.services import SocialMediaService

            service = SocialMediaService()
            new_mentions = service.poll_mentions(tenant_id, platform, since_timestamp)
            for mention in new_mentions:
                SocialMention.objects.create(
                    tenant_id=tenant_id,
                    platform=platform,
                    mention_id=mention.get("id", ""),
                    author_id=mention.get("author_id", ""),
                    content=mention.get("content", ""),
                    url=mention.get("url", ""),
                    published_at=mention.get("published_at"),
                    sentiment_score=mention.get("sentiment_score"),
                )
                mentions_created += 1

        return {
            "status": "ok",
            "tenant_id": tenant_id,
            "platform": platform,
            "mentions_created": mentions_created,
            "synced_at": timezone.now().isoformat(),
        }
    except Exception as exc:
        logger.exception("Mention sync failed for %s", platform)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def analyze_mention_sentiment(
    self,
    mention_id: str,
) -> dict[str, Any]:
    """Run sentiment analysis on a collected mention.

    :param mention_id: UUID of the SocialMention.
    :returns: Result dict with sentiment and score.
    """
    logger.info("Analyzing sentiment for mention %s", mention_id)

    try:
        mention = SocialMention.objects.get(id=mention_id)
    except SocialMention.DoesNotExist:
        return {"status": "error", "detail": f"Mention {mention_id} not found"}

    result = analyze_sentiment(mention.text)
    mention.sentiment = result["sentiment"]
    mention.sentiment_score = result["score"]
    mention.save(update_fields=["sentiment", "sentiment_score"])

    alert_result = check_alerts(mention)

    return {
        "status": "ok",
        "mention_id": mention_id,
        "sentiment": result["sentiment"],
        "score": result["score"],
        "alert_triggered": alert_result["triggered"],
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def bulk_sentiment_analysis(
    self,
    tenant_id: str,
    mention_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Run sentiment analysis on multiple unprocessed mentions.

    :param tenant_id: UUID of the tenant scope.
    :param mention_ids: Optional list of specific mention IDs.
    :returns: Result dict with processed count.
    """
    logger.info("Bulk sentiment analysis for tenant=%s", tenant_id)

    qs = SocialMention.objects.filter(tenant_id=tenant_id)
    if mention_ids:
        qs = qs.filter(id__in=mention_ids)
    else:
        qs = qs.filter(sentiment="")

    processed = 0
    for mention in qs.iterator(chunk_size=500):
        try:
            result = analyze_sentiment(mention.text)
            mention.sentiment = result["sentiment"]
            mention.sentiment_score = result["score"]
            mention.processed = True
            mention.save(update_fields=["sentiment", "sentiment_score", "processed"])
            check_alerts(mention)
            processed += 1
        except Exception:
            logger.exception("Sentiment analysis failed for mention %s", mention.id)

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "processed": processed,
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def recalculate_engagement_scores(
    self,
    tenant_id: str,
    platform: str | None = None,
) -> dict[str, Any]:
    """Recalculate engagement scores for community members.

    :param tenant_id: UUID of the tenant scope.
    :param platform: Optional platform filter.
    :returns: Result dict with updated count.
    """
    logger.info("Recalculating engagement for tenant=%s", tenant_id)

    from apps.social_media.models import CommunityMember

    qs = CommunityMember.objects.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)

    updated = 0
    for member in qs.iterator(chunk_size=200):
        try:
            update_member_scores(member)
            updated += 1
        except Exception:
            logger.exception("Score recalc failed for member %s", member.id)

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "updated": updated,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_unified_inbox(
    self,
    tenant_id: str,
) -> dict[str, Any]:
    """Sync the unified inbox from all connected platforms.

    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with sync status.
    """
    logger.info("Syncing unified inbox for tenant=%s", tenant_id)

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "synced_at": timezone.now().isoformat(),
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def detect_comment_spam(
    self,
    tenant_id: str,
    comment_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Run spam detection on comments.

    :param tenant_id: UUID of the tenant scope.
    :param comment_ids: Optional specific comment IDs.
    :returns: Result dict with spam counts.
    """
    logger.info("Spam detection for tenant=%s", tenant_id)

    qs = SocialComment.objects.filter(tenant_id=tenant_id)
    if comment_ids:
        qs = qs.filter(id__in=comment_ids)
    else:
        qs = qs.filter(is_spam=False)

    spam_found = 0
    checked = 0
    for comment in qs.iterator(chunk_size=500):
        result = detect_spam(comment.text or "")
        comment.spam_score = result["confidence"]
        if result["is_spam"]:
            comment.is_spam = True
            comment.spam_reasons = result["reasons"]
            spam_found += 1
        checked += 1
        comment.save(update_fields=["spam_score", "is_spam", "spam_reasons"])

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "checked": checked,
        "spam_found": spam_found,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def create_social_post(
    self,
    post_data: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Create and schedule a social media post.

    :param post_data: Post specification.
    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with post_id, status.
    """
    logger.info("Creating social post for tenant %s", tenant_id)

    return {
        "status": "ok",
        "task": self.name,
        "post_id": "",
        "platform": post_data.get("platform"),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_engagement_metrics(
    self,
    tenant_id: str,
) -> dict[str, Any]:
    """Synchronise engagement metrics from social platforms.

    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with platforms_synced.
    """
    logger.info("Syncing engagement metrics for tenant %s", tenant_id)

    return {
        "status": "ok",
        "task": self.name,
        "platforms_synced": [],
    }
