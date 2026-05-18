"""Project and ProjectMilestone models."""

from __future__ import annotations

from django.db import models

from apps.clients.models.client import Client


class Project(models.Model):
    """A project undertaken for a client.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        client: The client this project belongs to.
        name: Project name.
        description: Detailed project description.
        status: Current project status.
        start_date: Project start date.
        end_date: Project end date (estimated or actual).
        budget_amount: Allocated budget amount.
        budget_type: How the project is billed.
        manager_id: User ID of the project manager.
        team_ids: JSON list of team member user IDs.
        settings: Project-specific configuration.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class Status(models.TextChoices):
        """Project lifecycle statuses."""

        PLANNING = "planning", "Planning"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    class BudgetType(models.TextChoices):
        """Project billing types."""

        FIXED = "fixed", "Fixed Price"
        HOURLY = "hourly", "Hourly"
        RETAINER = "retainer", "Retainer"
        HYBRID = "hybrid", "Hybrid"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="projects",
        help_text="The client this project belongs to",
    )
    name = models.CharField(max_length=255, help_text="Project name")
    description = models.TextField(blank=True, help_text="Detailed project description")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
        help_text="Current project status",
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Project start date",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Project end date (estimated or actual)",
    )
    budget_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Allocated budget amount",
    )
    budget_type = models.CharField(
        max_length=20,
        choices=BudgetType.choices,
        default=BudgetType.FIXED,
        help_text="How the project is billed",
    )
    manager_id = models.CharField(
        max_length=256,
        blank=True,
        db_index=True,
        help_text="User ID of the project manager",
    )
    team_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of team member user IDs",
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Project-specific configuration",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        db_table = "voyager_project"
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "client", "status"]),
            models.Index(fields=["tenant_id", "manager_id"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.client.name})"


class ProjectMilestone(models.Model):
    """A milestone within a project.

    Attributes:
        id: Auto-incrementing primary key.
        project: The parent project this milestone belongs to.
        name: Milestone name.
        description: Detailed milestone description.
        due_date: When the milestone is due.
        status: Current milestone status.
        deliverables: JSON list of deliverable items.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class Status(models.TextChoices):
        """Milestone statuses."""

        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        MISSED = "missed", "Missed"

    id = models.BigAutoField(primary_key=True, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="milestones",
        help_text="The parent project this milestone belongs to",
    )
    name = models.CharField(max_length=255, help_text="Milestone name")
    description = models.TextField(blank=True, help_text="Detailed milestone description")
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="When the milestone is due",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current milestone status",
    )
    deliverables = models.JSONField(
        default=list,
        blank=True,
        help_text="List of deliverable items with name and status",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        db_table = "voyager_project_milestone"
        verbose_name = "Project Milestone"
        verbose_name_plural = "Project Milestones"
        ordering = ["due_date", "name"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.project.name})"
