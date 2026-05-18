"""Initial migration for AI Agents module.

Creates all tables: agents, agent_resource_limits, agent_memories,
memory_entries, agent_contexts, agent_collaborations, mcp_tool_calls,
and agent_learning_loops.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Initial migration for the AI Agents Django app."""

    initial = True

    dependencies = []

    operations = [
        # AIAgent — core agent table
        migrations.CreateModel(
            name="AIAgent",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                ("name", models.CharField(help_text="Human-readable agent name", max_length=255)),
                (
                    "agent_type",
                    models.CharField(
                        choices=[
                            ("creative", "Creative"),
                            ("analyst", "Analyst"),
                            ("optimizer", "Optimizer"),
                            ("researcher", "Researcher"),
                            ("coordinator", "Coordinator"),
                        ],
                        help_text="Agent role determining default capabilities and resource budgets",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("idle", "Idle"),
                            ("running", "Running"),
                            ("paused", "Paused"),
                            ("suspended", "Suspended"),
                            ("error", "Error"),
                        ],
                        default="idle",
                        help_text="Current lifecycle status",
                        max_length=20,
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
                ("schedule", models.CharField(blank=True, help_text="Optional cron expression for scheduled runs", max_length=100)),
                ("last_run_at", models.DateTimeField(blank=True, help_text="Timestamp of the most recent execution", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when the agent was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when the agent was last updated")),
            ],
            options={
                "db_table": "voyager_ai_agent",
                "verbose_name": "AI Agent",
                "verbose_name_plural": "AI Agents",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="aiagent",
            index=models.Index(fields=["tenant_id", "agent_type"], name="voyager_aai_tenant_type_idx"),
        ),
        migrations.AddIndex(
            model_name="aiagent",
            index=models.Index(fields=["tenant_id", "status"], name="voyager_aai_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="aiagent",
            index=models.Index(fields=["agent_type", "status"], name="voyager_aai_type_status_idx"),
        ),

        # AgentResourceLimit — resource limits per agent
        migrations.CreateModel(
            name="AgentResourceLimit",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                (
                    "agent",
                    models.OneToOneField(
                        help_text="The agent these limits apply to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resource_limit",
                        to="ai_agents.aiagent",
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                ("max_api_calls", models.IntegerField(default=100, help_text="Daily API call budget")),
                ("used_api_calls", models.IntegerField(default=0, help_text="API calls consumed today")),
                ("max_memory_mb", models.IntegerField(default=512, help_text="Memory budget in megabytes")),
                ("used_memory_mb", models.IntegerField(default=0, help_text="Memory consumed in megabytes")),
                ("max_cost_per_day", models.DecimalField(decimal_places=4, default=5.0000, help_text="Daily cost budget in dollars", max_digits=8)),
                ("used_cost_today", models.DecimalField(decimal_places=4, default=0.0000, help_text="Cost consumed today in dollars", max_digits=8)),
                ("throttle_factor", models.DecimalField(decimal_places=2, default=1.0, help_text="Current speed multiplier (1.0 = full speed, 0.25 = severely throttled)", max_digits=3)),
                ("last_reset_at", models.DateTimeField(auto_now_add=True, help_text="When daily counters were last zeroed")),
                ("created_at", models.DateTimeField(auto_now_add=True, help_text="Timestamp when the record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when the record was last updated")),
            ],
            options={
                "db_table": "voyager_agent_resource_limit",
                "verbose_name": "Agent Resource Limit",
                "verbose_name_plural": "Agent Resource Limits",
            },
        ),
        migrations.AddIndex(
            model_name="agentresourcelimit",
            index=models.Index(fields=["tenant_id", "agent"], name="voyager_arl_tenant_agent_idx"),
        ),

        # AgentMemory — Qdrant collection reference
        migrations.CreateModel(
            name="AgentMemory",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                (
                    "agent",
                    models.OneToOneField(
                        help_text="The agent whose memory this represents",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memory",
                        to="ai_agents.aiagent",
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                ("collection_name", models.CharField(help_text="Qdrant collection identifier for this agent's vectors", max_length=255, unique=True)),
                ("vector_size", models.IntegerField(default=1536, help_text="Embedding dimension size")),
                ("distance_metric", models.CharField(default="cosine", help_text="Distance metric used in Qdrant", max_length=20)),
                ("total_vectors", models.IntegerField(default=0, help_text="Approximate number of vectors stored")),
                ("last_consolidated_at", models.DateTimeField(blank=True, help_text="When memory consolidation last ran", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, help_text="Timestamp when the record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when the record was last updated")),
            ],
            options={
                "db_table": "voyager_agent_memory",
                "verbose_name": "Agent Memory",
                "verbose_name_plural": "Agent Memories",
            },
        ),
        migrations.AddIndex(
            model_name="agentmemory",
            index=models.Index(fields=["tenant_id", "collection_name"], name="voyager_am_tenant_coll_idx"),
        ),

        # MemoryEntry — cached memory metadata
        migrations.CreateModel(
            name="MemoryEntry",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                (
                    "agent",
                    models.ForeignKey(
                        help_text="The agent this memory belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memory_entries",
                        to="ai_agents.aiagent",
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                ("qdrant_id", models.CharField(db_index=True, help_text="UUID of the corresponding point in Qdrant", max_length=64)),
                ("content", models.TextField(help_text="The textual content of the memory chunk")),
                ("importance", models.DecimalField(decimal_places=3, default=0.5, help_text="Importance score from 0.0 to 1.0", max_digits=4)),
                ("metadata", models.JSONField(blank=True, default=dict, help_text="JSON metadata: source, task_type, tags")),
                ("access_count", models.IntegerField(default=0, help_text="Number of times this memory was retrieved")),
                ("last_accessed", models.DateTimeField(auto_now_add=True, help_text="Timestamp of last access")),
                ("is_active", models.BooleanField(default=True, help_text="Whether the entry is active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when the memory was created")),
            ],
            options={
                "db_table": "voyager_memory_entry",
                "verbose_name": "Memory Entry",
                "verbose_name_plural": "Memory Entries",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="memoryentry",
            index=models.Index(fields=["agent", "is_active", "-importance"], name="voyager_me_agent_active_imp_idx"),
        ),
        migrations.AddIndex(
            model_name="memoryentry",
            index=models.Index(fields=["agent", "-created_at"], name="voyager_me_agent_created_idx"),
        ),
        migrations.AddIndex(
            model_name="memoryentry",
            index=models.Index(fields=["tenant_id", "agent"], name="voyager_me_tenant_agent_idx"),
        ),

        # AgentContext — assembled context snapshots
        migrations.CreateModel(
            name="AgentContext",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                (
                    "agent",
                    models.ForeignKey(
                        help_text="The agent this context was assembled for",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contexts",
                        to="ai_agents.aiagent",
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                ("task_type", models.CharField(help_text="The type of task being executed", max_length=50)),
                ("brand_context", models.JSONField(blank=True, default=dict, help_text="Brand guidelines snapshot")),
                ("audience_context", models.JSONField(blank=True, default=dict, help_text="Audience personas snapshot")),
                ("performance_context", models.JSONField(blank=True, default=dict, help_text="Recent performance data snapshot")),
                ("memory_ids", models.JSONField(blank=True, default=list, help_text="List of memory entry IDs included in context")),
                ("current_state", models.JSONField(blank=True, default=dict, help_text="Active campaigns, scheduled content, pending approvals")),
                ("assembled_at", models.DateTimeField(auto_now_add=True, help_text="When the context was assembled")),
                ("token_estimate", models.IntegerField(default=0, help_text="Estimated token count of the assembled context")),
                ("created_at", models.DateTimeField(auto_now_add=True, help_text="Timestamp when the record was created")),
            ],
            options={
                "db_table": "voyager_agent_context",
                "verbose_name": "Agent Context",
                "verbose_name_plural": "Agent Contexts",
                "ordering": ["-assembled_at"],
            },
        ),
        migrations.AddIndex(
            model_name="agentcontext",
            index=models.Index(fields=["tenant_id", "agent", "-assembled_at"], name="voyager_ac_tenant_agent_assemb_idx"),
        ),
        migrations.AddIndex(
            model_name="agentcontext",
            index=models.Index(fields=["agent", "task_type"], name="voyager_ac_agent_task_idx"),
        ),

        # AgentCollaboration — multi-agent collaboration sessions
        migrations.CreateModel(
            name="AgentCollaboration",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                (
                    "initiator_agent",
                    models.ForeignKey(
                        help_text="The agent that started the collaboration",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="initiated_collaborations",
                        to="ai_agents.aiagent",
                    ),
                ),
                ("task_id", models.CharField(help_text="Identifier of the task being collaborated on", max_length=128)),
                (
                    "pattern",
                    models.CharField(
                        choices=[
                            ("pipeline", "Pipeline"),
                            ("fan_out", "Fan-out"),
                            ("fan_in", "Fan-in"),
                            ("review", "Review"),
                            ("debate", "Debate"),
                        ],
                        help_text="Collaboration pattern used",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        help_text="Current status of the collaboration",
                        max_length=20,
                    ),
                ),
                ("delegation_chain", models.JSONField(default=list, help_text="Ordered list of agent IDs in the delegation chain")),
                ("max_depth", models.IntegerField(default=5, help_text="Maximum allowed delegation depth")),
                ("messages", models.JSONField(blank=True, default=list, help_text="JSON log of inter-agent messages")),
                ("started_at", models.DateTimeField(blank=True, help_text="When the collaboration began", null=True)),
                ("completed_at", models.DateTimeField(blank=True, help_text="When the collaboration finished", null=True)),
                ("result_summary", models.JSONField(blank=True, default=dict, help_text="JSON summary of the collaboration outcome")),
                ("created_at", models.DateTimeField(auto_now_add=True, help_text="Timestamp when the record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when the record was last updated")),
            ],
            options={
                "db_table": "voyager_agent_collaboration",
                "verbose_name": "Agent Collaboration",
                "verbose_name_plural": "Agent Collaborations",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="agentcollaboration",
            index=models.Index(fields=["tenant_id", "status"], name="voyager_acol_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="agentcollaboration",
            index=models.Index(fields=["initiator_agent", "status"], name="voyager_acol_initiator_status_idx"),
        ),
        migrations.AddIndex(
            model_name="agentcollaboration",
            index=models.Index(fields=["task_id"], name="voyager_acol_task_idx"),
        ),

        # MCPToolCall — tool registrations and invocations
        migrations.CreateModel(
            name="MCPToolCall",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                (
                    "agent",
                    models.ForeignKey(
                        help_text="The agent that registered or invoked this tool",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tool_calls",
                        to="ai_agents.aiagent",
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                ("tool_id", models.CharField(db_index=True, help_text="Unique tool identifier", max_length=128)),
                ("name", models.CharField(help_text="Human-readable tool name", max_length=255)),
                ("description", models.TextField(blank=True, help_text="Tool description")),
                ("version", models.CharField(default="1.0.0", help_text="Semantic version string", max_length=20)),
                ("input_schema", models.JSONField(blank=True, default=dict, help_text="JSON Schema for tool inputs")),
                ("output_schema", models.JSONField(blank=True, default=dict, help_text="JSON Schema for tool outputs")),
                ("endpoint", models.CharField(blank=True, help_text="URL or internal path to invoke the tool", max_length=500)),
                ("rate_limit_max_calls", models.IntegerField(default=100, help_text="Max calls per rate limit window")),
                ("rate_limit_window_seconds", models.IntegerField(default=3600, help_text="Rate limit window in seconds")),
                ("timeout_ms", models.IntegerField(default=30000, help_text="Execution timeout in milliseconds")),
                ("cost_per_call", models.DecimalField(decimal_places=6, default=0.01, help_text="Cost in dollars per invocation", max_digits=8)),
                ("invocation_input", models.JSONField(blank=True, default=dict, help_text="Input params for an invocation")),
                ("invocation_output", models.JSONField(blank=True, default=dict, help_text="Output result for an invocation")),
                ("success", models.BooleanField(blank=True, help_text="Whether the invocation succeeded", null=True)),
                ("error_message", models.TextField(blank=True, help_text="Error text if the invocation failed")),
                ("duration_ms", models.IntegerField(blank=True, help_text="Actual execution duration in milliseconds", null=True)),
                ("called_at", models.DateTimeField(blank=True, help_text="When the tool was invoked", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when the record was created")),
            ],
            options={
                "db_table": "voyager_mcp_tool_call",
                "verbose_name": "MCP Tool Call",
                "verbose_name_plural": "MCP Tool Calls",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="mcptoolcall",
            index=models.Index(fields=["tenant_id", "tool_id"], name="voyager_mcp_tenant_tool_idx"),
        ),
        migrations.AddIndex(
            model_name="mcptoolcall",
            index=models.Index(fields=["agent", "tool_id", "-created_at"], name="voyager_mcp_agent_tool_created_idx"),
        ),
        migrations.AddIndex(
            model_name="mcptoolcall",
            index=models.Index(fields=["agent", "success"], name="voyager_mcp_agent_success_idx"),
        ),

        # AgentLearningLoop — learning iterations
        migrations.CreateModel(
            name="AgentLearningLoop",
            fields=[
                ("id", models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                (
                    "agent",
                    models.ForeignKey(
                        help_text="The agent whose strategy was updated",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_loops",
                        to="ai_agents.aiagent",
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, help_text="Tenant identifier for multi-tenancy isolation", max_length=128)),
                ("analysis_period_days", models.IntegerField(default=30, help_text="Number of days of history analyzed")),
                ("tasks_analyzed", models.IntegerField(default=0, help_text="Number of tasks included in the analysis")),
                ("success_patterns", models.JSONField(blank=True, default=list, help_text="Patterns extracted from successful tasks")),
                ("failure_patterns", models.JSONField(blank=True, default=list, help_text="Patterns extracted from failed tasks")),
                ("prompt_adjustments", models.JSONField(blank=True, default=dict, help_text="System prompt changes applied")),
                ("ab_test_enabled", models.BooleanField(default=False, help_text="Whether A/B testing is active")),
                ("ab_test_config", models.JSONField(blank=True, default=dict, help_text="A/B test configuration")),
                ("strategy_score", models.DecimalField(decimal_places=3, default=0.5, help_text="Overall strategy effectiveness score (0.0 to 1.0)", max_digits=4)),
                ("applied_at", models.DateTimeField(auto_now_add=True, help_text="When the strategy update was applied")),
                ("created_at", models.DateTimeField(auto_now_add=True, help_text="Timestamp when the record was created")),
            ],
            options={
                "db_table": "voyager_agent_learning_loop",
                "verbose_name": "Agent Learning Loop",
                "verbose_name_plural": "Agent Learning Loops",
                "ordering": ["-applied_at"],
            },
        ),
        migrations.AddIndex(
            model_name="agentlearningloop",
            index=models.Index(fields=["tenant_id", "agent", "-applied_at"], name="voyager_al_tenant_agent_applied_idx"),
        ),
        migrations.AddIndex(
            model_name="agentlearningloop",
            index=models.Index(fields=["agent", "strategy_score"], name="voyager_al_agent_score_idx"),
        ),
    ]
