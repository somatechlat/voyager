"""Memory management schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema


class MemorySchema(Schema):
    """Agent memory collection reference."""

    id: int
    agent_id: int
    tenant_id: str
    collection_name: str
    vector_size: int
    distance_metric: str
    total_vectors: int
    last_consolidated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MemoryEntrySchema(Schema):
    """Individual memory entry."""

    id: int
    agent_id: int
    tenant_id: str
    qdrant_id: str
    content: str
    importance: float
    metadata: dict[str, Any]
    access_count: int
    last_accessed: datetime
    is_active: bool
    created_at: datetime


class StoreMemoryRequest(Schema):
    """Request body for storing a memory."""

    content: str
    metadata: dict[str, Any] = {}


class StoreMemoryResponse(Schema):
    """Response for memory storage."""

    chunks_stored: int
    qdrant_ids: list[str]


class SearchMemoryRequest(Schema):
    """Request body for memory search."""

    query: str
    top_k: int = 10


class SearchMemoryResult(Schema):
    """Single memory search result."""

    qdrant_id: str
    content: str
    importance: float
    access_count: int
    created_at: str
    final_score: float


class SearchMemoryResponse(Schema):
    """Response for memory search."""

    results: list[SearchMemoryResult]
    total: int


class ConsolidateMemoryResponse(Schema):
    """Response for memory consolidation."""

    consolidated: bool
    forgotten: int
    memories_remaining: int
