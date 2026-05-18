"""Channel and message API endpoints for team collaboration.

Provides CRUD for message channels, sending messages, thread management,
and participant management.
"""

from __future__ import annotations

from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.team.models import Message, MessageChannel
from apps.team.serializers import (
    ChannelCreateSchema,
    ChannelListResponseSchema,
    ChannelSchema,
    ChannelUpdateSchema,
    MessageCreateSchema,
    MessageListResponseSchema,
    MessageSchema,
    ThreadReplySchema,
)
from apps.team.services.messaging import MessagingService, MessagingServiceError

router = Router(auth=VoyagerKeycloakBearer())


def _channel_to_dict(channel: MessageChannel) -> dict[str, Any]:
    """Serialize a MessageChannel to a dict matching ChannelSchema."""
    return {
        "id": channel.id,
        "tenant_id": channel.tenant_id,
        "name": channel.name,
        "channel_type": channel.channel_type,
        "participant_ids": channel.participant_ids or [],
        "created_at": channel.created_at,
        "updated_at": channel.updated_at,
    }


def _message_to_dict(message: Message) -> dict[str, Any]:
    """Serialize a Message to a dict matching MessageSchema."""
    return {
        "id": message.id,
        "channel_id": message.channel_id,
        "author_id": message.author_id,
        "content": message.content,
        "mentions": message.mentions or [],
        "attachments": message.attachments or [],
        "thread_parent_id": message.thread_parent_id,
        "reply_count": message.reply_count(),
        "edited_at": message.edited_at,
        "created_at": message.created_at,
    }


# -- Channel CRUD --------------------------------------------------------


@router.get("", response=ChannelListResponseSchema)
def list_channels(request, channel_type: str | None = None, page: int = 1, page_size: int = 20):
    """List channels for the tenant."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    user_id = getattr(user, "user_id", "")
    try:
        result = MessagingService.list_channels(
            tenant_id=tenant_id,
            user_id=user_id,
            channel_type=channel_type,
            page=page,
            page_size=page_size,
        )
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return {
        "items": [_channel_to_dict(c) for c in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("", response=ChannelSchema)
def create_channel(request, payload: ChannelCreateSchema):
    """Create a new message channel."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    creator_id = getattr(user, "user_id", "")
    try:
        channel = MessagingService.create_channel(
            tenant_id=tenant_id,
            name=payload.name,
            channel_type=payload.channel_type,
            participant_ids=payload.participant_ids,
            creator_id=creator_id,
        )
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return _channel_to_dict(channel)


@router.get("/{channel_id}", response=ChannelSchema)
def get_channel(request, channel_id: int):
    """Get a single channel by ID."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        channel = MessagingService.get_channel(channel_id, tenant_id)
    except MessagingServiceError as exc:
        raise HttpError(404, str(exc))
    return _channel_to_dict(channel)


@router.put("/{channel_id}", response=ChannelSchema)
def update_channel(request, channel_id: int, payload: ChannelUpdateSchema):
    """Update a channel."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        channel = MessagingService.update_channel(
            channel_id,
            tenant_id,
            name=payload.name,
            participant_ids=payload.participant_ids,
        )
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return _channel_to_dict(channel)


@router.delete("/{channel_id}")
def delete_channel(request, channel_id: int):
    """Delete a channel and all its messages."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        channel = MessagingService.get_channel(channel_id, tenant_id)
        channel.delete()
    except MessagingServiceError as exc:
        raise HttpError(404, str(exc))
    return {"success": True, "deleted": channel_id}


# -- Participant management ----------------------------------------------


@router.post("/{channel_id}/participants/{user_id}", response=ChannelSchema)
def add_participant(request, channel_id: int, user_id: str):
    """Add a participant to a channel."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        channel = MessagingService.add_participant(channel_id, tenant_id, user_id)
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return _channel_to_dict(channel)


@router.delete("/{channel_id}/participants/{user_id}", response=ChannelSchema)
def remove_participant(request, channel_id: int, user_id: str):
    """Remove a participant from a channel."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        channel = MessagingService.remove_participant(channel_id, tenant_id, user_id)
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return _channel_to_dict(channel)


# -- Messages ------------------------------------------------------------


@router.get("/{channel_id}/messages", response=MessageListResponseSchema)
def list_messages(request, channel_id: int, page: int = 1, page_size: int = 50):
    """List messages in a channel."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        result = MessagingService.list_messages(channel_id, tenant_id, page, page_size)
    except MessagingServiceError as exc:
        raise HttpError(404, str(exc))
    return {
        "items": [_message_to_dict(m) for m in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("/{channel_id}/messages", response=MessageSchema)
def send_message(request, channel_id: int, payload: MessageCreateSchema):
    """Send a message to a channel."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    author_id = getattr(user, "user_id", "")
    try:
        message = MessagingService.send_message(
            channel_id=channel_id,
            tenant_id=tenant_id,
            author_id=author_id,
            content=payload.content,
            attachments=payload.attachments,
            thread_parent_id=payload.thread_parent_id,
        )
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return _message_to_dict(message)


# -- Thread management ---------------------------------------------------


@router.get("/{channel_id}/messages/{message_id}/replies", response=MessageListResponseSchema)
def list_replies(request, channel_id: int, message_id: int, page: int = 1, page_size: int = 50):
    """List thread replies to a message."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        result = MessagingService.list_thread_replies(message_id, tenant_id, page, page_size)
    except MessagingServiceError as exc:
        raise HttpError(404, str(exc))
    return {
        "items": [_message_to_dict(m) for m in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("/{channel_id}/messages/{message_id}/reply", response=MessageSchema)
def reply_to_message(request, channel_id: int, message_id: int, payload: ThreadReplySchema):
    """Reply to a message in a thread."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    author_id = getattr(user, "user_id", "")
    try:
        message = MessagingService.reply_to_message(
            message_id=message_id,
            tenant_id=tenant_id,
            author_id=author_id,
            content=payload.content,
            attachments=payload.attachments,
        )
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return _message_to_dict(message)


# -- Message editing/deletion --------------------------------------------


@router.put("/{channel_id}/messages/{message_id}", response=MessageSchema)
def edit_message(request, channel_id: int, message_id: int, content: str):
    """Edit a message. Only the original author can edit."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    author_id = getattr(user, "user_id", "")
    try:
        message = MessagingService.edit_message(message_id, tenant_id, author_id, content)
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return _message_to_dict(message)


@router.delete("/{channel_id}/messages/{message_id}")
def delete_message(request, channel_id: int, message_id: int):
    """Delete a message. Only the original author can delete."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    author_id = getattr(user, "user_id", "")
    try:
        MessagingService.delete_message(message_id, tenant_id, author_id)
    except MessagingServiceError as exc:
        raise HttpError(400, str(exc))
    return {"success": True, "deleted": message_id}
