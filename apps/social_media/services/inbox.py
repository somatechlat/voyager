"""Unified inbox service.

Handles message aggregation from all connected platforms, threading,
deduplication, routing rules, and response time tracking.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.social_media.models import InboxMessage

logger = logging.getLogger(__name__)

SPAM_PATTERNS = [
    re.compile(r"follow\s*(me|back|for\s*follow)", re.IGNORECASE),
    re.compile(r"check\s*(out\s*)?(my|our)\s*(bio|profile|link)", re.IGNORECASE),
    re.compile(r"dm\s*(me|us)\s*(for|to)", re.IGNORECASE),
    re.compile(r"(buy|sell|cheap|discount|offer)\s", re.IGNORECASE),
    re.compile(r"(earn|make)\s*\$?\d+", re.IGNORECASE),
    re.compile(r"(winner|congratulations|you('ve)?\s*won)", re.IGNORECASE),
]

URL_RE = re.compile(r"https?://\S+")


class MessageNormalizer:
    """Normalizes raw platform messages into a standard format."""

    @staticmethod
    def normalize_instagram(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize an Instagram message."""
        return {
            "platform": "instagram",
            "platform_message_id": str(raw.get("id", "")),
            "type": _map_instagram_type(raw.get("type", "")),
            "author_name": raw.get("username", ""),
            "author_platform_id": str(raw.get("user_id", "")),
            "author_avatar": raw.get("profile_pic", ""),
            "text": raw.get("text", ""),
            "media_urls": [raw["media_url"]] if raw.get("media_url") else [],
            "parent_id": raw.get("parent_id"),
            "post_id": str(raw.get("media_id", "")),
            "received_at": _parse_ts(raw.get("timestamp")),
        }

    @staticmethod
    def normalize_linkedin(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a LinkedIn message."""
        author = raw.get("author", {})
        created = raw.get("created", {})
        return {
            "platform": "linkedin",
            "platform_message_id": str(raw.get("id", "")),
            "type": _map_linkedin_type(raw.get("type", "")),
            "author_name": author.get("name", ""),
            "author_platform_id": str(author.get("id", "")),
            "author_avatar": author.get("avatar", ""),
            "text": raw.get("message", ""),
            "media_urls": [],
            "parent_id": raw.get("parentCommentId"),
            "post_id": str(raw.get("postId", "")),
            "received_at": _parse_ts(created.get("time")),
        }

    @staticmethod
    def normalize_twitter(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Twitter/X message."""
        return {
            "platform": "twitter",
            "platform_message_id": str(raw.get("id", "")),
            "type": _map_twitter_type(raw.get("type", "")),
            "author_name": raw.get("author_name", ""),
            "author_platform_id": str(raw.get("author_id", "")),
            "author_avatar": raw.get("author_avatar", ""),
            "text": raw.get("text", ""),
            "media_urls": raw.get("media_urls", []),
            "parent_id": raw.get("parent_id"),
            "post_id": str(raw.get("tweet_id", "")),
            "received_at": _parse_ts(raw.get("created_at")),
        }

    @staticmethod
    def normalize_facebook(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Facebook message."""
        return {
            "platform": "facebook",
            "platform_message_id": str(raw.get("id", "")),
            "type": _map_facebook_type(raw.get("type", "")),
            "author_name": raw.get("from", {}).get("name", ""),
            "author_platform_id": str(raw.get("from", {}).get("id", "")),
            "author_avatar": raw.get("from", {}).get("avatar", ""),
            "text": raw.get("message", ""),
            "media_urls": raw.get("attachments", {}).get("data", []),
            "parent_id": raw.get("parent_id"),
            "post_id": str(raw.get("post_id", "")),
            "received_at": _parse_ts(raw.get("created_time")),
        }

    @staticmethod
    def normalize_tiktok(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a TikTok message."""
        return {
            "platform": "tiktok",
            "platform_message_id": str(raw.get("comment_id", "")),
            "type": _map_tiktok_type(raw.get("type", "")),
            "author_name": raw.get("user", {}).get("display_name", ""),
            "author_platform_id": str(raw.get("user", {}).get("user_id", "")),
            "author_avatar": raw.get("user", {}).get("avatar_url", ""),
            "text": raw.get("text", ""),
            "media_urls": [],
            "parent_id": raw.get("parent_comment_id"),
            "post_id": str(raw.get("video_id", "")),
            "received_at": _parse_ts(raw.get("create_time")),
        }


NORMALIZERS: dict[str, Any] = {
    "instagram": MessageNormalizer.normalize_instagram,
    "linkedin": MessageNormalizer.normalize_linkedin,
    "twitter": MessageNormalizer.normalize_twitter,
    "facebook": MessageNormalizer.normalize_facebook,
    "tiktok": MessageNormalizer.normalize_tiktok,
}


def normalize_message(raw: dict[str, Any], platform: str) -> dict[str, Any] | None:
    """Normalize a raw platform message into standard fields.

    :param raw: Raw message payload from the platform API.
    :param platform: Platform name (instagram, linkedin, etc.).
    :returns: Normalized dict or None if platform unsupported.
    """
    normalizer = NORMALIZERS.get(platform)
    if normalizer is None:
        logger.warning("No normalizer for platform: %s", platform)
        return None
    try:
        return normalizer(raw)
    except Exception:
        logger.exception("Failed to normalize message from %s", platform)
        return None


def detect_spam(text: str) -> dict[str, Any]:
    """Score a message for spam indicators.

    :param text: Message body text.
    :returns: Dict with is_spam, confidence, reasons.
    """
    score = 0
    reasons: list[str] = []
    if not text:
        return {"is_spam": False, "confidence": 0.0, "reasons": []}

    for pattern in SPAM_PATTERNS:
        if pattern.search(text):
            score += 30
            reasons.append(f"matched: {pattern.pattern[:40]}")

    if _is_repetitive(text):
        score += 20
        reasons.append("repetitive_text")

    link_count = len(URL_RE.findall(text))
    if link_count > 2:
        score += 25 * link_count
        reasons.append(f"excessive_links: {link_count}")

    if text == text.upper() and len(text) > 20:
        score += 15
        reasons.append("all_caps")

    return {
        "is_spam": score >= 50,
        "confidence": min(score / 100.0, 1.0),
        "reasons": reasons,
    }


def thread_messages(messages: list[InboxMessage]) -> dict[uuid.UUID, list[InboxMessage]]:
    """Group messages into threads by parent/child relationships.

    :param messages: List of InboxMessage objects.
    :returns: Dict mapping thread_id to ordered list of messages.
    """
    threads: dict[uuid.UUID, list[InboxMessage]] = {}
    roots: list[InboxMessage] = []

    for msg in messages:
        if msg.parent_id is not None:
            thread_id = msg.thread_id or msg.parent_id
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(msg)
        else:
            roots.append(msg)

    for root in roots:
        tid = root.thread_id or root.id
        if tid not in threads:
            threads[tid] = []
        threads[tid].insert(0, root)

    return threads


def deduplicate_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove duplicate messages using content hash.

    :param messages: List of normalized message dicts.
    :returns: Deduplicated list preserving order.
    """
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for m in messages:
        key = _message_fingerprint(m)
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


def apply_routing_rules(
    message: dict[str, Any], rules: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Apply auto-assignment routing rules to a message.

    :param message: Normalized message dict.
    :param rules: List of routing rules with conditions.
    :returns: Assignment dict with userId and reason, or None.
    """
    for rule in rules:
        condition = rule.get("condition", {})
        if _matches_condition(message, condition):
            return {
                "userId": rule.get("assigned_to", ""),
                "reason": rule.get("name", "auto-routed"),
            }
    return None


def aggregate_messages(
    tenant_id: str,
    platform_messages: dict[str, list[dict[str, Any]]],
    routing_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate and normalize messages from all platforms.

    :param tenant_id: Tenant scope identifier.
    :param platform_messages: Map of platform -> raw message list.
    :param routing_rules: Optional auto-assignment rules.
    :returns: Aggregation result with counts and stored IDs.
    """
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []

    for platform, raw_list in platform_messages.items():
        for raw in raw_list:
            try:
                norm = normalize_message(raw, platform)
                if norm:
                    norm["tenant_id"] = tenant_id
                    normalized.append(norm)
            except Exception as exc:
                errors.append(f"{platform}: {exc}")
                logger.warning("Failed normalizing message from %s", platform)

    normalized = deduplicate_messages(normalized)

    stored_ids: list[str] = []
    with transaction.atomic():
        for nm in normalized:
            spam_result = detect_spam(nm.get("text", ""))
            nm["spam_score"] = spam_result["confidence"]
            if routing_rules:
                assignment = apply_routing_rules(nm, routing_rules)
                if assignment:
                    nm["assigned_to"] = assignment["userId"]
                    nm["assignment_reason"] = assignment["reason"]
            msg = InboxMessage.objects.create(**nm)
            stored_ids.append(str(msg.id))

    return {
        "stored_count": len(stored_ids),
        "stored_ids": stored_ids,
        "platforms": list(platform_messages.keys()),
        "errors": errors,
    }


def _map_instagram_type(t: str) -> str:
    mapping = {"comment": "comment", "dm": "dm", "mention": "mention"}
    return mapping.get(t, "comment")


def _map_linkedin_type(t: str) -> str:
    mapping = {"comment": "comment", "message": "dm", "mention": "mention"}
    return mapping.get(t, "comment")


def _map_twitter_type(t: str) -> str:
    mapping = {"tweet": "mention", "dm": "dm", "mention": "mention"}
    return mapping.get(t, "mention")


def _map_facebook_type(t: str) -> str:
    mapping = {"comment": "comment", "message": "dm", "mention": "mention"}
    return mapping.get(t, "comment")


def _map_tiktok_type(t: str) -> str:
    mapping = {"comment": "comment", "mention": "mention"}
    return mapping.get(t, "comment")


def _parse_ts(value: Any) -> Any:
    """Parse various timestamp formats."""
    if value is None:
        return timezone.now()
    return value


def _is_repetitive(text: str) -> bool:
    """Check if text has repetitive patterns."""
    if len(text) < 20:
        return False
    words = text.lower().split()
    if not words:
        return False
    unique_ratio = len(set(words)) / len(words)
    return unique_ratio < 0.3


def _message_fingerprint(m: dict[str, Any]) -> str:
    """Generate a content fingerprint for deduplication."""
    content = f"{m.get('platform')}:{m.get('author_name')}:{m.get('text', '')[:200]}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def _matches_condition(message: dict[str, Any], condition: dict[str, Any]) -> bool:
    """Check if a message matches a routing condition."""
    field = condition.get("field", "")
    value = message.get(field, "")
    op = condition.get("operator", "eq")
    target = condition.get("value", "")
    if op == "eq":
        return value == target
    if op == "contains":
        return target in str(value)
    if op == "startswith":
        return str(value).startswith(str(target))
    return False
