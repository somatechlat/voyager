"""Workflow and WorkflowVersion models."""

from __future__ import annotations

from django.db import models


class Workflow(models.Model):
    """A workflow definition with nodes, edges, and configuration.

    Workflows are versioned, tenant-scoped visual automation definitions
    that compile to Vortex GraphDSL for execution.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Human-readable workflow name.
        description: Optional workflow description.
        version: Current version number (auto-incremented on publish).
        status: Workflow lifecycle status (draft/active/paused/archived).
        nodes: JSON array of node definitions.
        connections: JSON array of edge definitions.
        config: Optional workflow-level configuration.
        trigger_config: Global trigger configuration.
        created_by: User ID of the workflow creator.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable workflow name",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional workflow description",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Current version number",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
        help_text="Workflow lifecycle status",
    )
    nodes = models.JSONField(
        default=list,
        help_text="JSON array of node definitions",
    )
    connections = models.JSONField(
        default=list,
        help_text="JSON array of edge definitions",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Workflow-level configuration",
    )
    trigger_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Global trigger configuration",
    )
    created_by = models.CharField(
        max_length=256,
        help_text="User ID of the workflow creator",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
    )

    class Meta:
        db_table = "voyager_workflow"
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "-updated_at"]),
            models.Index(fields=["tenant_id", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_workflow_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"

    def is_editable(self) -> bool:
        """Check if workflow can be edited (only draft or paused)."""
        return self.status in (self.STATUS_DRAFT, self.STATUS_PAUSED)

    def can_execute(self) -> bool:
        """Check if workflow can be executed (active or paused can be manually triggered)."""
        return self.status in (self.STATUS_ACTIVE, self.STATUS_PAUSED)


class WorkflowVersion(models.Model):
    """A frozen snapshot of a workflow at a specific version.

    When a workflow is published, its current state is snapshotted
    here so that running executions can continue against the old
    version while edits proceed on the main workflow.

    Attributes:
        id: Auto-incrementing primary key.
        workflow: The parent workflow.
        version: The version number of this snapshot.
        nodes: JSON array of node definitions at this version.
        connections: JSON array of edge definitions at this version.
        changelog: Description of changes in this version.
        published_by: User ID who published this version.
        created_at: Timestamp when published.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="versions",
        help_text="The parent workflow",
    )
    version = models.PositiveIntegerField(
        help_text="The version number of this snapshot",
    )
    nodes = models.JSONField(
        default=list,
        help_text="JSON array of node definitions at this version",
    )
    connections = models.JSONField(
        default=list,
        help_text="JSON array of edge definitions at this version",
    )
    changelog = models.TextField(
        blank=True,
        help_text="Description of changes in this version",
    )
    published_by = models.CharField(
        max_length=256,
        blank=True,
        help_text="User ID who published this version",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "voyager_workflow_version"
        verbose_name = "Workflow Version"
        verbose_name_plural = "Workflow Versions"
        ordering = ["-version"]
        unique_together = [["workflow", "version"]]
        indexes = [
            models.Index(fields=["workflow", "-version"]),
        ]

    def __str__(self) -> str:
        return f"{self.workflow.name} v{self.version}"
