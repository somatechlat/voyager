"""Django Admin for Team app.

Registers Task, TaskComment, TaskTimeEntry, MessageChannel,
and Message models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.team.models import (
    ActivityFeed,
    Message,
    MessageChannel,
    Task,
    TaskComment,
    TaskTimeEntry,
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


class TaskCommentInline(admin.TabularInline):
    """Inline for TaskComment within Task."""

    model = TaskComment
    extra = 0
    readonly_fields = ("id", "created_at")


class TaskTimeEntryInline(admin.TabularInline):
    """Inline for TaskTimeEntry within Task."""

    model = TaskTimeEntry
    extra = 0
    readonly_fields = ("id", "created_at")


@admin.register(Task)
class TaskAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for Task model."""

    list_display = (
        "id",
        "title_preview",
        "status",
        "priority",
        "task_type",
        "assignee_id_short",
        "due_date",
        "estimated_hours",
        "actual_hours",
        "is_overdue",
        "completion_pct",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "task_type",
        "due_date",
        "created_at",
    )
    search_fields = (
        "title",
        "description",
        "project_id",
        "client_id",
        "assignee_id",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "actual_hours",
        "created_at",
        "updated_at",
    )
    inlines = [TaskCommentInline, TaskTimeEntryInline]
    date_hierarchy = "due_date"

    @admin.display(description="Title")
    def title_preview(self, obj: Task) -> str:
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title

    @admin.display(description="Assignee")
    def assignee_id_short(self, obj: Task) -> str:
        return obj.assignee_id[:12] if obj.assignee_id else "—"

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj: Task) -> str:
        return obj.tenant_id[:12] if obj.tenant_id else "—"

    @admin.display(description="Overdue")
    def is_overdue(self, obj: Task) -> bool:
        return obj.is_overdue()

    @admin.display(description="Completion %")
    def completion_pct(self, obj: Task) -> str:
        return f"{obj.completion_percentage()}%"

    @admin.display(description="Tags")
    def display_tags(self, obj: Task) -> str:
        return self._format_json(obj.tags, 150)

    @admin.display(description="Subtasks")
    def display_subtasks(self, obj: Task) -> str:
        return self._format_json(obj.subtasks, 200)


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """Admin for TaskComment model."""

    list_display = (
        "task_title",
        "author_id_short",
        "content_preview",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("content", "author_id")
    ordering = ("created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("task",)

    @admin.display(description="Task")
    def task_title(self, obj: TaskComment) -> str:
        return f"#{obj.task_id} {obj.task.title[:30]}" if obj.task else "—"

    @admin.display(description="Author")
    def author_id_short(self, obj: TaskComment) -> str:
        return obj.author_id[:12] if obj.author_id else "—"

    @admin.display(description="Content")
    def content_preview(self, obj: TaskComment) -> str:
        return obj.content[:50] if obj.content else "—"


@admin.register(TaskTimeEntry)
class TaskTimeEntryAdmin(admin.ModelAdmin):
    """Admin for TaskTimeEntry model."""

    list_display = (
        "task_title",
        "user_id_short",
        "started_at",
        "ended_at",
        "duration_seconds",
        "description_preview",
        "created_at",
    )
    list_filter = ("started_at", "created_at")
    search_fields = ("description", "user_id")
    ordering = ("-started_at",)
    readonly_fields = ("id", "duration_seconds", "created_at")
    list_select_related = ("task",)

    @admin.display(description="Task")
    def task_title(self, obj: TaskTimeEntry) -> str:
        return f"#{obj.task_id} {obj.task.title[:30]}" if obj.task else "—"

    @admin.display(description="User")
    def user_id_short(self, obj: TaskTimeEntry) -> str:
        return obj.user_id[:12] if obj.user_id else "—"

    @admin.display(description="Description")
    def description_preview(self, obj: TaskTimeEntry) -> str:
        return obj.description[:40] if obj.description else "—"


@admin.register(MessageChannel)
class MessageChannelAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for MessageChannel model."""

    list_display = (
        "name",
        "channel_type",
        "participant_count",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("channel_type", "created_at")
    search_fields = ("name", "tenant_id")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Participants")
    def participant_count(self, obj: MessageChannel) -> int:
        pids = obj.participant_ids or []
        return len(pids) if isinstance(pids, list) else 0

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj: MessageChannel) -> str:
        return obj.tenant_id[:12] if obj.tenant_id else "—"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin for Message model."""

    list_display = (
        "channel_name",
        "author_id_short",
        "content_preview",
        "is_thread_reply",
        "reply_count",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("content", "author_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "edited_at", "created_at")
    list_select_related = ("channel",)

    @admin.display(description="Channel")
    def channel_name(self, obj: Message) -> str:
        return obj.channel.name if obj.channel else "—"

    @admin.display(description="Author")
    def author_id_short(self, obj: Message) -> str:
        return obj.author_id[:12] if obj.author_id else "—"

    @admin.display(description="Content")
    def content_preview(self, obj: Message) -> str:
        content = obj.content
        return content[:50] + "..." if len(content) > 50 else content


@admin.register(ActivityFeed)
class ActivityFeedAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for ActivityFeed model."""

    list_display = (
        "action_type",
        "actor_id_short",
        "target_type",
        "target_id",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("action_type", "target_type", "created_at")
    search_fields = ("action_type", "actor_id", "target_id", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at")

    @admin.display(description="Actor")
    def actor_id_short(self, obj: ActivityFeed) -> str:
        return obj.actor_id[:12] if obj.actor_id else "—"

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj: ActivityFeed) -> str:
        return obj.tenant_id[:12] if obj.tenant_id else "—"

    @admin.display(description="Metadata")
    def display_metadata(self, obj: ActivityFeed) -> str:
        return self._format_json(obj.metadata, 200)
