"""Comment management service.

Handles spam detection, auto-moderation, AI reply suggestions,
and bulk comment operations across social platforms.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from django.utils import timezone

from apps.social_media.models import SocialComment

logger = logging.getLogger(__name__)

SPAM_PATTERNS = [
    re.compile(r"follow\s*(me|back|for\s*follow)", re.IGNORECASE),
    re.compile(r"check\s*(out\s*)?(my|our)\s*(bio|profile|link)", re.IGNORECASE),
    re.compile(r"dm\s*(me|us)\s*(for|to)", re.IGNORECASE),
    re.compile(r"(buy|sell|cheap|discount|offer)\s", re.IGNORECASE),
    re.compile(r"(earn|make)\s*\$?\d+", re.IGNORECASE),
    re.compile(r"(winner|congratulations|you('ve)?\s*won)", re.IGNORECASE),
    re.compile(r"(click\s*link|limited\s*time|act\s*now)", re.IGNORECASE),
]

PROFANITY_LIST = [
    "spam",
    "scam",
    "fake",
    "bot",
]

URL_RE = re.compile(r"https?://\S+")


class SpamDetector:
    """Rule-based spam detection for social comments."""

    @staticmethod
    def detect(comment_text: str) -> dict[str, Any]:
        """Score a comment for spam indicators.

        :param comment_text: The comment body text.
        :returns: Dict with is_spam, confidence, reasons.
        """
        score = 0
        reasons: list[str] = []
        text = comment_text or ""

        for pattern in SPAM_PATTERNS:
            if pattern.search(text):
                score += 30
                reasons.append(f"spam_pattern: {pattern.pattern[:40]}")

        if _is_repetitive(text):
            score += 20
            reasons.append("repetitive_text")

        link_count = len(URL_RE.findall(text))
        if link_count > 2:
            score += 25 * link_count
            reasons.append(f"excessive_links:{link_count}")

        if text == text.upper() and len(text) > 20:
            score += 15
            reasons.append("all_caps")

        word_count = len(text.split())
        if word_count > 0:
            for word in PROFANITY_LIST:
                if word in text.lower():
                    score += 10
                    reasons.append(f"profanity:{word}")

        return {
            "is_spam": score >= 50,
            "confidence": round(min(score / 100.0, 1.0), 2),
            "reasons": reasons,
        }


class AutoModerator:
    """Applies auto-moderation rules to comments."""

    DEFAULT_RULES = [
        {
            "name": "Hide spam",
            "condition": {"field": "spam_score", "operator": "gte", "value": 0.7},
            "action": "hide",
            "notify": False,
        },
        {
            "name": "Flag profanity",
            "condition": {"field": "text", "operator": "contains_profanity"},
            "action": "hide",
            "notify": True,
        },
        {
            "name": "Flag negative sentiment",
            "condition": {
                "field": "sentiment_score",
                "operator": "lt",
                "value": -0.5,
            },
            "action": "flag",
            "notify": True,
        },
    ]

    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        """Initialize with optional custom rules."""
        self.rules = rules or self.DEFAULT_RULES

    def moderate(self, comment: SocialComment) -> dict[str, Any]:
        """Apply moderation rules to a comment.

        :param comment: SocialComment instance.
        :returns: Action taken dict with action, notify.
        """
        for rule in self.rules:
            if self._matches(comment, rule.get("condition", {})):
                action = rule.get("action", "none")
                if action == "hide":
                    comment.is_hidden = True
                    comment.hidden_reason = rule["name"]
                comment.moderation_action = action
                comment.save(update_fields=["is_hidden", "hidden_reason", "moderation_action"])
                return {
                    "action": action,
                    "rule": rule["name"],
                    "notify": rule.get("notify", False),
                }
        return {"action": "none", "rule": None, "notify": False}

    @staticmethod
    def _matches(comment: SocialComment, condition: dict[str, Any]) -> bool:
        """Check if a comment matches a moderation condition."""
        field = condition.get("field", "")
        op = condition.get("operator", "eq")
        target = condition.get("value")
        value: Any = None
        if hasattr(comment, field):
            value = getattr(comment, field)
        if op == "gte":
            return isinstance(value, (int, float)) and value >= target
        if op == "lt":
            return isinstance(value, (int, float)) and value < target
        if op == "contains_profanity":
            return _contains_profanity(str(value or ""))
        if op == "eq":
            return value == target
        return False


def bulk_moderate(
    comment_ids: list[str],
    action: str,
    user_id: str,
    reason: str = "",
) -> dict[str, Any]:
    """Apply a moderation action to multiple comments.

    :param comment_ids: List of comment UUIDs.
    :param action: Moderation action — hide, delete, flag, none.
    :param user_id: User performing the action.
    :param reason: Reason for moderation.
    :returns: Result dict with processed count.
    """
    updated = 0
    comments = SocialComment.objects.filter(id__in=comment_ids)
    now = timezone.now()

    for comment in comments:
        comment.moderation_action = action
        comment.moderated_by = user_id
        comment.moderated_at = now
        if action == "hide":
            comment.is_hidden = True
            comment.hidden_reason = reason or "bulk hide"
        elif action == "none":
            comment.is_hidden = False
            comment.hidden_reason = ""
        comment.save(
            update_fields=[
                "moderation_action",
                "moderated_by",
                "moderated_at",
                "is_hidden",
                "hidden_reason",
            ]
        )
        updated += 1

    return {"processed": updated, "action": action}


def reply_to_comment(
    comment_id: str,
    reply_text: str,
    user_id: str,
) -> dict[str, Any]:
    """Record a reply to a social comment.

    :param comment_id: UUID of the comment being replied to.
    :param reply_text: The reply text.
    :param user_id: User sending the reply.
    :returns: Result dict with status.
    """
    try:
        comment = SocialComment.objects.get(id=comment_id)
    except SocialComment.DoesNotExist:
        return {"status": "error", "detail": "Comment not found"}

    now = timezone.now()
    comment.reply_text = reply_text
    comment.replied_by = user_id
    comment.replied_at = now
    comment.save(update_fields=["reply_text", "replied_by", "replied_at"])

    return {
        "status": "ok",
        "comment_id": comment_id,
        "replied_at": now.isoformat(),
    }


def suggest_response(
    comment_text: str,
    brand_tone: str = "professional",
    conversation_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate AI response suggestions for a comment.

    :param comment_text: The incoming comment text.
    :param brand_tone: Brand tone descriptor.
    :param conversation_history: Previous messages for context.
    :returns: List of suggestion dicts with text, tone, confidence.
    """
    suggestions: list[dict[str, Any]] = []
    tones = ["helpful", "empathetic", "professional"]

    templates: dict[str, dict[str, str]] = {
        "helpful": (
            "Thanks for reaching out! We'd be happy to help. "
            "Could you share a bit more detail so we can assist you best?"
        ),
        "empathetic": (
            "We really appreciate you taking the time to share this with us. "
            "Your feedback matters, and we're here to listen."
        ),
        "professional": (
            "Thank you for your message. Our team will review and "
            "get back to you as soon as possible."
        ),
    }

    for tone in tones:
        response = templates.get(tone, templates["professional"])
        confidence = _calculate_relevance(response, comment_text, tone, brand_tone)
        suggestions.append(
            {
                "text": response,
                "tone": tone,
                "confidence": round(confidence, 2),
            }
        )

    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    return suggestions


def _is_repetitive(text: str) -> bool:
    """Check if text has repetitive patterns."""
    if len(text) < 20:
        return False
    words = text.lower().split()
    if not words:
        return False
    return len(set(words)) / len(words) < 0.3


def _contains_profanity(text: str) -> bool:
    """Check if text contains profanity."""
    lowered = text.lower()
    return any(word in lowered for word in PROFANITY_LIST)


def _calculate_relevance(response: str, comment: str, tone: str, brand_tone: str) -> float:
    """Score how relevant a response is to a comment.

    :param response: Suggested response text.
    :param comment: Incoming comment text.
    :param tone: Response tone.
    :param brand_tone: Brand tone preference.
    :returns: Relevance score 0.0 to 1.0.
    """
    score = 0.5
    if tone == brand_tone:
        score += 0.2
    comment_lower = comment.lower()
    response_lower = response.lower()
    common = set(comment_lower.split()) & set(response_lower.split())
    if common:
        score += min(len(common) * 0.05, 0.2)
    return min(score, 1.0)
