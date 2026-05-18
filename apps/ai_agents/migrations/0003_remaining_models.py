# Generated initial migration for ai_agents


from django.db import migrations, models


class Pattern(models.TextChoices):
    PIPELINE = "pipeline", "Pipeline"
    FAN_OUT = "fan_out", "Fan-out"
    FAN_IN = "fan_in", "Fan-in"
    REVIEW = "review", "Review"
    DEBATE = "debate", "Debate"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("ai_agents", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="AgentContext",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "agent",
                    models.ForeignKey(
                        to="ai_agents.AIAgent",
                        on_delete=models.CASCADE,
                        related_name="contexts",
                        help_text="The agent this context was assembled for",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "task_type",
                    models.CharField(
                        max_length=50,
                        help_text="The type of task being executed",
                    ),
                ),
                (
                    "brand_context",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Brand guidelines snapshot",
                    ),
                ),
                (
                    "audience_context",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Audience personas snapshot",
                    ),
                ),
                (
                    "performance_context",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Recent performance data snapshot",
                    ),
                ),
                (
                    "memory_ids",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of memory entry IDs included in context",
                    ),
                ),
                (
                    "current_state",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Active campaigns, scheduled content, pending approvals",
                    ),
                ),
                (
                    "assembled_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the context was assembled",
                    ),
                ),
                (
                    "token_estimate",
                    models.IntegerField(
                        default=0,
                        help_text="Estimated token count of the assembled context",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_agent_context",
                "verbose_name": "Agent Context",
                "verbose_name_plural": "Agent Contexts",
                "ordering": ["-assembled_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "agent", "-assembled_at"]),
                    models.Index(fields=["agent", "task_type"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AgentCollaboration",
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
                    "initiator_agent",
                    models.ForeignKey(
                        to="ai_agents.AIAgent",
                        on_delete=models.CASCADE,
                        related_name="initiated_collaborations",
                        help_text="The agent that started the collaboration",
                    ),
                ),
                (
                    "task_id",
                    models.CharField(
                        max_length=128,
                        help_text="Identifier of the task being collaborated on",
                    ),
                ),
                (
                    "pattern",
                    models.CharField(
                        max_length=20,
                        choices=Pattern.choices,
                        help_text="Collaboration pattern used",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING,
                        help_text="Current status of the collaboration",
                    ),
                ),
                (
                    "delegation_chain",
                    models.JSONField(
                        default=list,
                        help_text="Ordered list of agent IDs in the delegation chain",
                    ),
                ),
                (
                    "max_depth",
                    models.IntegerField(
                        default=5,
                        help_text="Maximum allowed delegation depth",
                    ),
                ),
                (
                    "messages",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="JSON log of inter-agent messages",
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the collaboration began",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the collaboration finished",
                    ),
                ),
                (
                    "result_summary",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="JSON summary of the collaboration outcome",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_agent_collaboration",
                "verbose_name": "Agent Collaboration",
                "verbose_name_plural": "Agent Collaborations",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["initiator_agent", "status"]),
                    models.Index(fields=["task_id"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="MCPToolCall",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "agent",
                    models.ForeignKey(
                        to="ai_agents.AIAgent",
                        on_delete=models.CASCADE,
                        related_name="tool_calls",
                        help_text="The agent that registered or invoked this tool",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "tool_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Unique tool identifier",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Human-readable tool name")),
                ("description", models.TextField(blank=True, help_text="Tool description")),
                (
                    "version",
                    models.CharField(
                        max_length=20,
                        default="1.0.0",
                        help_text="Semantic version string",
                    ),
                ),
                (
                    "input_schema",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="JSON Schema for tool inputs",
                    ),
                ),
                (
                    "output_schema",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="JSON Schema for tool outputs",
                    ),
                ),
                (
                    "endpoint",
                    models.CharField(
                        max_length=500,
                        blank=True,
                        help_text="URL or internal path to invoke the tool",
                    ),
                ),
                (
                    "rate_limit_max_calls",
                    models.IntegerField(
                        default=100,
                        help_text="Max calls per rate limit window",
                    ),
                ),
                (
                    "rate_limit_window_seconds",
                    models.IntegerField(
                        default=3600,
                        help_text="Rate limit window in seconds",
                    ),
                ),
                (
                    "timeout_ms",
                    models.IntegerField(
                        default=30000,
                        help_text="Execution timeout in milliseconds",
                    ),
                ),
                (
                    "cost_per_call",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=6,
                        default=0.01,
                        help_text="Cost in dollars per invocation",
                    ),
                ),
                (
                    "invocation_input",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Input params for an invocation",
                    ),
                ),
                (
                    "invocation_output",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Output result for an invocation",
                    ),
                ),
                (
                    "success",
                    models.BooleanField(
                        null=True,
                        blank=True,
                        help_text="Whether the invocation succeeded",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True,
                        help_text="Error text if the invocation failed",
                    ),
                ),
                (
                    "duration_ms",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        help_text="Actual execution duration in milliseconds",
                    ),
                ),
                (
                    "called_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the tool was invoked",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_mcp_tool_call",
                "verbose_name": "MCP Tool Call",
                "verbose_name_plural": "MCP Tool Calls",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "tool_id"]),
                    models.Index(fields=["agent", "tool_id", "-created_at"]),
                    models.Index(fields=["agent", "success"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AgentLearningLoop",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "agent",
                    models.ForeignKey(
                        to="ai_agents.AIAgent",
                        on_delete=models.CASCADE,
                        related_name="learning_loops",
                        help_text="The agent whose strategy was updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "analysis_period_days",
                    models.IntegerField(
                        default=30,
                        help_text="Number of days of history analyzed",
                    ),
                ),
                (
                    "tasks_analyzed",
                    models.IntegerField(
                        default=0,
                        help_text="Number of tasks included in the analysis",
                    ),
                ),
                (
                    "success_patterns",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Patterns extracted from successful tasks",
                    ),
                ),
                (
                    "failure_patterns",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Patterns extracted from failed tasks",
                    ),
                ),
                (
                    "prompt_adjustments",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="System prompt changes applied",
                    ),
                ),
                (
                    "ab_test_enabled",
                    models.BooleanField(
                        default=False,
                        help_text="Whether A/B testing is active",
                    ),
                ),
                (
                    "ab_test_config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="A/B test configuration",
                    ),
                ),
                (
                    "strategy_score",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=3,
                        default=0.5,
                        help_text="Overall strategy effectiveness score (0.0 to 1.0)",
                    ),
                ),
                (
                    "applied_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the strategy update was applied",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_agent_learning_loop",
                "verbose_name": "Agent Learning Loop",
                "verbose_name_plural": "Agent Learning Loops",
                "ordering": ["-applied_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "agent", "-applied_at"]),
                    models.Index(fields=["agent", "strategy_score"]),
                ],
            },
        ),
    ]
