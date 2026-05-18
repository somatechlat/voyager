"""Activity feed model: ActivityFeed.

Defines the activity feed model for tracking actions across the platform.
"""

from __future__ import annotations

from django.db import models


class ActivityFeed(models.Model):
    """An activity feed entry tracking actions across the platform.

    Provides an audit trail of user actions with filtering by actor,
    target, and event type.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    actor_id = models.CharField(
        max_length=128, db_index=True,
        help_text="UUID of the user who performed the action",
    )
    action_type = models.CharField(
        max_length=50, db_index=True,
        help_text="Type of action (e.g. task.created, task.assigned)",
    )
    target_type = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text="Type of resource affected (e.g. task, message)",
    )
    target_id = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="ID of the affected resource",
    )
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text="Additional context as key-value pairs",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when created",
    )

    class Meta:
        db_table = "voyager_activity_feed"
        verbose_name = "Activity Feed Entry"
        verbose_name_plural = "Activity Feed Entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "-created_at"]),
            models.Index(fields=["tenant_id", "actor_id", "-created_at"]),
            models.Index(fields=["tenant_id", "action_type", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action_type} by {self.actor_id} on {self.target_type}:{self.target_id}"
