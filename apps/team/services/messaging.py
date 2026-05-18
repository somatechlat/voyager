"""Messaging service — channel management, messaging, and thread handling.

Provides operations for creating channels, sending messages, managing
threads, and extracting mentions from message content.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from apps.team.models import Message, MessageChannel

logger = logging.getLogger(__name__)


class MessagingServiceError(Exception):
    """Raised when a messaging operation fails."""

    pass


class MessagingService:
    """Service layer for messaging operations."""

    # -- Channel operations ------------------------------------------------

    @staticmethod
    def create_channel(
        tenant_id: str,
        name: str,
        channel_type: str = "group",
        participant_ids: list[str] | None = None,
        creator_id: str = "",
    ) -> MessageChannel:
        """Create a new message channel.

        Args:
            tenant_id: Tenant scope identifier.
            name: Channel display name.
            channel_type: 'direct' or 'group'.
            participant_ids: List of participant user IDs.
            creator_id: User ID creating the channel (auto-added).

        Returns:
            The created MessageChannel instance.

        Raises:
            MessagingServiceError: If channel_type is invalid.
        """
        valid_types = [t[0] for t in MessageChannel.ChannelType.choices]
        if channel_type not in valid_types:
            raise MessagingServiceError(
                f"Invalid channel_type '{channel_type}'. Valid: {valid_types}"
            )

        participants = list(participant_ids or [])
        if creator_id and creator_id not in participants:
            participants.append(creator_id)

        if channel_type == "direct" and len(participants) != 2:
            raise MessagingServiceError(
                "Direct channels require exactly 2 participants"
            )

        channel = MessageChannel.objects.create(
            tenant_id=tenant_id,
            name=name,
            channel_type=channel_type,
            participant_ids=participants,
        )
        logger.info(
            "Created channel #%d '%s' (%s) for tenant %s",
            channel.id,
            name,
            channel_type,
            tenant_id,
        )
        return channel

    @staticmethod
    def get_channel(channel_id: int, tenant_id: str) -> MessageChannel:
        """Fetch a channel by ID and tenant.

        Args:
            channel_id: Channel primary key.
            tenant_id: Tenant scope identifier.

        Returns:
            The MessageChannel instance.

        Raises:
            MessagingServiceError: If channel not found.
        """
        try:
            return MessageChannel.objects.get(id=channel_id, tenant_id=tenant_id)
        except MessageChannel.DoesNotExist:
            raise MessagingServiceError(f"Channel {channel_id} not found")

    @staticmethod
    def list_channels(
        tenant_id: str,
        user_id: str | None = None,
        channel_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List channels accessible to a user.

        Args:
            tenant_id: Tenant scope identifier.
            user_id: Filter channels where user is a participant.
            channel_type: Filter by channel type.
            page: Page number.
            page_size: Items per page.

        Returns:
            Dict with items, total, page, page_size.
        """
        qs = MessageChannel.objects.filter(tenant_id=tenant_id)

        if user_id:
            qs = qs.filter(participant_ids__contains=[user_id])
        if channel_type:
            qs = qs.filter(channel_type=channel_type)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("-updated_at")[start:end])

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def update_channel(
        channel_id: int,
        tenant_id: str,
        name: str | None = None,
        participant_ids: list[str] | None = None,
    ) -> MessageChannel:
        """Update a channel.

        Args:
            channel_id: Channel primary key.
            tenant_id: Tenant scope identifier.
            name: New channel name.
            participant_ids: New participant list.

        Returns:
            The updated MessageChannel instance.
        """
        channel = MessagingService.get_channel(channel_id, tenant_id)
        if name is not None:
            channel.name = name
        if participant_ids is not None:
            channel.participant_ids = participant_ids
        channel.save()
        return channel

    @staticmethod
    def add_participant(channel_id: int, tenant_id: str, user_id: str) -> MessageChannel:
        """Add a participant to a channel.

        Args:
            channel_id: Channel primary key.
            tenant_id: Tenant scope identifier.
            user_id: User ID to add.

        Returns:
            The updated MessageChannel instance.
        """
        channel = MessagingService.get_channel(channel_id, tenant_id)
        channel.add_participant(user_id)
        channel.save()
        return channel

    @staticmethod
    def remove_participant(
        channel_id: int, tenant_id: str, user_id: str
    ) -> MessageChannel:
        """Remove a participant from a channel.

        Args:
            channel_id: Channel primary key.
            tenant_id: Tenant scope identifier.
            user_id: User ID to remove.

        Returns:
            The updated MessageChannel instance.
        """
        channel = MessagingService.get_channel(channel_id, tenant_id)
        channel.remove_participant(user_id)
        channel.save()
        return channel

    # -- Message operations ------------------------------------------------

    @staticmethod
    def send_message(
        channel_id: int,
        tenant_id: str,
        author_id: str,
        content: str,
        attachments: list[str] | None = None,
        thread_parent_id: int | None = None,
    ) -> Message:
        """Send a message to a channel.

        Args:
            channel_id: Target channel ID.
            tenant_id: Tenant scope identifier.
            author_id: Sender user ID.
            content: Message text content.
            attachments: Optional attachment references.
            thread_parent_id: Optional parent message for threading.

        Returns:
            The created Message instance.

        Raises:
            MessagingServiceError: If channel not found or user not participant.
        """
        channel = MessagingService.get_channel(channel_id, tenant_id)
        if not channel.has_participant(author_id):
            raise MessagingServiceError(
                f"User {author_id} is not a participant in channel {channel_id}"
            )

        mentions = MessagingService.extract_mentions(content)

        message = Message.objects.create(
            channel=channel,
            author_id=author_id,
            content=content,
            mentions=mentions,
            attachments=attachments or [],
            thread_parent_id=thread_parent_id,
        )

        channel.save()
        logger.info(
            "Message #%d sent to channel #%d by %s", message.id, channel_id, author_id
        )
        return message

    @staticmethod
    def get_message(message_id: int, tenant_id: str) -> Message:
        """Fetch a message by ID with tenant verification.

        Args:
            message_id: Message primary key.
            tenant_id: Tenant scope identifier.

        Returns:
            The Message instance.

        Raises:
            MessagingServiceError: If message not found.
        """
        try:
            return Message.objects.select_related("channel").get(
                id=message_id, channel__tenant_id=tenant_id
            )
        except Message.DoesNotExist:
            raise MessagingServiceError(f"Message {message_id} not found")

    @staticmethod
    def list_messages(
        channel_id: int,
        tenant_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List messages in a channel.

        Args:
            channel_id: Channel primary key.
            tenant_id: Tenant scope identifier.
            page: Page number.
            page_size: Items per page.

        Returns:
            Dict with items, total, page, page_size.
        """
        MessagingService.get_channel(channel_id, tenant_id)
        qs = Message.objects.filter(channel_id=channel_id, thread_parent_id=None)
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("-created_at")[start:end])

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def list_thread_replies(
        message_id: int,
        tenant_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List thread replies to a message.

        Args:
            message_id: Parent message ID.
            tenant_id: Tenant scope identifier.
            page: Page number.
            page_size: Items per page.

        Returns:
            Dict with items, total, page, page_size.
        """
        MessagingService.get_message(message_id, tenant_id)
        qs = Message.objects.filter(thread_parent_id=message_id)
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("created_at")[start:end])

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def reply_to_message(
        message_id: int,
        tenant_id: str,
        author_id: str,
        content: str,
        attachments: list[str] | None = None,
    ) -> Message:
        """Reply to a message in a thread.

        Args:
            message_id: Parent message ID.
            tenant_id: Tenant scope identifier.
            author_id: Reply author user ID.
            content: Reply text content.
            attachments: Optional attachment references.

        Returns:
            The created reply Message instance.
        """
        parent = MessagingService.get_message(message_id, tenant_id)
        return MessagingService.send_message(
            channel_id=parent.channel_id,
            tenant_id=tenant_id,
            author_id=author_id,
            content=content,
            attachments=attachments,
            thread_parent_id=message_id,
        )

    @staticmethod
    def edit_message(
        message_id: int, tenant_id: str, author_id: str, content: str
    ) -> Message:
        """Edit a message. Only the original author can edit.

        Args:
            message_id: Message primary key.
            tenant_id: Tenant scope identifier.
            author_id: User attempting the edit.
            content: New message content.

        Returns:
            The updated Message instance.

        Raises:
            MessagingServiceError: If user is not the author.
        """
        message = MessagingService.get_message(message_id, tenant_id)
        if message.author_id != author_id:
            raise MessagingServiceError("Only the original author can edit a message")
        message.content = content
        message.mentions = MessagingService.extract_mentions(content)
        from django.utils import timezone as tz

        message.edited_at = tz.now()
        message.save()
        return message

    @staticmethod
    def delete_message(message_id: int, tenant_id: str, author_id: str) -> None:
        """Delete a message. Only the original author can delete.

        Args:
            message_id: Message primary key.
            tenant_id: Tenant scope identifier.
            author_id: User attempting deletion.

        Raises:
            MessagingServiceError: If user is not the author.
        """
        message = MessagingService.get_message(message_id, tenant_id)
        if message.author_id != author_id:
            raise MessagingServiceError("Only the original author can delete a message")
        message.delete()

    # -- Mention extraction ------------------------------------------------

    @staticmethod
    def extract_mentions(content: str) -> list[str]:
        """Extract @username mentions from message content.

        Args:
            content: Text content to scan.

        Returns:
            List of mentioned usernames.
        """
        pattern = r"@(\w+)"
        return re.findall(pattern, content)
