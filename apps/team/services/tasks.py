"""Task service — unified re-export of core CRUD and operations.

TaskService combines TaskCoreService (CRUD) and TaskOpsService (workflow
operations) into a single interface for the API layer.
"""

from __future__ import annotations

from apps.team.services.task_core import TaskCoreService, TaskServiceError
from apps.team.services.task_ops import TaskOpsService

__all__ = ["TaskService", "TaskServiceError"]


class TaskService(TaskCoreService, TaskOpsService):
    """Unified task service combining CRUD and workflow operations.

    Inherits all methods from TaskCoreService (create, get, list, update,
    delete) and TaskOpsService (assign, transition_status, add_comment,
    list_comments, log_time, list_time_entries, bulk_update, add_dependency,
    remove_dependency, add_subtask, toggle_subtask).
    """
