"""Django Admin for Publishing app.

Registers ScheduledPost, PublishQueue, ContentCalendar,
RecurringPost, and ApprovalWorkflow models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.publishing.models import (
    ApprovalWorkflow,
    BlackoutWindow,
    ContentCalendar,
    PublishQueue,
    RecurringPost,
    ScheduledPost,
)


class _JSONMixin:
    """Mixin for formatting JSON fields."""

    @staticmethod
    def _format_json(value: object, max_len: int = 200) -> str:
        if not value:
            return "—"
        if isinstance(value, (dict, list)):
            text = json.dumps(value, indent=2, default=str)
            if len(text) > max_len:
                return text[:max_len] + "..."
            return text
        return str(value)[:max_len]


class _TenantIdMixin:
    """Mixin for shortening tenant_id display."""

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj):
        tid = getattr(obj, "tenant_id", "")
        return tid[:12] + "..." if len(str(tid)) > 12 else str(tid)


@admin.register(ScheduledPost)
class ScheduledPostAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ScheduledPost model."""

    list_display = (
        "platform",
        "caption_preview",
        "status",
        "priority",
        "scheduled_at",
        "approval_status",
        "tenant_id_short",
    )
    list_filter = (
        "platform",
        "status",
        "priority",
        "approval_status",
        "publish_type",
        "scheduled_at",
    )
    search_fields = (
        "caption",
        "platform_post_id",
        "content_id",
        "campaign_id",
        "tenant_id",
    )
    ordering = ("-scheduled_at",)
    readonly_fields = (
        "id",
        "publish_attempts",
        "last_attempt_at",
        "published_at",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "scheduled_at"

    @admin.display(description="Caption")
    def caption_preview(self, obj: ScheduledPost) -> str:
        return obj.caption[:50] if obj.caption else "—"

    @admin.display(description="Hashtags")
    def display_hashtags(self, obj: ScheduledPost) -> str:
        return self._format_json(obj.hashtags, 150)

    @admin.display(description="Media URLs")
    def display_media(self, obj: ScheduledPost) -> str:
        return self._format_json(obj.media_urls, 150)


@admin.register(PublishQueue)
class PublishQueueAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for PublishQueue model."""

    list_display = (
        "scheduled_post_id",
        "queue_priority",
        "retry_count",
        "next_retry_at",
        "overflow_reason",
        "processed_at",
        "created_at",
    )
    list_filter = ("queue_priority", "overflow_reason", "processed_at", "created_at")
    search_fields = ("scheduled_post_id",)
    ordering = ("queue_priority", "next_retry_at")
    readonly_fields = ("id", "retry_count", "processed_at", "created_at", "updated_at")

    @admin.display(description="Error Log")
    def display_errors(self, obj: PublishQueue) -> str:
        return self._format_json(obj.error_log, 300)


@admin.register(ContentCalendar)
class ContentCalendarAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for ContentCalendar model."""

    list_display = (
        "scheduled_post_id",
        "calendar_view",
        "position_order",
        "color_override",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("calendar_view", "created_at")
    search_fields = ("scheduled_post_id", "tenant_id")
    ordering = ("position_order",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(RecurringPost)
class RecurringPostAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for RecurringPost model."""

    list_display = (
        "name",
        "platform",
        "cron_expression",
        "variation_strategy",
        "is_active",
        "instance_count",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "platform",
        "variation_strategy",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "platform", "cron_expression", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "instance_count", "created_at", "updated_at")

    @admin.display(description="Content Pool")
    def display_pool(self, obj: RecurringPost) -> str:
        return self._format_json(obj.content_pool, 200)

    @admin.display(description="Base Content")
    def display_base(self, obj: RecurringPost) -> str:
        return self._format_json(obj.base_content, 200)


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ApprovalWorkflow model."""

    list_display = (
        "name",
        "type",
        "step_count",
        "auto_approve_on_timeout",
        "is_active",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("type", "auto_approve_on_timeout", "is_active", "created_at")
    search_fields = ("name", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Steps")
    def display_steps(self, obj: ApprovalWorkflow) -> str:
        return self._format_json(obj.steps_json, 400)


@admin.register(BlackoutWindow)
class BlackoutWindowAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for BlackoutWindow model."""

    list_display = (
        "name",
        "platform",
        "start_at",
        "end_at",
        "recurring",
        "is_active",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("platform", "recurring", "is_active", "start_at")
    search_fields = ("name", "tenant_id")
    ordering = ("-start_at",)
    readonly_fields = ("id", "created_at", "updated_at")
