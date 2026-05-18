"""Project management service.

Handles project CRUD, milestone tracking, and timeline management.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models import QuerySet
from ninja.errors import HttpError

from apps.clients.models.client import Client
from apps.clients.models.project import Project, ProjectMilestone

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project lifecycle management.

    Provides CRUD operations for projects, milestone tracking, and
    timeline calculations for client work.
    """

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create(tenant_id: str, client_id: int, data: dict[str, Any]) -> Project:
        """Create a new project for a client.

        Args:
            tenant_id: The tenant identifier.
            client_id: The client primary key.
            data: Dictionary of project field values.

        Returns:
            The newly created Project instance.

        Raises:
            HttpError: 404 if the client does not exist.
        """
        try:
            client = Client.objects.get(tenant_id=tenant_id, id=client_id)
        except Client.DoesNotExist:
            raise HttpError(404, "Client not found")

        project = Project.objects.create(tenant_id=tenant_id, client=client, **data)
        logger.info(
            "Project created: %s for client %s (tenant: %s)",
            project.name,
            client.name,
            tenant_id,
        )
        return project

    @staticmethod
    def list_projects(
        tenant_id: str,
        client_id: int | None = None,
        status: str | None = None,
        manager_id: str | None = None,
    ) -> QuerySet[Project]:
        """List projects with optional filtering.

        Args:
            tenant_id: The tenant identifier.
            client_id: Optional client filter.
            status: Optional status filter.
            manager_id: Optional project manager filter.

        Returns:
            QuerySet of matching Project instances.
        """
        qs: QuerySet[Project] = Project.objects.filter(tenant_id=tenant_id)
        if client_id:
            qs = qs.filter(client_id=client_id)
        if status:
            qs = qs.filter(status=status)
        if manager_id:
            qs = qs.filter(manager_id=manager_id)
        return qs.order_by("-created_at")

    @staticmethod
    def get_by_id(tenant_id: str, project_id: int) -> Project:
        """Retrieve a single project by ID.

        Args:
            tenant_id: The tenant identifier.
            project_id: The project primary key.

        Returns:
            The Project instance.

        Raises:
            HttpError: 404 if the project does not exist.
        """
        try:
            return Project.objects.get(tenant_id=tenant_id, id=project_id)
        except Project.DoesNotExist:
            raise HttpError(404, "Project not found")

    @staticmethod
    def update(project: Project, data: dict[str, Any]) -> Project:
        """Update an existing project.

        Args:
            project: The Project instance to update.
            data: Dictionary of fields to update.

        Returns:
            The updated Project instance.
        """
        for key, value in data.items():
            if value is not None and hasattr(project, key):
                setattr(project, key, value)
        project.save()
        logger.info("Project updated: %s", project.name)
        return project

    @staticmethod
    def delete(project: Project) -> None:
        """Delete a project and its milestones.

        Args:
            project: The Project instance to delete.
        """
        name = project.name
        project.delete()
        logger.info("Project deleted: %s", name)

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------

    @staticmethod
    def create_milestone(project_id: int, data: dict[str, Any]) -> ProjectMilestone:
        """Create a milestone for a project.

        Args:
            project_id: The project primary key.
            data: Dictionary of milestone field values.

        Returns:
            The newly created ProjectMilestone instance.

        Raises:
            HttpError: 404 if the project does not exist.
        """
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise HttpError(404, "Project not found")

        milestone = ProjectMilestone.objects.create(project=project, **data)
        logger.info("Milestone created: %s for project %s", milestone.name, project.name)
        return milestone

    @staticmethod
    def list_milestones(project_id: int) -> QuerySet[ProjectMilestone]:
        """List all milestones for a project.

        Args:
            project_id: The project primary key.

        Returns:
            QuerySet of ProjectMilestone instances.
        """
        return ProjectMilestone.objects.filter(project_id=project_id).order_by("due_date")

    @staticmethod
    def get_milestone_by_id(project_id: int, milestone_id: int) -> ProjectMilestone:
        """Retrieve a single milestone.

        Args:
            project_id: The project primary key.
            milestone_id: The milestone primary key.

        Returns:
            The ProjectMilestone instance.

        Raises:
            HttpError: 404 if the milestone does not exist.
        """
        try:
            return ProjectMilestone.objects.get(project_id=project_id, id=milestone_id)
        except ProjectMilestone.DoesNotExist:
            raise HttpError(404, "Milestone not found")

    @staticmethod
    def update_milestone(milestone: ProjectMilestone, data: dict[str, Any]) -> ProjectMilestone:
        """Update a milestone.

        Args:
            milestone: The ProjectMilestone instance.
            data: Dictionary of fields to update.

        Returns:
            The updated ProjectMilestone instance.
        """
        for key, value in data.items():
            if value is not None and hasattr(milestone, key):
                setattr(milestone, key, value)
        milestone.save()
        logger.info("Milestone updated: %s", milestone.name)
        return milestone

    @staticmethod
    def delete_milestone(milestone: ProjectMilestone) -> None:
        """Delete a milestone.

        Args:
            milestone: The ProjectMilestone instance to delete.
        """
        name = milestone.name
        milestone.delete()
        logger.info("Milestone deleted: %s", name)

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    @staticmethod
    def get_timeline(project_id: int) -> dict[str, Any]:
        """Compute project timeline summary.

        Calculates overall progress based on milestone completion.

        Args:
            project_id: The project primary key.

        Returns:
            Dictionary with timeline metrics.
        """
        milestones = ProjectMilestone.objects.filter(project_id=project_id)
        total = milestones.count()
        if total == 0:
            return {
                "total_milestones": 0,
                "completed": 0,
                "in_progress": 0,
                "pending": 0,
                "missed": 0,
                "progress_percent": 0.0,
            }

        completed = milestones.filter(status=ProjectMilestone.Status.COMPLETED).count()
        in_progress = milestones.filter(status=ProjectMilestone.Status.IN_PROGRESS).count()
        pending = milestones.filter(status=ProjectMilestone.Status.PENDING).count()
        missed = milestones.filter(status=ProjectMilestone.Status.MISSED).count()

        return {
            "total_milestones": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "missed": missed,
            "progress_percent": round((completed / total) * 100, 2),
        }
