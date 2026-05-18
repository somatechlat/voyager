"""Task-related models: Task, TaskComment, TaskTimeEntry.

Defines the core task management models with support for priorities,
dependencies, subtasks, time tracking, and comments.
"""

from __future__ import annotations

import re

from django.db import models
from django.utils import timezone


class Task(models.Model):
    """A task represents a unit of work assignable to a team member.

    Tasks support priorities, statuses, dependencies, subtasks, custom fields,
    and time tracking. All tasks are scoped to a tenant.
    """

    class Priority(models.TextChoices):
        """Priority levels with SLA guidance."""

        P0 = "P0", "Critical"
        P1 = "P1", "High"
        P2 = "P2", "Medium"
        P3 = "P3", "Low"

    class Status(models.TextChoices):
        """Task lifecycle statuses."""

        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    title = models.CharField(max_length=500, help_text="Short task title")
    description = models.TextField(blank=True, help_text="Detailed task description")
    project_id = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="Optional linked project UUID",
    )
    client_id = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="Optional linked client UUID",
    )
    campaign_id = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="Optional linked campaign UUID",
    )
    assignee_id = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="UUID of the assigned user",
    )
    reporter_id = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="UUID of the user who created the task",
    )
    priority = models.CharField(
        max_length=5, choices=Priority.choices, default=Priority.P2,
        db_index=True, help_text="Priority level P0-P3",
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.TODO,
        db_index=True, help_text="Current task status",
    )
    task_type = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text="Type of work (design, development, etc.)",
    )
    tags = models.JSONField(default=list, blank=True, help_text="List of string tags")
    due_date = models.DateField(
        null=True, blank=True, db_index=True, help_text="Deadline date",
    )
    estimated_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Estimated effort in hours",
    )
    actual_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Logged effort in hours",
    )
    dependencies = models.JSONField(
        default=list, blank=True, help_text="List of dependent task IDs",
    )
    subtasks = models.JSONField(
        default=list, blank=True,
        help_text="List of subtask objects with id, title, done fields",
    )
    custom_fields = models.JSONField(
        default=dict, blank=True, help_text="Key-value custom fields",
    )
    attachments = models.JSONField(
        default=list, blank=True, help_text="List of attachment file references",
    )
    position = models.IntegerField(
        default=0, help_text="Sort position for Kanban boards",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_task"
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "priority"]),
            models.Index(fields=["tenant_id", "assignee_id", "status"]),
            models.Index(fields=["tenant_id", "project_id", "status"]),
            models.Index(fields=["tenant_id", "due_date"]),
            models.Index(fields=["tenant_id", "task_type"]),
            models.Index(fields=["assignee_id", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"#{self.id} {self.title} [{self.status}]"

    def is_overdue(self) -> bool:
        """Check if the task is past its due date and not done."""
        if self.due_date and self.status not in (self.Status.DONE, self.Status.CANCELLED):
            return self.due_date < timezone.now().date()
        return False

    def completion_percentage(self) -> int:
        """Calculate subtask completion percentage (0-100)."""
        subs = self.subtasks or []
        if not subs:
            return 100 if self.status == self.Status.DONE else 0
        done_count = sum(1 for s in subs if s.get("done", False))
        return int((done_count / len(subs)) * 100)

    def blocked_by(self) -> list[int]:
        """Return list of task IDs that block this task."""
        deps = self.dependencies or []
        if not deps:
            return []
        blocker_ids = []
        for dep_id in deps:
            try:
                dep = Task.objects.get(id=dep_id)
                if dep.status != Task.Status.DONE:
                    blocker_ids.append(dep_id)
            except Task.DoesNotExist:
                continue
        return blocker_ids

    def can_transition_to(self, new_status: str) -> bool:
        """Check if a status transition is valid."""
        if new_status == self.status:
            return True
        if new_status == self.Status.DONE:
            return len(self.blocked_by()) == 0
        return new_status in [s[0] for s in self.Status.choices]


class TaskComment(models.Model):
    """A comment on a task with mention and attachment support."""

    id = models.BigAutoField(primary_key=True, editable=False)
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="comments",
        help_text="Parent task",
    )
    author_id = models.CharField(
        max_length=128, db_index=True, help_text="UUID of the comment author",
    )
    content = models.TextField(help_text="Comment text content")
    mentions = models.JSONField(
        default=list, blank=True, help_text="List of mentioned user IDs",
    )
    attachments = models.JSONField(
        default=list, blank=True, help_text="List of attachment references",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_task_comment"
        verbose_name = "Task Comment"
        verbose_name_plural = "Task Comments"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["author_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Comment on #{self.task_id} by {self.author_id}"

    def extract_mentions(self) -> list[str]:
        """Extract @username mentions from content."""
        pattern = r"@(\w+)"
        return re.findall(pattern, self.content)


class TaskTimeEntry(models.Model):
    """A time entry logged against a task."""

    id = models.BigAutoField(primary_key=True, editable=False)
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="time_entries",
        help_text="Parent task",
    )
    user_id = models.CharField(
        max_length=128, db_index=True,
        help_text="UUID of the user who logged time",
    )
    started_at = models.DateTimeField(db_index=True, help_text="When work began")
    ended_at = models.DateTimeField(
        null=True, blank=True, help_text="When work ended",
    )
    duration_seconds = models.IntegerField(
        null=True, blank=True, help_text="Computed duration in seconds",
    )
    description = models.TextField(
        blank=True, help_text="Optional description of work performed",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when created",
    )

    class Meta:
        db_table = "voyager_task_time_entry"
        verbose_name = "Task Time Entry"
        verbose_name_plural = "Task Time Entries"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["task", "user_id"]),
            models.Index(fields=["user_id", "started_at"]),
            models.Index(fields=["task", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"Time entry on #{self.task_id} by {self.user_id}"

    def compute_duration(self) -> int | None:
        """Calculate duration from started_at and ended_at in seconds."""
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return None

    def save(self, *args, **kwargs):
        """Auto-compute duration_seconds before saving."""
        if self.ended_at and self.started_at:
            self.duration_seconds = int(
                (self.ended_at - self.started_at).total_seconds()
            )
        super().save(*args, **kwargs)
