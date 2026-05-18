"""Memory models for agent persistent memory via Qdrant vector store."""

from __future__ import annotations

from django.db import models


class AgentMemory(models.Model):
    """Reference to an agent's memory collection in Qdrant vector store.

    Each agent has one memory record that tracks the Qdrant collection name
    and high-level memory statistics.

    Attributes:
        id: Auto-incrementing primary key.
        agent: The agent whose memory this represents.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        collection_name: Qdrant collection identifier for this agent's vectors.
        vector_size: Embedding dimension size (default 1536).
        distance_metric: Distance metric used in Qdrant (cosine, euclidean, dot).
        total_vectors: Approximate number of vectors stored.
        last_consolidated_at: When memory consolidation last ran.
        created_at: Creation timestamp.
        updated_at: Last-update timestamp.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    agent = models.OneToOneField(
        "ai_agents.AIAgent",
        on_delete=models.CASCADE,
        related_name="memory",
        help_text="The agent whose memory this represents",
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    collection_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Qdrant collection identifier for this agent's vectors",
    )
    vector_size = models.IntegerField(default=1536, help_text="Embedding dimension size")
    distance_metric = models.CharField(
        max_length=20, default="cosine", help_text="Distance metric used in Qdrant"
    )
    total_vectors = models.IntegerField(default=0, help_text="Approximate number of vectors stored")
    last_consolidated_at = models.DateTimeField(
        null=True, blank=True, help_text="When memory consolidation last ran"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_agent_memory"
        verbose_name = "Agent Memory"
        verbose_name_plural = "Agent Memories"
        indexes = [
            models.Index(fields=["tenant_id", "collection_name"]),
        ]

    def __str__(self) -> str:
        return f"Memory for {self.agent.name} ({self.collection_name})"


class MemoryEntry(models.Model):
    """Individual memory entry stored in Qdrant with local metadata cache.

    The actual embedding vector lives in Qdrant; this model caches metadata
    for fast local queries without hitting the vector store.

    Attributes:
        id: Auto-incrementing primary key.
        agent: The agent this memory belongs to.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        qdrant_id: UUID of the corresponding point in Qdrant.
        content: The textual content of the memory chunk.
        importance: Importance score from 0.0 to 1.0.
        metadata: JSON metadata (source, task_type, tags).
        access_count: Number of times this memory was retrieved.
        last_accessed: Timestamp of last access.
        is_active: Whether the entry is active (False if marked for forgetting).
        created_at: Creation timestamp.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    agent = models.ForeignKey(
        "ai_agents.AIAgent",
        on_delete=models.CASCADE,
        related_name="memory_entries",
        help_text="The agent this memory belongs to",
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    qdrant_id = models.CharField(
        max_length=64, db_index=True, help_text="UUID of the corresponding point in Qdrant"
    )
    content = models.TextField(help_text="The textual content of the memory chunk")
    importance = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=0.500,
        help_text="Importance score from 0.0 to 1.0",
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="JSON metadata: source, task_type, tags"
    )
    access_count = models.IntegerField(
        default=0, help_text="Number of times this memory was retrieved"
    )
    last_accessed = models.DateTimeField(auto_now_add=True, help_text="Timestamp of last access")
    is_active = models.BooleanField(default=True, help_text="Whether the entry is active")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the memory was created"
    )

    class Meta:
        db_table = "voyager_memory_entry"
        verbose_name = "Memory Entry"
        verbose_name_plural = "Memory Entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent", "is_active", "-importance"]),
            models.Index(fields=["agent", "-created_at"]),
            models.Index(fields=["tenant_id", "agent"]),
        ]

    def __str__(self) -> str:
        return f"MemoryEntry {self.qdrant_id[:8]} for {self.agent.name}"
