"""Initial migration for workflows_v2 — Workflow, Node, Edge, Template, Trigger."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Create core workflow tables."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Workflow",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("status", models.CharField(
                    choices=[("draft", "Draft"), ("active", "Active"),
                             ("paused", "Paused"), ("archived", "Archived")],
                    db_index=True, default="draft", max_length=20)),
                ("nodes", models.JSONField(default=list)),
                ("connections", models.JSONField(default=list)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("trigger_config", models.JSONField(blank=True, default=dict)),
                ("created_by", models.CharField(max_length=256)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_workflow",
                "verbose_name": "Workflow",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="workflow",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_workflow_tenant_name_uniq",
            ),
        ),
        migrations.CreateModel(
            name="WorkflowVersion",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("version", models.PositiveIntegerField()),
                ("nodes", models.JSONField(default=list)),
                ("connections", models.JSONField(default=list)),
                ("changelog", models.TextField(blank=True)),
                ("published_by", models.CharField(blank=True, max_length=256)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("workflow", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="versions", to="workflows_v2.workflow")),
            ],
            options={
                "db_table": "voyager_workflow_version",
                "verbose_name": "Workflow Version",
                "ordering": ["-version"],
                "unique_together": {("workflow", "version")},
            },
        ),
        migrations.CreateModel(
            name="WorkflowTrigger",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("trigger_type", models.CharField(
                    choices=[("cron", "Cron Schedule"), ("webhook", "Webhook"),
                             ("platform_event", "Platform Event"),
                             ("metric_threshold", "Metric Threshold"),
                             ("file_upload", "File Upload"),
                             ("email_received", "Email Received"),
                             ("manual", "Manual"), ("state_change", "State Change"),
                             ("scheduled", "Scheduled"), ("api_call", "API Call"),
                             ("form_submit", "Form Submission"),
                             ("websocket", "WebSocket"),
                             ("queue_message", "Queue Message"),
                             ("datetime", "Date/Time"), ("recurring", "Recurring")],
                    db_index=True, max_length=30)),
                ("name", models.CharField(max_length=255)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("trigger_count", models.PositiveIntegerField(default=0)),
                ("created_by", models.CharField(max_length=256)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("workflow", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="triggers", to="workflows_v2.workflow")),
            ],
            options={
                "db_table": "voyager_workflow_trigger",
                "verbose_name": "Workflow Trigger",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowTemplate",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("category", models.CharField(
                    choices=[("content", "Content"), ("approval", "Approval"),
                             ("notification", "Notification"),
                             ("integration", "Integration"),
                             ("analytics", "Analytics"),
                             ("social", "Social Media"),
                             ("email", "Email Marketing"), ("custom", "Custom")],
                    db_index=True, default="custom", max_length=50)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("author", models.CharField(max_length=100)),
                ("version", models.CharField(default="1.0.0", max_length=20)),
                ("rating", models.DecimalField(decimal_places=2, default=0.0, max_digits=3)),
                ("installs", models.PositiveIntegerField(default=0)),
                ("workflow", models.JSONField()),
                ("configurable", models.JSONField(blank=True, default=list)),
                ("required_modules", models.JSONField(blank=True, default=list)),
                ("is_public", models.BooleanField(default=True)),
                ("icon", models.CharField(blank=True, max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_workflow_template",
                "verbose_name": "Workflow Template",
                "ordering": ["-installs", "-rating", "name"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowNode",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("node_id", models.CharField(db_index=True, max_length=100)),
                ("node_type", models.CharField(
                    choices=[("trigger", "Trigger"), ("action", "Action"),
                             ("condition", "Condition"), ("loop", "Loop"),
                             ("delay", "Delay"), ("transform", "Transform"),
                             ("hitl", "Human-in-the-Loop"), ("webhook", "Webhook"),
                             ("sub_flow", "Sub-Flow"),
                             ("error_handler", "Error Handler")],
                    db_index=True, max_length=20)),
                ("label", models.CharField(blank=True, max_length=255)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("position", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("workflow", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="workflow_nodes", to="workflows_v2.workflow")),
            ],
            options={
                "db_table": "voyager_workflow_node",
                "verbose_name": "Workflow Node",
                "ordering": ["node_id"],
                "unique_together": {("workflow", "node_id")},
            },
        ),
        migrations.CreateModel(
            name="WorkflowEdge",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("source", models.CharField(db_index=True, max_length=100)),
                ("target", models.CharField(db_index=True, max_length=100)),
                ("label", models.CharField(blank=True, max_length=100)),
                ("condition", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("workflow", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="workflow_edges", to="workflows_v2.workflow")),
            ],
            options={
                "db_table": "voyager_workflow_edge",
                "verbose_name": "Workflow Edge",
                "ordering": ["source", "target"],
            },
        ),
        migrations.AddConstraint(
            model_name="workflowedge",
            constraint=models.UniqueConstraint(
                fields=["workflow", "source", "target"],
                name="%(app_label)s_edge_unique_connection",
            ),
        ),
    ]
