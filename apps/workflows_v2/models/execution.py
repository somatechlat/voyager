"""WorkflowExecution and WorkflowExecutionLog models."""

from __future__ import annotations

from django.db import models


class WorkflowExecution(models.Model):
    """A single run (execution) of a workflow.

    Tracks the lifecycle of a workflow run from trigger through
    completion, including current node, context state, and error info.

    Attributes:
        id: Auto-incrementing primary key.
        workflow: The workflow being executed.
        version: Workflow version at execution time.
        status: Execution status (pending/running/completed/failed/cancelled/timed_out).
        trigger_type: How the execution was triggered.
        trigger_data: Data that triggered the workflow.
        context: Mutable execution context (JSON).
        current_node: ID of the node currently being executed.
        graph_id: Vortex graph ID if submitted.
        run_id: Vortex run ID if executing.
        started_at: When execution began.
        completed_at: When execution finished.
        error: Error message if failed.
    """

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_TIMED_OUT = "timed_out"
    STATUS_WAITING_HITL = "waiting_hitl"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_TIMED_OUT, "Timed Out"),
        (STATUS_WAITING_HITL, "Waiting for Human Approval"),
    ]

    id = models.BigAutoField(primary_key=True, editable=False)
    workflow = models.ForeignKey(
        "Workflow",
        on_delete=models.CASCADE,
        related_name="executions",
        help_text="The workflow being executed",
    )
    version = models.PositiveIntegerField(
        help_text="Workflow version at execution time",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    trigger_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="How the execution was triggered",
    )
    trigger_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Data that triggered the workflow",
    )
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mutable execution context state",
    )
    current_node = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID of the node currently being executed",
    )
    graph_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="Vortex graph ID if submitted",
    )
    run_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="Vortex run ID if executing",
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    error = models.TextField(
        blank=True,
        help_text="Error message if failed",
    )

    class Meta:
        db_table = "voyager_workflow_execution"
        verbose_name = "Workflow Execution"
        verbose_name_plural = "Workflow Executions"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["workflow", "-started_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["workflow", "status"]),
        ]

    def __str__(self) -> str:
        return f"Execution {self.id} of {self.workflow.name} ({self.status})"

    def is_terminal(self) -> bool:
        """Check if execution is in a terminal state."""
        return self.status in (
            self.STATUS_COMPLETED,
            self.STATUS_FAILED,
            self.STATUS_CANCELLED,
            self.STATUS_TIMED_OUT,
        )

    @property
    def progress(self) -> float:
        """Calculate execution progress as a float 0.0-1.0."""
        log_count = self.logs.count()
        if log_count == 0:
            return 0.0
        total_nodes = len(self.workflow.nodes) if self.workflow else 1
        if total_nodes == 0:
            return 0.0
        return min(log_count / total_nodes, 1.0)


class WorkflowExecutionLog(models.Model):
    """A log entry for a single node execution within a workflow run.

    Records what happened at each node: input, output, duration,
    status, and any error that occurred.

    Attributes:
        id: Auto-incrementing primary key.
        execution: The parent execution.
        node_id: The node identifier that was executed.
        node_type: The type of node.
        input: Input data to the node.
        output: Output data from the node.
        status: Execution status for this node.
        duration_ms: Execution duration in milliseconds.
        error: Error message if node failed.
        executed_at: When the node was executed.
    """

    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_WAITING = "waiting"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
        (STATUS_WAITING, "Waiting"),
    ]

    id = models.BigAutoField(primary_key=True, editable=False)
    execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name="logs",
        help_text="The parent execution",
    )
    node_id = models.CharField(
        max_length=100,
        help_text="The node identifier that was executed",
    )
    node_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="The type of node",
    )
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Input data to the node",
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output data from the node",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUCCESS,
    )
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Execution duration in milliseconds",
    )
    error = models.TextField(
        blank=True,
        help_text="Error message if node failed",
    )
    executed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "voyager_workflow_execution_log"
        verbose_name = "Workflow Execution Log"
        verbose_name_plural = "Workflow Execution Logs"
        ordering = ["-executed_at"]
        indexes = [
            models.Index(fields=["execution", "-executed_at"]),
            models.Index(fields=["execution", "node_id"]),
        ]

    def __str__(self) -> str:
        return f"Log {self.node_id} ({self.status})"
