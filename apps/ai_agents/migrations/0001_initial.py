# Generated initial migration for ai_agents


from django.db import migrations, models


class AgentType(models.TextChoices):
    CREATIVE = "creative", "Creative"
    ANALYST = "analyst", "Analyst"
    OPTIMIZER = "optimizer", "Optimizer"
    RESEARCHER = "researcher", "Researcher"
    COORDINATOR = "coordinator", "Coordinator"


class Status(models.TextChoices):
    IDLE = "idle", "Idle"
    RUNNING = "running", "Running"
    PAUSED = "paused", "Paused"
    SUSPENDED = "suspended", "Suspended"
    ERROR = "error", "Error"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AIAgent",
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
                ("name", models.CharField(max_length=255, help_text="Human-readable agent name")),
                (
                    "agent_type",
                    models.CharField(
                        max_length=20,
                        choices=AgentType.choices,
                        help_text="Agent role determining default capabilities and resource budgets",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.IDLE,
                        help_text="Current lifecycle status",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        help_text="Agent configuration: model, temperature, max_tokens, system_prompt, tools, memory_enabled",
                    ),
                ),
                (
                    "resources",
                    models.JSONField(
                        default=dict,
                        help_text="Resource budget and usage: max_api_calls, max_memory_mb, max_cost_per_day, used counters",
                    ),
                ),
                (
                    "schedule",
                    models.CharField(
                        max_length=100,
                        blank=True,
                        help_text="Optional cron expression for scheduled runs",
                    ),
                ),
                (
                    "last_run_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Timestamp of the most recent execution",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the agent was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the agent was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_ai_agent",
                "verbose_name": "AI Agent",
                "verbose_name_plural": "AI Agents",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "agent_type"]),
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["agent_type", "status"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AgentResourceLimit",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "agent",
                    models.OneToOneField(
                        AIAgent,
                        on_delete=models.CASCADE,
                        related_name="resource_limit",
                        help_text="The agent these limits apply to",
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
                    "max_api_calls",
                    models.IntegerField(default=100, help_text="Daily API call budget"),
                ),
                (
                    "used_api_calls",
                    models.IntegerField(
                        default=0,
                        help_text="API calls consumed today",
                    ),
                ),
                (
                    "max_memory_mb",
                    models.IntegerField(
                        default=512,
                        help_text="Memory budget in megabytes",
                    ),
                ),
                (
                    "used_memory_mb",
                    models.IntegerField(
                        default=0,
                        help_text="Memory consumed in megabytes",
                    ),
                ),
                (
                    "max_cost_per_day",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=4,
                        default=5.0,
                        help_text="Daily cost budget in dollars",
                    ),
                ),
                (
                    "used_cost_today",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=4,
                        default=0.0,
                        help_text="Cost consumed today in dollars",
                    ),
                ),
                (
                    "throttle_factor",
                    models.DecimalField(
                        max_digits=3,
                        decimal_places=2,
                        default=1.0,
                        help_text="Current speed multiplier (1.0 = full speed, 0.25 = severely throttled)",
                    ),
                ),
                (
                    "last_reset_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When daily counters were last zeroed",
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
                "db_table": "voyager_agent_resource_limit",
                "verbose_name": "Agent Resource Limit",
                "verbose_name_plural": "Agent Resource Limits",
                "indexes": [models.Index(fields=["tenant_id", "agent"])],
            },
        ),
    ]
