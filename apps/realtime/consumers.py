"""WebSocket consumers for real-time communication.

Provides three consumer classes:

* :class:`NotificationConsumer` — Push notifications to authenticated users.
* :class:`TaskProgressConsumer` — Live progress updates for Celery tasks.
* :class:`SocialFeedConsumer` — Real-time social media feed aggregation.

All consumers extend :class:`AsyncJsonWebsocketConsumer` and use
channel-layer groups for broadcast semantics.
"""

from __future__ import annotations

import logging
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Real-time notifications for authenticated users.

    Routes:
        * Connects to ``ws/notifications/``.
        * Joins the per-user group ``notifications_<user_id>``.
        * Broadcast notifications are sent via ``send_notification``.

    Expected message format (outbound):
        .. code-block:: json

            {
                "type": "notification",
                "level": "info",
                "title": "Post published",
                "message": "Your post has been published successfully.",
                "link": "/posts/123",
                "timestamp": "2026-05-18T12:00:00Z"
            }
    """

    group_name: str | None = None

    async def connect(self) -> None:
        """Accept connection and join user-specific notification group."""
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4001)
            return

        await self.accept()
        self.group_name = f"notifications_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        logger.debug("NotificationConsumer connected: user=%s", user.id)

    async def disconnect(self, close_code: int) -> None:
        """Leave the notification group on disconnect."""
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("NotificationConsumer disconnected: code=%s", close_code)

    async def receive_json(self, content: dict[str, Any]) -> None:
        """Handle incoming JSON messages from the client.

        Clients may send ``{"action": "mark_read", "notification_id": "..."}``
        to acknowledge notifications.
        """
        action = content.get("action")
        if action == "mark_read":
            notification_id = content.get("notification_id")
            logger.info("Notification marked read: %s", notification_id)
            await self.send_json({"type": "ack", "notification_id": notification_id})
        else:
            await self.send_json({"type": "error", "detail": f"Unknown action: {action}"})

    async def send_notification(self, event: dict[str, Any]) -> None:
        """Handler for channel-layer ``notification`` type messages.

        Called automatically when a message is broadcast to the group
        with ``{"type": "send.notification", ...}``.
        """
        await self.send_json(event)


class TaskProgressConsumer(AsyncJsonWebsocketConsumer):
    """Real-time task progress updates via WebSocket.

    Routes:
        * Connects to ``ws/progress/``.
        * Joins the per-task group ``progress_<task_id>`` or
          the broadcast group ``progress_all``.

    Expected message format (outbound):
        .. code-block:: json

            {
                "type": "progress",
                "task_id": "abc-123",
                "task_name": "apps.publishing.tasks.publish_due_posts",
                "percent": 45,
                "status": "running",
                "current_step": "Uploading image to CDN",
                "eta_seconds": 12
            }
    """

    group_name: str | None = None

    async def connect(self) -> None:
        """Accept connection and join the global progress group."""
        await self.accept()
        self.group_name = "progress_all"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # If client specifies a task_id in query string, also join that group.
        task_id: str | None = (
            self.scope["query_string"].decode().get("task_id")
            if hasattr(self.scope["query_string"], "get")
            else None
        )
        if task_id:
            await self.channel_layer.group_add(f"progress_{task_id}", self.channel_name)

        logger.debug("TaskProgressConsumer connected")

    async def disconnect(self, close_code: int) -> None:
        """Leave all progress groups on disconnect."""
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("TaskProgressConsumer disconnected: code=%s", close_code)

    async def receive_json(self, content: dict[str, Any]) -> None:
        """Handle incoming client messages.

        Clients may subscribe to specific tasks by sending::

            {"action": "subscribe", "task_id": "..."}
        """
        action = content.get("action")
        if action == "subscribe":
            task_id = content.get("task_id")
            if task_id:
                await self.channel_layer.group_add(f"progress_{task_id}", self.channel_name)
                await self.send_json({"type": "subscribed", "task_id": task_id})
        elif action == "unsubscribe":
            task_id = content.get("task_id")
            if task_id:
                await self.channel_layer.group_discard(f"progress_{task_id}", self.channel_name)
                await self.send_json({"type": "unsubscribed", "task_id": task_id})

    async def send_progress(self, event: dict[str, Any]) -> None:
        """Handler for channel-layer ``send.progress`` type messages."""
        await self.send_json(event)


class SocialFeedConsumer(AsyncJsonWebsocketConsumer):
    """Real-time social media feed WebSocket consumer.

    Aggregates live updates from connected social platforms and pushes
    them to subscribed clients.

    Routes:
        * Connects to ``ws/social/``.
        * Joins groups based on the platforms the user wants to follow
          (e.g. ``social_twitter``, ``social_linkedin``).

    Expected message format (outbound):
        .. code-block:: json

            {
                "type": "social_post",
                "platform": "twitter",
                "post_id": "1798765432109876543",
                "author": "@handle",
                "content": "Check out our new product!",
                "engagement": {"likes": 42, "shares": 7},
                "timestamp": "2026-05-18T12:00:00Z"
            }
    """

    groups: list[str]

    async def connect(self) -> None:
        """Accept connection and join default social groups."""
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4001)
            return

        await self.accept()
        self.groups = ["social_all"]
        for group in self.groups:
            await self.channel_layer.group_add(group, self.channel_name)

        logger.debug("SocialFeedConsumer connected: user=%s", user.id)

    async def disconnect(self, close_code: int) -> None:
        """Leave all social feed groups on disconnect."""
        for group in getattr(self, "groups", []):
            await self.channel_layer.group_discard(group, self.channel_name)
        logger.debug("SocialFeedConsumer disconnected: code=%s", close_code)

    async def receive_json(self, content: dict[str, Any]) -> None:
        """Handle incoming client messages.

        Clients may filter the feed by platform::

            {"action": "filter", "platforms": ["twitter", "linkedin"]}
        """
        action = content.get("action")
        if action == "filter":
            platforms = content.get("platforms", [])
            # Leave existing groups and join platform-specific ones.
            for group in getattr(self, "groups", []):
                await self.channel_layer.group_discard(group, self.channel_name)
            self.groups = [f"social_{p}" for p in platforms]
            for group in self.groups:
                await self.channel_layer.group_add(group, self.channel_name)
            await self.send_json({"type": "filtered", "platforms": platforms})

    async def social_post(self, event: dict[str, Any]) -> None:
        """Handler for channel-layer ``social.post`` type messages."""
        await self.send_json(event)
