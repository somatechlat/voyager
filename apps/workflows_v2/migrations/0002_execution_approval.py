"""Migration for WorkflowExecution, WorkflowExecutionLog, HumanApprovalNode."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Create execution and approval tracking tables."""

    dependencies = [("workflows_v2", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="WorkflowExecution",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("version", models.PositiveIntegerField()),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("running", "Running"),
                             ("completed", "Completed"), ("failed", "Failed"),
                             ("cancelled", "Cancelled"), ("timed_out", "Timed Out"),
                             ("waiting_hitl", "Waiting for Human Approval")],
                    db_index=True, default="pending", max_length=20)),
                ("trigger_type", models.CharField(blank=True, max_length=50)),
                ("trigger_data", models.JSONField(blank=True, default=dict)),
                ("context", models.JSONField(blank=True, default=dict)),
                ("current_node", models.CharField(blank=True, max_length=100)),
                ("graph_id", models.CharField(blank=True, max_length=128)),
                ("run_id", models.CharField(blank=True, max_length=128)),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("workflow", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="executions", to="workflows_v2.workflow")),
            ],
            options={
                "db_table": "voyager_workflow_execution",
                "verbose_name": "Workflow Execution",
                "ordering": ["-started_at"],
            },
        ),
        migrations.AddIndex(
            model_name="workflowexecution",
            index=models.Index(fields=["workflow", "-started_at"], name="voyager_wf_exec_ws_start"),
        ),
        migrations.AddIndex(
            model_name="workflowexecution",
            index=models.Index(fields=["status"], name="voyager_wf_exec_status"),
        ),
        migrations.CreateModel(
            name="WorkflowExecutionLog",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("node_id", models.CharField(max_length=100)),
                ("node_type", models.CharField(blank=True, max_length=50)),
                ("input_data", models.JSONField(blank=True, default=dict)),
                ("output_data", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(
                    choices=[("success", "Success"), ("failed", "Failed"),
                             ("skipped", "Skipped"), ("waiting", "Waiting")],
                    default="success", max_length=20)),
                ("duration_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("executed_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("execution", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="logs", to="workflows_v2.workflowexecution")),
            ],
            options={
                "db_table": "voyager_workflow_execution_log",
                "verbose_name": "Workflow Execution Log",
                "ordering": ["-executed_at"],
            },
        ),
        migrations.CreateModel(
            name="HumanApprovalNode",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("node_id", models.CharField(max_length=100)),
                ("approvers", models.JSONField(default=list)),
                ("current_approver", models.CharField(blank=True, max_length=256)),
                ("form_config", models.JSONField(blank=True, default=dict)),
                ("timeout_hours", models.PositiveIntegerField(default=24)),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("approved", "Approved"),
                             ("rejected", "Rejected"), ("timed_out", "Timed Out"),
                             ("escalated", "Escalated"), ("cancelled", "Cancelled")],
                    db_index=True, default="pending", max_length=20)),
                ("decision", models.CharField(blank=True, max_length=50)),
                ("feedback", models.TextField(blank=True)),
                ("form_data", models.JSONField(blank=True, default=dict)),
                ("escalate_to", models.CharField(blank=True, max_length=256)),
                ("submitted_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("deadline_at", models.DateTimeField(blank=True, null=True)),
                ("execution", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="approval_requests",
                    to="workflows_v2.workflowexecution")),
            ],
            options={
                "db_table": "voyager_human_approval_node",
                "verbose_name": "Human Approval Node",
                "ordering": ["-submitted_at"],
            },
        ),
    ]
