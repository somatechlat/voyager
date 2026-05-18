"""WorkflowNode model — individual node within a workflow."""

from __future__ import annotations

from django.db import models


class WorkflowNode(models.Model):
    """A single node within a workflow definition.

    Supports 10 node types: trigger, action, condition, loop, delay,
    transform, hitl, webhook, sub_flow, error_handler.

    Attributes:
        id: Auto-incrementing primary key.
        workflow: The parent workflow.
        node_id: Client-generated unique identifier (e.g. 'trigger_1').
        node_type: The type of node.
        label: Human-readable label.
        config: Node-specific configuration JSON.
        position: Visual position {x, y} for the builder canvas.
        created_at: Timestamp.
        updated_at: Timestamp.
    """

    TYPE_TRIGGER = "trigger"
    TYPE_ACTION = "action"
    TYPE_CONDITION = "condition"
    TYPE_LOOP = "loop"
    TYPE_DELAY = "delay"
    TYPE_TRANSFORM = "transform"
    TYPE_HITL = "hitl"
    TYPE_WEBHOOK = "webhook"
    TYPE_SUB_FLOW = "sub_flow"
    TYPE_ERROR_HANDLER = "error_handler"

    NODE_TYPE_CHOICES = [
        (TYPE_TRIGGER, "Trigger"),
        (TYPE_ACTION, "Action"),
        (TYPE_CONDITION, "Condition"),
        (TYPE_LOOP, "Loop"),
        (TYPE_DELAY, "Delay"),
        (TYPE_TRANSFORM, "Transform"),
        (TYPE_HITL, "Human-in-the-Loop"),
        (TYPE_WEBHOOK, "Webhook"),
        (TYPE_SUB_FLOW, "Sub-Flow"),
        (TYPE_ERROR_HANDLER, "Error Handler"),
    ]

    id = models.BigAutoField(primary_key=True, editable=False)
    workflow = models.ForeignKey(
        "Workflow",
        on_delete=models.CASCADE,
        related_name="workflow_nodes",
        help_text="The parent workflow",
    )
    node_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Client-generated unique identifier (e.g. 'trigger_1')",
    )
    node_type = models.CharField(
        max_length=20,
        choices=NODE_TYPE_CHOICES,
        db_index=True,
        help_text="The type of node",
    )
    label = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable label",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Node-specific configuration",
    )
    position = models.JSONField(
        default=dict,
        blank=True,
        help_text="Visual position {x, y} for the builder canvas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_workflow_node"
        verbose_name = "Workflow Node"
        verbose_name_plural = "Workflow Nodes"
        ordering = ["node_id"]
        unique_together = [["workflow", "node_id"]]
        indexes = [
            models.Index(fields=["workflow", "node_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.node_id} ({self.get_node_type_display()})"
