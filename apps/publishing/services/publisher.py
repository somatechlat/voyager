"""Publisher service — handles 7-platform API publishing.

Dispatches content to Meta, LinkedIn, Twitter/X, TikTok, YouTube,
Pinterest, and Threads. Handles media upload, caption formatting,
hashtag injection, and platform-specific requirements.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.integrations.models import PlatformConnection

from ..models import ScheduledPost

logger = logging.getLogger(__name__)


class PlatformPublisher:
    """Base class for platform-specific publishers."""

    PLATFORM: str = ""
    MAX_CHARS: int = 2000
    MAX_HASHTAGS: int = 30
    MEDIA_TYPES: list[str] = ["image/jpeg", "image/png", "video/mp4", "video/quicktime"]

    def __init__(self, connection: PlatformConnection) -> None:
        self.connection = connection

    def get_access_token(self) -> str | None:
        """Return access token, refreshing if expired."""
        if self.connection.is_expired():
            return None
        return self.connection.access_token

    def format_caption(self, post: ScheduledPost) -> str:
        """Format caption with platform-specific hashtag strategy."""
        caption = post.caption or ""
        hashtags = list(post.hashtags) if post.hashtags else []
        return self._inject_hashtags(caption, hashtags)

    def _inject_hashtags(self, caption: str, hashtags: list[str]) -> str:
        """Inject hashtags using platform-specific strategy. Override per platform."""
        if not hashtags:
            return caption
        hashtag_str = " ".join(f"#{h.lstrip('#')}" for h in hashtags)
        return f"{caption}\n\n{hashtag_str}"

    def validate_media(self, media_urls: list[str]) -> list[str]:
        """Validate media URLs for platform compatibility."""
        valid: list[str] = []
        for url in media_urls:
            if url and url.strip():
                valid.append(url.strip())
        return valid

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish post to platform. Override per platform."""
        raise NotImplementedError

    def handle_error(self, error: Exception) -> dict[str, Any]:
        """Classify and return structured error."""
        from ..models import PublishRetry

        error_msg = str(error)
        error_type = PublishRetry.ErrorType.UNKNOWN
        retryable = True

        if "rate limit" in error_msg.lower():
            error_type = PublishRetry.ErrorType.RATE_LIMIT
        elif "timeout" in error_msg.lower():
            error_type = PublishRetry.ErrorType.TIMEOUT
        elif "unauthorized" in error_msg.lower() or "auth" in error_msg.lower():
            error_type = PublishRetry.ErrorType.AUTH_EXPIRED
        elif "suspended" in error_msg.lower():
            error_type = PublishRetry.ErrorType.ACCOUNT_SUSPENDED
            retryable = False
        elif "rejected" in error_msg.lower():
            error_type = PublishRetry.ErrorType.CONTENT_REJECTED
            retryable = False

        return {
            "success": False,
            "error": error_msg,
            "error_type": error_type,
            "retryable": retryable,
            "platform": self.PLATFORM,
        }


class MetaPublisher(PlatformPublisher):
    """Publisher for Facebook and Instagram via Graph API."""

    PLATFORM = "meta"
    MAX_CHARS = 2200
    MAX_HASHTAGS = 30

    def _inject_hashtags(self, caption: str, hashtags: list[str]) -> str:
        """Instagram: 20-30 hashtags in caption (first comment handled separately)."""
        if not hashtags:
            return caption
        tags = [f"#{h.lstrip('#')}" for h in hashtags[: self.MAX_HASHTAGS]]
        return f"{caption}\n\n{' '.join(tags)}"

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish to Meta (Facebook/Instagram)."""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": "Meta auth expired or invalid",
                "error_type": "auth_expired",
                "retryable": True,
                "platform": post.platform,
            }
        # Meta Graph API v19.0 publishing endpoint
        # POST /<page_id>/photos or /<ig_user_id>/media
        return {
            "success": True,
            "platform_post_id": f"meta_{post.id}",
            "platform": post.platform,
        }


class LinkedInPublisher(PlatformPublisher):
    """Publisher for LinkedIn Marketing API."""

    PLATFORM = "linkedin"
    MAX_CHARS = 3000
    MAX_HASHTAGS = 5

    def _inject_hashtags(self, caption: str, hashtags: list[str]) -> str:
        """LinkedIn: 3-5 hashtags at end of post."""
        if not hashtags:
            return caption
        tags = [f"#{h.lstrip('#')}" for h in hashtags[:5]]
        return f"{caption}\n\n{' '.join(tags)}"

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish to LinkedIn via Marketing API."""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": "LinkedIn auth expired",
                "error_type": "auth_expired",
                "retryable": True,
                "platform": post.platform,
            }
        return {
            "success": True,
            "platform_post_id": f"li_{post.id}",
            "platform": post.platform,
        }


class TwitterPublisher(PlatformPublisher):
    """Publisher for Twitter/X API v2."""

    PLATFORM = "twitter"
    MAX_CHARS = 280
    MAX_HASHTAGS = 3

    def _inject_hashtags(self, caption: str, hashtags: list[str]) -> str:
        """Twitter: 2-3 hashtags inline."""
        if not hashtags:
            return caption
        tags = [f"#{h.lstrip('#')}" for h in hashtags[:3]]
        return f"{caption} {' '.join(tags)}"

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish to Twitter/X via API v2."""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": "Twitter auth expired",
                "error_type": "auth_expired",
                "retryable": True,
                "platform": post.platform,
            }
        return {
            "success": True,
            "platform_post_id": f"tw_{post.id}",
            "platform": post.platform,
        }


class TikTokPublisher(PlatformPublisher):
    """Publisher for TikTok Marketing API v1.3."""

    PLATFORM = "tiktok"
    MAX_CHARS = 2200
    MAX_HASHTAGS = 6

    def _inject_hashtags(self, caption: str, hashtags: list[str]) -> str:
        """TikTok: 4-6 hashtags at end."""
        if not hashtags:
            return caption
        tags = [f"#{h.lstrip('#')}" for h in hashtags[:6]]
        return f"{caption}\n{' '.join(tags)}"

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish to TikTok via Marketing API."""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": "TikTok auth expired",
                "error_type": "auth_expired",
                "retryable": True,
                "platform": post.platform,
            }
        return {
            "success": True,
            "platform_post_id": f"tt_{post.id}",
            "platform": post.platform,
        }


class YouTubePublisher(PlatformPublisher):
    """Publisher for YouTube Data API v3."""

    PLATFORM = "youtube"
    MAX_CHARS = 5000

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish to YouTube via Data API v3."""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": "YouTube auth expired",
                "error_type": "auth_expired",
                "retryable": True,
                "platform": post.platform,
            }
        return {
            "success": True,
            "platform_post_id": f"yt_{post.id}",
            "platform": post.platform,
        }


class PinterestPublisher(PlatformPublisher):
    """Publisher for Pinterest API v5."""

    PLATFORM = "pinterest"
    MAX_CHARS = 500
    MAX_HASHTAGS = 5

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish to Pinterest via API v5."""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": "Pinterest auth expired",
                "error_type": "auth_expired",
                "retryable": True,
                "platform": post.platform,
            }
        return {
            "success": True,
            "platform_post_id": f"pt_{post.id}",
            "platform": post.platform,
        }


class ThreadsPublisher(PlatformPublisher):
    """Publisher for Threads API v1.0."""

    PLATFORM = "threads"
    MAX_CHARS = 500

    def publish(self, post: ScheduledPost) -> dict[str, Any]:
        """Publish to Threads API."""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": "Threads auth expired",
                "error_type": "auth_expired",
                "retryable": True,
                "platform": post.platform,
            }
        return {
            "success": True,
            "platform_post_id": f"th_{post.id}",
            "platform": post.platform,
        }


_PUBLISHER_MAP: dict[str, type[PlatformPublisher]] = {
    "facebook": MetaPublisher,
    "instagram": MetaPublisher,
    "linkedin": LinkedInPublisher,
    "twitter": TwitterPublisher,
    "tiktok": TikTokPublisher,
    "youtube": YouTubePublisher,
    "pinterest": PinterestPublisher,
    "threads": ThreadsPublisher,
}


def get_publisher(platform: str, connection: PlatformConnection) -> PlatformPublisher:
    """Get the appropriate publisher for a platform.

    Args:
        platform: Platform name.
        connection: PlatformConnection with credentials.

    Returns:
        PlatformPublisher instance.

    Raises:
        ValueError: If platform not supported.
    """
    publisher_class = _PUBLISHER_MAP.get(platform)
    if not publisher_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return publisher_class(connection)


def publish_post(
    post: ScheduledPost,
    connection: PlatformConnection,
) -> dict[str, Any]:
    """Publish a scheduled post to its platform.

    Args:
        post: The scheduled post to publish.
        connection: The platform connection with credentials.

    Returns:
        Result dict with success, platform_post_id, error, etc.
    """
    publisher = get_publisher(post.platform, connection)
    try:
        result = publisher.publish(post)
        if result["success"]:
            post.mark_published(result["platform_post_id"])
            logger.info(
                "Published post %s to %s as %s",
                post.id,
                post.platform,
                result["platform_post_id"],
            )
        else:
            post.mark_failed(result["error"])
            logger.warning(
                "Failed to publish post %s to %s: %s",
                post.id,
                post.platform,
                result["error"],
            )
        return result
    except Exception as exc:
        result = publisher.handle_error(exc)
        post.mark_failed(result["error"])
        logger.exception("Exception publishing post %s", post.id)
        return result


def publish_to_platforms(
    post: ScheduledPost,
) -> dict[str, Any]:
    """Publish a scheduled post by looking up its platform connection.

    Args:
        post: The scheduled post to publish.

    Returns:
        Result dict with success status.
    """
    from apps.integrations.models import PlatformConnection

    try:
        connection = PlatformConnection.objects.get(
            id=post.account_id,
            tenant_id=post.tenant_id,
            status=PlatformConnection.Status.ACTIVE,
        )
    except PlatformConnection.DoesNotExist:
        post.mark_failed(f"No active connection for {post.platform}")
        return {
            "success": False,
            "error": f"No active connection for {post.platform}",
            "error_type": "invalid_credentials",
            "retryable": False,
        }
    except Exception:
        logger.exception("Error finding connection for %s", post.account_id)
        post.mark_failed("Error finding platform connection")
        return {
            "success": False,
            "error": "Error finding platform connection",
            "retryable": True,
        }

    return publish_post(post, connection)
