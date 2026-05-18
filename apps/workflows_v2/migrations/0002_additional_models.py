# Generated initial migration for workflows_v2


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("workflows_v2", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="WorkflowEdge",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "workflow",
                    models.ForeignKey(
                        to="Workflow",
                        on_delete=models.CASCADE,
                        related_name="workflow_edges",
                        help_text="The parent workflow",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        max_length=100,
                        db_index=True,
                        help_text="Source node identifier (node_id string)",
                    ),
                ),
                (
                    "target",
                    models.CharField(
                        max_length=100,
                        db_index=True,
                        help_text="Target node identifier (node_id string)",
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        max_length=100,
                        blank=True,
                        help_text="Edge label (e.g. 'true' for condition branches)",
                    ),
                ),
                (
                    "condition",
                    models.TextField(
                        blank=True,
                        help_text="Optional conditional expression for this edge",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "voyager_workflow_edge",
                "verbose_name": "Workflow Edge",
                "verbose_name_plural": "Workflow Edges",
                "ordering": ["source", "target"],
                "indexes": [
                    models.Index(fields=["workflow", "source"]),
                    models.Index(fields=["workflow", "target"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["workflow", "source", "target"],
                        name="%(app_label)s_edge_unique_connection",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="WorkflowExecution",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "workflow",
                    models.ForeignKey(
                        to="Workflow",
                        on_delete=models.CASCADE,
                        related_name="executions",
                        help_text="The workflow being executed",
                    ),
                ),
                (
                    "version",
                    models.PositiveIntegerField(
                        help_text="Workflow version at execution time",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=STATUS_CHOICES,
                        default=STATUS_PENDING,
                        db_index=True,
                    ),
                ),
                (
                    "trigger_type",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        help_text="How the execution was triggered",
                    ),
                ),
                (
                    "trigger_data",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Data that triggered the workflow",
                    ),
                ),
                (
                    "context",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Mutable execution context state",
                    ),
                ),
                (
                    "current_node",
                    models.CharField(
                        max_length=100,
                        blank=True,
                        help_text="ID of the node currently being executed",
                    ),
                ),
                (
                    "graph_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Vortex graph ID if submitted",
                    ),
                ),
                (
                    "run_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Vortex run ID if executing",
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("completed_at", models.DateTimeField(null=True, blank=True)),
                ("error", models.TextField(blank=True, help_text="Error message if failed")),
            ],
            options={
                "db_table": "voyager_workflow_execution",
                "verbose_name": "Workflow Execution",
                "verbose_name_plural": "Workflow Executions",
                "ordering": ["-started_at"],
                "indexes": [
                    models.Index(fields=["workflow", "-started_at"]),
                    models.Index(fields=["status"]),
                    models.Index(fields=["workflow", "status"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="WorkflowExecutionLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "execution",
                    models.ForeignKey(
                        WorkflowExecution,
                        on_delete=models.CASCADE,
                        related_name="logs",
                        help_text="The parent execution",
                    ),
                ),
                (
                    "node_id",
                    models.CharField(
                        max_length=100,
                        help_text="The node identifier that was executed",
                    ),
                ),
                (
                    "node_type",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        help_text="The type of node",
                    ),
                ),
                (
                    "input_data",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Input data to the node",
                    ),
                ),
                (
                    "output_data",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Output data from the node",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=STATUS_CHOICES,
                        default=STATUS_SUCCESS,
                    ),
                ),
                (
                    "duration_ms",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Execution duration in milliseconds",
                    ),
                ),
                ("error", models.TextField(blank=True, help_text="Error message if node failed")),
                ("executed_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_workflow_execution_log",
                "verbose_name": "Workflow Execution Log",
                "verbose_name_plural": "Workflow Execution Logs",
                "ordering": ["-executed_at"],
                "indexes": [
                    models.Index(fields=["execution", "-executed_at"]),
                    models.Index(fields=["execution", "node_id"]),
                ],
            },
        ),
    ]
