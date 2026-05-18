# Generated initial migration for workflows_v2


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Workflow",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, help_text="Human-readable workflow name"),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional workflow description",
                    ),
                ),
                (
                    "version",
                    models.PositiveIntegerField(default=1, help_text="Current version number"),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=STATUS_CHOICES,
                        default=STATUS_DRAFT,
                        db_index=True,
                        help_text="Workflow lifecycle status",
                    ),
                ),
                (
                    "nodes",
                    models.JSONField(default=list, help_text="JSON array of node definitions"),
                ),
                (
                    "connections",
                    models.JSONField(
                        default=list,
                        help_text="JSON array of edge definitions",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Workflow-level configuration",
                    ),
                ),
                (
                    "trigger_config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Global trigger configuration",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        max_length=256,
                        help_text="User ID of the workflow creator",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_workflow",
                "verbose_name": "Workflow",
                "verbose_name_plural": "Workflows",
                "ordering": ["-updated_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "-updated_at"]),
                    models.Index(fields=["tenant_id", "name"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"], name="%(app_label)s_workflow_tenant_name_uniq"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="WorkflowVersion",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "workflow",
                    models.ForeignKey(
                        Workflow,
                        on_delete=models.CASCADE,
                        related_name="versions",
                        help_text="The parent workflow",
                    ),
                ),
                (
                    "version",
                    models.PositiveIntegerField(
                        help_text="The version number of this snapshot",
                    ),
                ),
                (
                    "nodes",
                    models.JSONField(
                        default=list,
                        help_text="JSON array of node definitions at this version",
                    ),
                ),
                (
                    "connections",
                    models.JSONField(
                        default=list,
                        help_text="JSON array of edge definitions at this version",
                    ),
                ),
                (
                    "changelog",
                    models.TextField(
                        blank=True,
                        help_text="Description of changes in this version",
                    ),
                ),
                (
                    "published_by",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        help_text="User ID who published this version",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_workflow_version",
                "verbose_name": "Workflow Version",
                "verbose_name_plural": "Workflow Versions",
                "ordering": ["-version"],
                "indexes": [models.Index(fields=["workflow", "-version"])],
                "unique_together": [["workflow", "version"]],
            },
        ),
        migrations.CreateModel(
            name="WorkflowNode",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "workflow",
                    models.ForeignKey(
                        to="Workflow",
                        on_delete=models.CASCADE,
                        related_name="workflow_nodes",
                        help_text="The parent workflow",
                    ),
                ),
                (
                    "node_id",
                    models.CharField(
                        max_length=100,
                        db_index=True,
                        help_text="Client-generated unique identifier (e.g. 'trigger_1')",
                    ),
                ),
                (
                    "node_type",
                    models.CharField(
                        max_length=20,
                        choices=NODE_TYPE_CHOICES,
                        db_index=True,
                        help_text="The type of node",
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        help_text="Human-readable label",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Node-specific configuration",
                    ),
                ),
                (
                    "position",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Visual position {x, y} for the builder canvas",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_workflow_node",
                "verbose_name": "Workflow Node",
                "verbose_name_plural": "Workflow Nodes",
                "ordering": ["node_id"],
                "indexes": [models.Index(fields=["workflow", "node_type"])],
                "unique_together": [["workflow", "node_id"]],
            },
        ),
    ]
