"""Tests for AI Agents models: AIAgent, AgentMemory, MemoryEntry, AgentResourceLimit."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.ai_agents.models import AgentMemory, AgentResourceLimit, AIAgent, MemoryEntry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def ai_agent(tenant_id: str) -> AIAgent:
    """Create and return an AIAgent instance."""
    return AIAgent.objects.create(
        tenant_id=tenant_id,
        name="Creative Assistant",
        agent_type=AIAgent.AgentType.CREATIVE,
        status=AIAgent.Status.IDLE,
        config={
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4000,
            "system_prompt": "You are a creative marketing assistant.",
            "tools": ["image_gen", "text_gen"],
            "memory_enabled": True,
        },
        resources={
            "max_api_calls": 1000,
            "max_memory_mb": 512,
            "max_cost_per_day": 50.0,
            "used_api_calls": 0,
            "used_memory_mb": 0,
            "used_cost_today": 0.0,
        },
        schedule="0 9 * * *",
    )


@pytest.fixture
def agent_memory(ai_agent: AIAgent) -> AgentMemory:
    """Create and return an AgentMemory instance."""
    return AgentMemory.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        collection_name=f"agent_{ai_agent.id}_memory",
        vector_size=1536,
        distance_metric="cosine",
        total_vectors=0,
    )


@pytest.fixture
def memory_entry(ai_agent: AIAgent) -> MemoryEntry:
    """Create and return a MemoryEntry instance."""
    return MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="550e8400-e29b-41d4-a716-446655440001",
        content="User prefers short, punchy headlines with emojis.",
        importance=Decimal("0.850"),
        metadata={"source": "user_feedback", "task_type": "content_creation", "tags": ["style"]},
        access_count=5,
    )


@pytest.fixture
def agent_resource_limit(ai_agent: AIAgent) -> AgentResourceLimit:
    """Create and return an AgentResourceLimit instance."""
    return AgentResourceLimit.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        max_api_calls=1000,
        used_api_calls=250,
        max_memory_mb=512,
        used_memory_mb=128,
        max_cost_per_day=Decimal("50.0000"),
        used_cost_today=Decimal("12.5000"),
        throttle_factor=Decimal("1.00"),
    )


# ---------------------------------------------------------------------------
# AIAgent tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ai_agent_creation(ai_agent: AIAgent) -> None:
    """AIAgent can be created with all required fields."""
    assert ai_agent.id is not None
    assert ai_agent.name == "Creative Assistant"
    assert ai_agent.tenant_id == "test-tenant-001"
    assert ai_agent.agent_type == "creative"
    assert ai_agent.status == "idle"


@pytest.mark.django_db
def test_ai_agent_str(ai_agent: AIAgent) -> None:
    """String representation includes name and agent type."""
    assert str(ai_agent) == "Creative Assistant (creative)"


@pytest.mark.django_db
def test_ai_agent_defaults(tenant_id: str) -> None:
    """AIAgent fields have correct defaults."""
    agent = AIAgent.objects.create(
        tenant_id=tenant_id,
        name="Default Agent",
        agent_type=AIAgent.AgentType.ANALYST,
    )
    assert agent.status == AIAgent.Status.IDLE
    assert agent.config == {}
    assert agent.resources == {}
    assert agent.schedule == ""
    assert agent.last_run_at is None


@pytest.mark.django_db
def test_ai_agent_all_types(tenant_id: str) -> None:
    """All AgentType choices can be stored."""
    for value, _label in AIAgent.AgentType.choices:
        agent = AIAgent.objects.create(
            tenant_id=tenant_id,
            name=f"Agent {value}",
            agent_type=value,
        )
        assert agent.agent_type == value


@pytest.mark.django_db
def test_ai_agent_all_statuses(tenant_id: str) -> None:
    """All Status choices can be stored."""
    for value, _label in AIAgent.Status.choices:
        agent = AIAgent.objects.create(
            tenant_id=tenant_id,
            name=f"Agent {value}",
            agent_type=AIAgent.AgentType.ANALYST,
            status=value,
        )
        assert agent.status == value


@pytest.mark.django_db
def test_ai_agent_config_json(ai_agent: AIAgent) -> None:
    """config JSON stores agent configuration."""
    assert ai_agent.config["model"] == "gpt-4o"
    assert ai_agent.config["temperature"] == 0.7
    assert ai_agent.config["tools"] == ["image_gen", "text_gen"]
    assert ai_agent.config["memory_enabled"] is True


@pytest.mark.django_db
def test_ai_agent_resources_json(ai_agent: AIAgent) -> None:
    """resources JSON stores resource budget and usage."""
    assert ai_agent.resources["max_api_calls"] == 1000
    assert ai_agent.resources["max_memory_mb"] == 512
    assert ai_agent.resources["used_api_calls"] == 0


@pytest.mark.django_db
def test_ai_agent_schedule(tenant_id: str) -> None:
    """schedule stores a cron expression."""
    agent = AIAgent.objects.create(
        tenant_id=tenant_id,
        name="Scheduled Agent",
        agent_type=AIAgent.AgentType.COORDINATOR,
        schedule="*/15 * * * *",
    )
    assert agent.schedule == "*/15 * * * *"


@pytest.mark.django_db
def test_ai_agent_ordering(tenant_id: str) -> None:
    """AIAgents are ordered by created_at descending."""
    AIAgent.objects.create(
        tenant_id=tenant_id,
        name="First Agent",
        agent_type=AIAgent.AgentType.ANALYST,
    )
    AIAgent.objects.create(
        tenant_id=tenant_id,
        name="Second Agent",
        agent_type=AIAgent.AgentType.ANALYST,
    )
    agents = list(AIAgent.objects.all())
    assert agents[0].name == "Second Agent"
    assert agents[1].name == "First Agent"


# ---------------------------------------------------------------------------
# AgentMemory tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_agent_memory_creation(agent_memory: AgentMemory) -> None:
    """AgentMemory can be created linked to an AIAgent."""
    assert agent_memory.id is not None
    assert agent_memory.agent is not None
    assert agent_memory.collection_name == f"agent_{agent_memory.agent.id}_memory"
    assert agent_memory.vector_size == 1536
    assert agent_memory.distance_metric == "cosine"
    assert agent_memory.total_vectors == 0


@pytest.mark.django_db
def test_agent_memory_str(agent_memory: AgentMemory) -> None:
    """String representation includes agent name and collection name."""
    rep = str(agent_memory)
    assert "Creative Assistant" in rep
    assert agent_memory.collection_name in rep


@pytest.mark.django_db
def test_agent_memory_defaults(ai_agent: AIAgent) -> None:
    """AgentMemory fields have correct defaults."""
    am = AgentMemory.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        collection_name=f"agent_{ai_agent.id}_default",
    )
    assert am.vector_size == 1536
    assert am.distance_metric == "cosine"
    assert am.total_vectors == 0
    assert am.last_consolidated_at is None


@pytest.mark.django_db
def test_agent_memory_unique_collection_name(
    ai_agent: AIAgent,
    tenant_id: str,
) -> None:
    """Duplicate collection_name raises IntegrityError."""
    AgentMemory.objects.create(
        agent=ai_agent,
        tenant_id=tenant_id,
        collection_name="unique-collection",
    )
    other_agent = AIAgent.objects.create(
        tenant_id=tenant_id,
        name="Other Agent",
        agent_type=AIAgent.AgentType.RESEARCHER,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AgentMemory.objects.create(
                agent=other_agent,
                tenant_id=tenant_id,
                collection_name="unique-collection",
            )


@pytest.mark.django_db
def test_agent_memory_related_to_agent(agent_memory: AgentMemory) -> None:
    """AgentMemory is linked to AIAgent via one-to-one."""
    assert agent_memory.agent.memory == agent_memory


# ---------------------------------------------------------------------------
# MemoryEntry tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_memory_entry_creation(memory_entry: MemoryEntry) -> None:
    """MemoryEntry can be created with all required fields."""
    assert memory_entry.id is not None
    assert memory_entry.agent is not None
    assert memory_entry.qdrant_id == "550e8400-e29b-41d4-a716-446655440001"
    assert memory_entry.content == "User prefers short, punchy headlines with emojis."
    assert memory_entry.importance == Decimal("0.850")
    assert memory_entry.access_count == 5
    assert memory_entry.is_active is True


@pytest.mark.django_db
def test_memory_entry_str(memory_entry: MemoryEntry) -> None:
    """String representation includes qdrant_id prefix and agent name."""
    rep = str(memory_entry)
    assert "550e8400" in rep
    assert "Creative Assistant" in rep


@pytest.mark.django_db
def test_memory_entry_defaults(ai_agent: AIAgent) -> None:
    """MemoryEntry fields have correct defaults."""
    me = MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="550e8400-e29b-41d4-a716-446655440002",
        content="Default memory content.",
    )
    assert me.importance == Decimal("0.500")
    assert me.metadata == {}
    assert me.access_count == 0
    assert me.is_active is True


@pytest.mark.django_db
def test_memory_entry_importance_range(ai_agent: AIAgent) -> None:
    """importance can range from 0.0 to 1.0."""
    low = MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="low-uuid-here-0000-000000000001",
        content="Low importance.",
        importance=Decimal("0.001"),
    )
    high = MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="high-uuid-here-0000-000000000001",
        content="High importance.",
        importance=Decimal("0.999"),
    )
    assert low.importance == Decimal("0.001")
    assert high.importance == Decimal("0.999")


@pytest.mark.django_db
def test_memory_entry_metadata_json(ai_agent: AIAgent) -> None:
    """metadata JSON stores source, task_type and tags."""
    me = MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="meta-uuid-here-0000-000000000001",
        content="Tagged memory.",
        metadata={
            "source": "conversation",
            "task_type": "optimization",
            "tags": ["conversion", "a/b-test"],
        },
    )
    assert me.metadata["source"] == "conversation"
    assert "conversion" in me.metadata["tags"]


@pytest.mark.django_db
def test_memory_entry_access_count_increment(memory_entry: MemoryEntry) -> None:
    """access_count can be incremented."""
    original = memory_entry.access_count
    memory_entry.access_count += 1
    memory_entry.save()
    memory_entry.refresh_from_db()
    assert memory_entry.access_count == original + 1


@pytest.mark.django_db
def test_memory_entry_inactive(ai_agent: AIAgent) -> None:
    """MemoryEntry can be marked inactive for forgetting."""
    me = MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="inactive-uuid-0000-000000000001",
        content="To be forgotten.",
        is_active=False,
    )
    assert me.is_active is False


@pytest.mark.django_db
def test_memory_entry_related_to_agent(
    ai_agent: AIAgent,
    memory_entry: MemoryEntry,
) -> None:
    """MemoryEntry is linked to AIAgent via foreign key."""
    assert memory_entry.agent == ai_agent
    assert ai_agent.memory_entries.count() >= 1
    assert memory_entry in list(ai_agent.memory_entries.all())


@pytest.mark.django_db
def test_memory_entry_ordering(ai_agent: AIAgent) -> None:
    """MemoryEntry entries are ordered by created_at descending."""
    MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="order-uuid-0001-000000000001",
        content="First entry.",
    )
    MemoryEntry.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        qdrant_id="order-uuid-0002-000000000001",
        content="Second entry.",
    )
    entries = list(MemoryEntry.objects.filter(agent=ai_agent))
    assert entries[0].content == "Second entry."


# ---------------------------------------------------------------------------
# AgentResourceLimit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_agent_resource_limit_creation(agent_resource_limit: AgentResourceLimit) -> None:
    """AgentResourceLimit can be created with all fields."""
    assert agent_resource_limit.id is not None
    assert agent_resource_limit.agent is not None
    assert agent_resource_limit.max_api_calls == 1000
    assert agent_resource_limit.used_api_calls == 250
    assert agent_resource_limit.max_memory_mb == 512
    assert agent_resource_limit.used_memory_mb == 128
    assert agent_resource_limit.max_cost_per_day == Decimal("50.0000")
    assert agent_resource_limit.used_cost_today == Decimal("12.5000")
    assert agent_resource_limit.throttle_factor == Decimal("1.00")


@pytest.mark.django_db
def test_agent_resource_limit_str(agent_resource_limit: AgentResourceLimit) -> None:
    """String representation includes agent name."""
    assert str(agent_resource_limit) == "Limits for Creative Assistant"


@pytest.mark.django_db
def test_agent_resource_limit_defaults(ai_agent: AIAgent) -> None:
    """AgentResourceLimit fields have correct defaults."""
    arl = AgentResourceLimit.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
    )
    assert arl.max_api_calls == 100
    assert arl.used_api_calls == 0
    assert arl.max_memory_mb == 512
    assert arl.used_memory_mb == 0
    assert arl.max_cost_per_day == Decimal("5.0000")
    assert arl.used_cost_today == Decimal("0.0000")
    assert arl.throttle_factor == Decimal("1.00")


@pytest.mark.django_db
def test_agent_resource_limit_throttled(ai_agent: AIAgent) -> None:
    """throttle_factor can be set below 1.0 when throttled."""
    arl = AgentResourceLimit.objects.create(
        agent=ai_agent,
        tenant_id=ai_agent.tenant_id,
        throttle_factor=Decimal("0.25"),
    )
    assert arl.throttle_factor == Decimal("0.25")


@pytest.mark.django_db
def test_agent_resource_limit_related_to_agent(
    agent_resource_limit: AgentResourceLimit,
) -> None:
    """AgentResourceLimit is linked to AIAgent via one-to-one."""
    assert agent_resource_limit.agent.resource_limit == agent_resource_limit


@pytest.mark.django_db
def test_agent_resource_limit_api_usage_percentage(
    agent_resource_limit: AgentResourceLimit,
) -> None:
    """API usage is 25% of max."""
    pct = (agent_resource_limit.used_api_calls / agent_resource_limit.max_api_calls) * 100
    assert pct == 25.0


@pytest.mark.django_db
def test_agent_resource_limit_memory_usage_percentage(
    agent_resource_limit: AgentResourceLimit,
) -> None:
    """Memory usage is 25% of max."""
    pct = (agent_resource_limit.used_memory_mb / agent_resource_limit.max_memory_mb) * 100
    assert pct == 25.0


@pytest.mark.django_db
def test_agent_resource_limit_cost_usage(
    agent_resource_limit: AgentResourceLimit,
) -> None:
    """Cost usage can be tracked against daily budget."""
    assert agent_resource_limit.used_cost_today <= agent_resource_limit.max_cost_per_day
    remaining = agent_resource_limit.max_cost_per_day - agent_resource_limit.used_cost_today
    assert remaining == Decimal("37.5000")
