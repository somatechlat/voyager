# Generated initial migration for workflows_v2


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("workflows_v2", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="WorkflowTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "name",
                    models.CharField(max_length=255, help_text="Human-readable template name"),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed template description",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        max_length=50,
                        choices=CATEGORY_CHOICES,
                        default=CATEGORY_CUSTOM,
                        db_index=True,
                        help_text="Template category",
                    ),
                ),
                ("tags", models.JSONField(default=list, blank=True, help_text="Searchable tags")),
                (
                    "author",
                    models.CharField(max_length=100, help_text="Template author identifier"),
                ),
                (
                    "version",
                    models.CharField(
                        max_length=20,
                        default="1.0.0",
                        help_text="Template version string (semver)",
                    ),
                ),
                (
                    "rating",
                    models.DecimalField(
                        max_digits=3,
                        decimal_places=2,
                        default=0.0,
                        help_text="Average user rating (0.00-5.00)",
                    ),
                ),
                (
                    "installs",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of installations",
                    ),
                ),
                ("workflow", models.JSONField(help_text="The workflow definition JSON")),
                (
                    "configurable",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="JSON schema for customizable parameters",
                    ),
                ),
                (
                    "required_modules",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of required module names",
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=True,
                        help_text="Whether visible in marketplace",
                    ),
                ),
                ("icon", models.CharField(max_length=50, blank=True, help_text="Icon identifier")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_workflow_template",
                "verbose_name": "Workflow Template",
                "verbose_name_plural": "Workflow Templates",
                "ordering": ["-installs", "-rating", "name"],
                "indexes": [
                    models.Index(fields=["category", "is_public"]),
                    models.Index(fields=["-rating"]),
                    models.Index(fields=["-installs"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="WorkflowTrigger",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "workflow",
                    models.ForeignKey(
                        to="Workflow",
                        on_delete=models.CASCADE,
                        related_name="triggers",
                        help_text="The workflow to trigger",
                    ),
                ),
                (
                    "trigger_type",
                    models.CharField(
                        max_length=30,
                        choices=TRIGGER_TYPE_CHOICES,
                        db_index=True,
                        help_text="The type of trigger",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Human-readable trigger name")),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Trigger-specific configuration",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        db_index=True,
                        help_text="Whether this trigger is enabled",
                    ),
                ),
                (
                    "last_triggered_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When this trigger last fired",
                    ),
                ),
                (
                    "trigger_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total number of times triggered",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        max_length=256,
                        help_text="User who created the trigger",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_workflow_trigger",
                "verbose_name": "Workflow Trigger",
                "verbose_name_plural": "Workflow Triggers",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["workflow", "trigger_type"]),
                    models.Index(fields=["workflow", "is_active"]),
                    models.Index(fields=["trigger_type", "is_active"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="HumanApprovalNode",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "execution",
                    models.ForeignKey(
                        to="WorkflowExecution",
                        on_delete=models.CASCADE,
                        related_name="approval_requests",
                        help_text="The parent workflow execution",
                    ),
                ),
                ("node_id", models.CharField(max_length=100, help_text="The HITL node identifier")),
                (
                    "approvers",
                    models.JSONField(
                        default=list,
                        help_text="List of approver identifiers (user IDs or roles)",
                    ),
                ),
                (
                    "current_approver",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        help_text="Currently assigned approver",
                    ),
                ),
                (
                    "form_config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Form field definitions for the approval UI",
                    ),
                ),
                (
                    "timeout_hours",
                    models.PositiveIntegerField(
                        default=24,
                        help_text="Hours before auto-timeout",
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
                    "decision",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        help_text="The final decision value (e.g. 'approve', 'reject')",
                    ),
                ),
                (
                    "feedback",
                    models.TextField(
                        blank=True,
                        help_text="Free-text feedback from approver",
                    ),
                ),
                (
                    "form_data",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Submitted form data",
                    ),
                ),
                (
                    "escalate_to",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        help_text="Escalation target if timeout",
                    ),
                ),
                ("submitted_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("decided_at", models.DateTimeField(null=True, blank=True)),
                (
                    "deadline_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Timeout deadline",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_human_approval_node",
                "verbose_name": "Human Approval Node",
                "verbose_name_plural": "Human Approval Nodes",
                "ordering": ["-submitted_at"],
                "indexes": [
                    models.Index(fields=["execution", "node_id"]),
                    models.Index(fields=["status", "deadline_at"]),
                    models.Index(fields=["current_approver", "status"]),
                ],
            },
        ),
    ]
