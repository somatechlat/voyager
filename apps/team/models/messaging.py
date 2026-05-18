"""Messaging models: MessageChannel, Message.

Defines channel and message models for team communication with
threading, mentions, and attachment support.
"""

from __future__ import annotations

import re

from django.db import models


class MessageChannel(models.Model):
    """A messaging channel for team communication.

    Channels can be direct (1:1) or group conversations.
    """

    class ChannelType(models.TextChoices):
        """Types of message channels."""

        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(max_length=255, help_text="Channel display name")
    channel_type = models.CharField(
        max_length=20, choices=ChannelType.choices, default=ChannelType.GROUP,
        db_index=True, help_text="Direct (1:1) or group conversation",
    )
    participant_ids = models.JSONField(
        default=list, help_text="List of participant user IDs",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_message_channel"
        verbose_name = "Message Channel"
        verbose_name_plural = "Message Channels"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "channel_type"]),
            models.Index(fields=["tenant_id", "-updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.channel_type})"

    def has_participant(self, user_id: str) -> bool:
        """Check if a user is a participant in this channel."""
        return user_id in (self.participant_ids or [])

    def add_participant(self, user_id: str) -> None:
        """Add a participant to the channel."""
        participants = self.participant_ids or []
        if user_id not in participants:
            participants.append(user_id)
            self.participant_ids = participants

    def remove_participant(self, user_id: str) -> None:
        """Remove a participant from the channel."""
        participants = self.participant_ids or []
        if user_id in participants:
            participants.remove(user_id)
            self.participant_ids = participants


class Message(models.Model):
    """A message sent within a channel.

    Supports threading via thread_parent_id, mentions, and attachments.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    channel = models.ForeignKey(
        MessageChannel, on_delete=models.CASCADE, related_name="messages",
        help_text="Parent channel",
    )
    author_id = models.CharField(
        max_length=128, db_index=True,
        help_text="UUID of the message author",
    )
    content = models.TextField(help_text="Message text content")
    mentions = models.JSONField(
        default=list, blank=True, help_text="List of mentioned user IDs",
    )
    attachments = models.JSONField(
        default=list, blank=True,
        help_text="List of attachment file references",
    )
    thread_parent_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        help_text="ID of parent message for threading",
    )
    edited_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of last edit",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when created",
    )

    class Meta:
        db_table = "voyager_message"
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "-created_at"]),
            models.Index(fields=["thread_parent_id", "-created_at"]),
            models.Index(fields=["author_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Message by {self.author_id}: {preview}"

    def is_thread_reply(self) -> bool:
        """Check if this message is a thread reply."""
        return self.thread_parent_id is not None

    def reply_count(self) -> int:
        """Count replies to this message."""
        return Message.objects.filter(thread_parent_id=self.id).count()

    def extract_mentions(self) -> list[str]:
        """Extract @username mentions from content."""
        pattern = r"@(\w+)"
        return re.findall(pattern, self.content)
