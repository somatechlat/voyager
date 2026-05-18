"""Pydantic models for Voyant API request/response validation.

These models mirror the Ninja schemas defined in the Voyant source:

* ``apps/analysis/api.py`` — AnalyzeRequest, AnalyzeResponse
* ``apps/sql/api.py``      — SqlRequest, SqlResponse
* ``apps/search/api.py``   — SearchQuery, SemanticSearchResult, IndexResponse
* ``apps/scraper/api.py``  — ScrapeJobSchema, ScrapeResultSchema, ScrapeArtifactSchema
* ``apps/workflows/api.py`` — JobResponse, ArtifactInfo
* ``apps/ingestion/api.py`` — JobResponse (ingestion variant)
* ``apps/discovery/api.py`` — SourceResponse, DiscoverResponse

All models use Pydantic v2 ``BaseModel`` with strict type checking.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────


class JobStatus(str, Enum):  # noqa: UP042
    """Job status values returned by Voyant workflows."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapeJobStatus(str, Enum):  # noqa: UP042
    """Scrape-specific job status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ─────────────────────────────────────────────────────────────
# Data Ingestion models
# ─────────────────────────────────────────────────────────────


class IngestJobRequest(BaseModel):
    """Request body for ``POST /api/v1/jobs/ingest``.

    Mirrors ``apps.workflows.api.IngestRequest``.
    """

    source_id: str = Field(..., description="ID of the data source to ingest from")
    mode: str = Field(default="full", description="Ingestion mode: full|incremental")
    tables: list[str] | None = Field(
        default=None, description="Optional list of table names to ingest"
    )


class IngestJobResponse(BaseModel):
    """Response body for ingestion job operations.

    Mirrors ``apps.workflows.api.JobResponse`` and
    ``apps.ingestion.api.JobResponse``.
    """

    job_id: str = Field(..., description="Unique job identifier (UUID)")
    tenant_id: str = Field(..., description="Tenant that owns the job")
    status: str = Field(..., description="Current job status")
    progress: float = Field(default=0.0, description="Progress from 0.0 to 1.0")
    stage: str = Field(default="queued", description="Current execution stage")
    created_at: str | None = Field(default=None, description="Creation ISO timestamp")
    started_at: str | None = Field(default=None, description="Start ISO timestamp")
    completed_at: str | None = Field(default=None, description="Completion ISO timestamp")
    result_summary: dict[str, Any] | None = Field(
        default=None, description="Summary of results when completed"
    )
    error_message: str | None = Field(default=None, description="Error message if failed")


# ─────────────────────────────────────────────────────────────
# Analysis models
# ─────────────────────────────────────────────────────────────


class KPIQuery(BaseModel):
    """KPI query definition for analysis requests.

    Mirrors ``apps.analysis.api.KPIQuery``.
    """

    name: str = Field(..., description="Human-readable KPI name")
    sql: str = Field(..., description="SQL query that computes the KPI")


class AnalyzeRequest(BaseModel):
    """Request body for ``POST /api/v1/analyze``.

    Mirrors ``apps.analysis.api.AnalyzeRequest``.
    """

    source_id: str | None = Field(default=None, description="Data source identifier")
    table: str | None = Field(default=None, description="Target table name")
    tables: list[str] | None = Field(default=None, description="Multiple table names")
    sample_size: int = Field(default=10000, ge=100, le=1000000)
    kpis: list[KPIQuery] | None = Field(default=None, description="Custom KPI queries")
    analyzers: list[str] | None = Field(default=None, description="List of analyzer names to run")
    analyzer_context: dict[str, Any] | None = Field(
        default=None, description="Extra context passed to analyzers"
    )
    profile: bool = Field(default=True, description="Run profiling step")
    run_analyzers: bool = Field(default=True, description="Run analyzer step")
    generate_artifacts: bool = Field(default=True, description="Generate output artifacts")


class AnalyzeResponse(BaseModel):
    """Response body for ``POST /api/v1/analyze``.

    Mirrors ``apps.analysis.api.AnalyzeResponse``.
    """

    job_id: str = Field(..., description="UUID of the created analysis job")
    tenant_id: str = Field(..., description="Tenant identifier")
    status: str = Field(..., description="Job status")
    summary: dict[str, Any] = Field(
        default_factory=dict, description="Analysis summary with KPIs and statistics"
    )
    artifacts: dict[str, Any] = Field(
        default_factory=dict, description="Generated artifact references"
    )
    manifest: list[dict[str, Any]] = Field(
        default_factory=list, description="List of executed analysis steps"
    )


# ─────────────────────────────────────────────────────────────
# SQL execution models
# ─────────────────────────────────────────────────────────────


class SQLExecuteRequest(BaseModel):
    """Request body for ``POST /api/v1/sql/query``.

    Mirrors ``apps.sql.api.SqlRequest``.
    """

    sql: str = Field(..., description="SQL query string. Only SELECT queries are permitted.")
    limit: int = Field(default=1000, ge=1, le=10000, description="Max rows to return")
    parameters: dict[str, Any] | None = Field(
        default=None, description="Optional parameterized query values"
    )


class SQLExecuteResponse(BaseModel):
    """Response body for ``POST /api/v1/sql/query``.

    Mirrors ``apps.sql.api.SqlResponse``.
    """

    columns: list[str] = Field(..., description="Column names from the query result")
    rows: list[list[Any]] = Field(..., description="Result rows as lists of values")
    row_count: int = Field(..., description="Number of rows returned")
    truncated: bool = Field(..., description="True if results were truncated")
    execution_time_ms: int = Field(..., description="Query execution time in ms")
    query_id: str | None = Field(default=None, description="Trino query ID")


class SQLTableListResponse(BaseModel):
    """Response body for ``GET /api/v1/sql/tables``."""

    tables: list[str] = Field(default_factory=list, description="Available table names")
    schema: str | None = Field(default=None, description="Schema that was queried")


class SQLColumnInfo(BaseModel):
    """Column metadata from ``GET /api/v1/sql/tables/{table}/columns``."""

    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type")
    nullable: bool = Field(default=True, description="Whether the column allows NULL")


# ─────────────────────────────────────────────────────────────
# Semantic search models
# ─────────────────────────────────────────────────────────────


class SearchQueryRequest(BaseModel):
    """Request body for ``POST /api/v1/search/query``.

    Mirrors ``apps.search.api.SearchQuery``.
    """

    query: str = Field(..., min_length=1, max_length=10000, description="Search query text")
    limit: int = Field(default=5, ge=1, le=100, description="Max results to return")
    filters: dict[str, Any] | None = Field(default=None, description="Optional metadata filters")


class SemanticSearchResult(BaseModel):
    """Single search result from ``POST /api/v1/search/query``.

    Mirrors ``apps.search.api.SemanticSearchResult``.
    """

    id: str = Field(..., description="Unique identifier of the indexed item")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score (higher = more similar)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata associated with the item"
    )


class IndexRequest(BaseModel):
    """Request body for ``POST /api/v1/search/index``.

    Mirrors ``apps.search.api.IndexRequest``.
    """

    text: str = Field(..., min_length=1, max_length=100000, description="Text content to index")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata to store with the item"
    )
    item_id: str | None = Field(
        default=None, description="Optional custom ID (auto-generated if omitted)"
    )


class IndexResponse(BaseModel):
    """Response body for ``POST /api/v1/search/index``.

    Mirrors ``apps.search.api.IndexResponse``.
    """

    id: str = Field(..., description="Assigned item identifier")
    status: str = Field(..., description="Indexing operation status")
    dimensions: int = Field(..., description="Embedding vector dimensionality")


class EmbedResponse(BaseModel):
    """Response body for embedding generation."""

    embedding: list[float] = Field(..., description="Dense vector representation")
    dimensions: int = Field(..., description="Vector dimensionality")
    model: str = Field(default="tfidf", description="Embedding model used")


# ─────────────────────────────────────────────────────────────
# Web scraping models
# ─────────────────────────────────────────────────────────────


class ScrapeStartRequest(BaseModel):
    """Request body for ``POST /api/v1/scrape/start``.

    Mirrors ``apps.scraper.api.ScrapeStartSchema``.
    """

    urls: list[str] = Field(..., description="URLs to scrape")
    selectors: dict[str, Any] | None = Field(
        default=None, description="CSS/XPath selectors for data extraction"
    )
    options: dict[str, Any] | None = Field(
        default=None,
        description="Scrape options: engine, timeout, scroll, wait_for, ocr",
    )


class ScrapeArtifact(BaseModel):
    """Artifact produced by a scrape job.

    Mirrors ``apps.scraper.api.ScrapeArtifactSchema``.
    """

    artifact_id: str = Field(..., description="Unique artifact identifier")
    artifact_type: str = Field(..., description="Type: html, screenshot, json, pdf")
    format: str = Field(..., description="File format extension")
    storage_path: str = Field(..., description="MinIO/storage path to the artifact")
    size_bytes: int | None = Field(default=None, description="Artifact size in bytes")
    content_hash: str | None = Field(default=None, description="SHA-256 content hash")


class ScrapeJobResponse(BaseModel):
    """Response body for scrape job status.

    Mirrors ``apps.scraper.api.ScrapeJobSchema``.
    """

    job_id: str = Field(..., description="Scrape job UUID")
    status: str = Field(..., description="Job status")
    pages_fetched: int = Field(default=0, description="Number of pages fetched")
    bytes_processed: int = Field(default=0, description="Total bytes processed")
    artifact_count: int = Field(default=0, description="Number of artifacts produced")
    error_count: int = Field(default=0, description="Number of errors encountered")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    started_at: str | None = Field(default=None, description="Start timestamp")
    finished_at: str | None = Field(default=None, description="Finish timestamp")
    error_message: str | None = Field(default=None, description="Error message if failed")


class ScrapeResultResponse(BaseModel):
    """Response body for ``GET /api/v1/scrape/result/{job_id}``.

    Mirrors ``apps.scraper.api.ScrapeResultSchema``.
    """

    job_id: str = Field(..., description="Scrape job UUID")
    status: str = Field(..., description="Job status")
    artifacts: list[ScrapeArtifact] = Field(default_factory=list, description="Produced artifacts")


class OCRRequest(BaseModel):
    """Request body for ``POST /api/v1/scrape/ocr``.

    Mirrors ``apps.scraper.api.ScrapeOcrSchema``.
    """

    image_url: str = Field(..., description="URL or MinIO path to the image")
    language: str = Field(default="spa+eng", description="OCR language pack")


class OCRResponse(BaseModel):
    """Response body for OCR processing."""

    text: str = Field(..., description="Extracted text from the image")
    language: str = Field(default="spa+eng", description="Language used")
    confidence: float | None = Field(default=None, description="OCR confidence score")


# ─────────────────────────────────────────────────────────────
# Data source / discovery models
# ─────────────────────────────────────────────────────────────


class SourceResponse(BaseModel):
    """Response body for source operations.

    Mirrors ``apps.discovery.api.SourceResponse``.
    """

    source_id: str = Field(..., description="Source UUID")
    tenant_id: str = Field(..., description="Tenant identifier")
    name: str = Field(..., description="Human-readable source name")
    source_type: str = Field(..., description="Connector type")
    status: str = Field(..., description="Source status")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    datahub_urn: str | None = Field(default=None, description="DataHub URN if registered")


# ─────────────────────────────────────────────────────────────
# Health model
# ─────────────────────────────────────────────────────────────


class HealthCheckResponse(BaseModel):
    """Response body for ``GET /health``."""

    status: str = Field(..., description="'healthy' or 'degraded'")
    version: str = Field(..., description="Voyant build version")
    checks: dict[str, bool] = Field(
        default_factory=dict, description="Named dependency health flags"
    )
