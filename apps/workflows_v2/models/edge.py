"""WorkflowEdge model — connections between workflow nodes."""

from __future__ import annotations

from django.db import models


class WorkflowEdge(models.Model):
    """A directed connection (edge) between two workflow nodes.

    Edges define the flow of execution. Condition edges carry an
    expression label (e.g. 'true', 'false').

    Attributes:
        id: Auto-incrementing primary key.
        workflow: The parent workflow.
        source: Source node identifier (node_id string).
        target: Target node identifier (node_id string).
        label: Optional edge label (e.g. 'true' for condition branches).
        condition: Optional conditional expression for this edge.
        created_at: Timestamp.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    workflow = models.ForeignKey(
        "Workflow",
        on_delete=models.CASCADE,
        related_name="workflow_edges",
        help_text="The parent workflow",
    )
    source = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Source node identifier (node_id string)",
    )
    target = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Target node identifier (node_id string)",
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Edge label (e.g. 'true' for condition branches)",
    )
    condition = models.TextField(
        blank=True,
        help_text="Optional conditional expression for this edge",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "voyager_workflow_edge"
        verbose_name = "Workflow Edge"
        verbose_name_plural = "Workflow Edges"
        ordering = ["source", "target"]
        indexes = [
            models.Index(fields=["workflow", "source"]),
            models.Index(fields=["workflow", "target"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "source", "target"],
                name="%(app_label)s_edge_unique_connection",
            ),
        ]

    def __str__(self) -> str:
        label_str = f" [{self.label}]" if self.label else ""
        return f"{self.source}{label_str} -> {self.target}"
