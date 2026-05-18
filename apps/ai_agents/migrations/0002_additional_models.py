# Generated initial migration for ai_agents


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("ai_agents", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="AgentMemory",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "agent",
                    models.OneToOneField(
                        to="ai_agents.AIAgent",
                        on_delete=models.CASCADE,
                        related_name="memory",
                        help_text="The agent whose memory this represents",
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
                    "collection_name",
                    models.CharField(
                        max_length=255,
                        unique=True,
                        help_text="Qdrant collection identifier for this agent's vectors",
                    ),
                ),
                (
                    "vector_size",
                    models.IntegerField(
                        default=1536,
                        help_text="Embedding dimension size",
                    ),
                ),
                (
                    "distance_metric",
                    models.CharField(
                        max_length=20,
                        default="cosine",
                        help_text="Distance metric used in Qdrant",
                    ),
                ),
                (
                    "total_vectors",
                    models.IntegerField(
                        default=0,
                        help_text="Approximate number of vectors stored",
                    ),
                ),
                (
                    "last_consolidated_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When memory consolidation last ran",
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
                "db_table": "voyager_agent_memory",
                "verbose_name": "Agent Memory",
                "verbose_name_plural": "Agent Memories",
                "indexes": [models.Index(fields=["tenant_id", "collection_name"])],
            },
        ),
        migrations.CreateModel(
            name="MemoryEntry",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "agent",
                    models.ForeignKey(
                        to="ai_agents.AIAgent",
                        on_delete=models.CASCADE,
                        related_name="memory_entries",
                        help_text="The agent this memory belongs to",
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
                    "qdrant_id",
                    models.CharField(
                        max_length=64,
                        db_index=True,
                        help_text="UUID of the corresponding point in Qdrant",
                    ),
                ),
                ("content", models.TextField(help_text="The textual content of the memory chunk")),
                (
                    "importance",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=3,
                        default=0.5,
                        help_text="Importance score from 0.0 to 1.0",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="JSON metadata: source, task_type, tags",
                    ),
                ),
                (
                    "access_count",
                    models.IntegerField(
                        default=0,
                        help_text="Number of times this memory was retrieved",
                    ),
                ),
                (
                    "last_accessed",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp of last access",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the entry is active",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the memory was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_memory_entry",
                "verbose_name": "Memory Entry",
                "verbose_name_plural": "Memory Entries",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["agent", "is_active", "-importance"]),
                    models.Index(fields=["agent", "-created_at"]),
                    models.Index(fields=["tenant_id", "agent"]),
                ],
            },
        ),
    ]
