"""Comment management views.

Endpoints for comment listing, moderation, spam detection,
replies, and AI response suggestions.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.social_media.models import SocialComment
from apps.social_media.services.comments import (
    AutoModerator,
    SpamDetector,
    bulk_moderate,
    reply_to_comment,
    suggest_response,
)

router = Router(auth=VoyagerKeycloakBearer())


class CommentOut:
    """Output schema for a social comment."""

    id: str
    platform: str
    post_id: str
    author_name: str
    author_avatar: str
    text: str
    sentiment: str
    sentiment_score: float
    spam_score: float
    is_spam: bool
    is_hidden: bool
    moderation_action: str
    reply_text: str
    replied_at: str | None
    like_count: int
    received_at: str
    created_at: str


class ModerateIn:
    """Input schema for moderating a comment."""

    action: str
    reason: str = ""


class ReplyIn:
    """Input schema for replying to a comment."""

    reply_text: str


class BulkModerateIn:
    """Input schema for bulk moderation."""

    ids: list[str]
    action: str
    reason: str = ""


class SuggestIn:
    """Input schema for AI response suggestions."""

    comment_text: str
    brand_tone: str = "professional"


@router.get("/comments", response=list[CommentOut], tags=["SM Comments"])
def list_comments(
    request,
    tenant_id: str = "",
    platform: str = "",
    post_id: str = "",
    is_spam: bool | None = None,
    is_hidden: bool | None = None,
    sentiment: str = "",
    limit: int = 50,
    offset: int = 0,
):
    """List social comments with filters."""
    qs = SocialComment.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    if post_id:
        qs = qs.filter(post_id=post_id)
    if is_spam is not None:
        qs = qs.filter(is_spam=is_spam)
    if is_hidden is not None:
        qs = qs.filter(is_hidden=is_hidden)
    if sentiment:
        qs = qs.filter(sentiment=sentiment)
    qs = qs.order_by("-received_at")[offset : offset + limit]
    return [_comment_to_dict(c) for c in qs]


@router.get("/comments/{comment_id}", response=CommentOut, tags=["SM Comments"])
def get_comment(request, comment_id: str):
    """Get a single comment."""
    comment = get_object_or_404(SocialComment, id=comment_id)
    return _comment_to_dict(comment)


@router.post("/comments/{comment_id}/moderate", response=dict, tags=["SM Comments"])
def moderate_comment(request, comment_id: str, payload: ModerateIn):
    """Moderate a single comment."""
    comment = get_object_or_404(SocialComment, id=comment_id)
    user_id = getattr(request, "user_id", "system")
    result = bulk_moderate([comment_id], payload.action, user_id, payload.reason)
    return result


@router.post("/comments/{comment_id}/reply", response=dict, tags=["SM Comments"])
def reply_to_comment_view(request, comment_id: str, payload: ReplyIn):
    """Reply to a comment."""
    user_id = getattr(request, "user_id", "system")
    return reply_to_comment(comment_id, payload.reply_text, user_id)


@router.post("/comments/bulk-moderate", response=dict, tags=["SM Comments"])
def bulk_moderate_comments(request, payload: BulkModerateIn):
    """Moderate multiple comments."""
    user_id = getattr(request, "user_id", "system")
    return bulk_moderate(payload.ids, payload.action, user_id, payload.reason)


@router.post("/comments/{comment_id}/spam-check", response=dict, tags=["SM Comments"])
def check_spam(request, comment_id: str):
    """Run spam detection on a comment."""
    comment = get_object_or_404(SocialComment, id=comment_id)
    detector = SpamDetector()
    result = detector.detect(comment.text)
    comment.spam_score = result["confidence"]
    comment.is_spam = result["is_spam"]
    comment.spam_reasons = result["reasons"]
    comment.save(update_fields=["spam_score", "is_spam", "spam_reasons"])
    return result


@router.post("/comments/{comment_id}/auto-moderate", response=dict, tags=["SM Comments"])
def auto_moderate(request, comment_id: str):
    """Run auto-moderation rules on a comment."""
    comment = get_object_or_404(SocialComment, id=comment_id)
    moderator = AutoModerator()
    result = moderator.moderate(comment)
    return result


@router.post("/comments/suggest-response", response=dict, tags=["SM Comments"])
def get_response_suggestions(request, payload: SuggestIn):
    """Get AI response suggestions for a comment."""
    suggestions = suggest_response(
        comment_text=payload.comment_text,
        brand_tone=payload.brand_tone,
    )
    return {"suggestions": suggestions}


@router.get("/comments/stats/overview", response=dict, tags=["SM Comments"])
def comment_stats(request, tenant_id: str = ""):
    """Get comment statistics."""
    qs = SocialComment.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return {
        "total": qs.count(),
        "by_sentiment": {
            "positive": qs.filter(sentiment="positive").count(),
            "neutral": qs.filter(sentiment="neutral").count(),
            "negative": qs.filter(sentiment="negative").count(),
        },
        "spam_count": qs.filter(is_spam=True).count(),
        "hidden_count": qs.filter(is_hidden=True).count(),
        "pending_reply": qs.filter(reply_text="", is_spam=False, is_hidden=False).count(),
    }


def _comment_to_dict(c: SocialComment) -> dict[str, Any]:
    """Convert SocialComment to response dict."""
    return {
        "id": str(c.id),
        "platform": c.platform,
        "post_id": c.post_id,
        "author_name": c.author_name,
        "author_avatar": c.author_avatar,
        "text": c.text,
        "sentiment": c.sentiment,
        "sentiment_score": float(c.sentiment_score) if c.sentiment_score else 0,
        "spam_score": float(c.spam_score) if c.spam_score else 0,
        "is_spam": c.is_spam,
        "is_hidden": c.is_hidden,
        "moderation_action": c.moderation_action,
        "reply_text": c.reply_text,
        "replied_at": c.replied_at.isoformat() if c.replied_at else None,
        "like_count": c.like_count,
        "received_at": c.received_at.isoformat(),
        "created_at": c.created_at.isoformat(),
    }
