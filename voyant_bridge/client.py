"""HTTP client for the Voyant data intelligence API (port 8000).

Provides an async interface to Voyant's REST endpoints for data ingestion,
statistical analysis, SQL execution (Trino), semantic search (Milvus), and
web scraping (Playwright/Tesseract).

Usage::

    from voyant_bridge.client import voyant_client
    job_id = await voyant_client.ingest_data(source_config, token)
    results = await voyant_client.execute_sql(query, catalog, token)
    memories = await voyant_client.search_similar(query, collection, limit, token)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class VoyantClient:
    """Async HTTP client for Voyant data intelligence API.

    Endpoints mirror the Ninja routers in ``apps/core/api.py``.

    :param base_url: Voyant HTTP base URL (default: ``http://voyant-api:8000``).
    :param timeout: Request timeout in seconds (default: ``30.0``).
    """

    BASE_URL: str = "http://voyant-api:8000"
    TIMEOUT: float = 30.0

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url: str = base_url or self.BASE_URL
        self.timeout: float = timeout or self.TIMEOUT
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
        )

    # ── Data Ingestion (apps.workflows.api jobs_router) ──────────────────

    async def ingest_data(self, source_config: dict[str, Any], token: str) -> str:
        """Submit a data ingestion job.

        Maps to ``POST /api/v1/jobs/ingest``.
        Used by: analytics_v2, integrations.

        :param source_config: Dict with ``source_id``, ``mode``,
            optional ``tables`` and ``tenant_id``.
        :param token: Bearer JWT token.
        :returns: UUID ``job_id`` assigned by Voyant.
        """
        payload: dict[str, Any] = {
            "source_id": source_config["source_id"],
            "mode": source_config.get("mode", "full"),
        }
        tables: list[str] | None = source_config.get("tables")
        if tables is not None:
            payload["tables"] = tables
        response = await self._client.post(
            f"{self.base_url}/api/v1/jobs/ingest",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": source_config.get("tenant_id", ""),
            },
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        job_id: str = data["job_id"]
        logger.info("Ingestion submitted: %s (status=%s)", job_id, data.get("status"))
        return job_id

    async def get_job_status(self, job_id: str, token: str) -> dict[str, Any]:
        """Check job status.

        Maps to ``GET /api/v1/jobs/{job_id}``.
        """
        response = await self._client.get(
            f"{self.base_url}/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def cancel_job(self, job_id: str, token: str) -> dict[str, str]:
        """Cancel a running job.

        Maps to ``POST /api/v1/jobs/{job_id}/cancel``.
        """
        response = await self._client.post(
            f"{self.base_url}/api/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    # ── Analysis (apps.analysis.api analyze_router) ──────────────────────

    async def analyze_data(self, dataset: dict[str, Any], token: str) -> dict[str, Any]:
        """Run statistical analysis on a dataset.

        Maps to ``POST /api/v1/analyze``.
        Used by: strategy, analytics_v2.

        :param dataset: Dict with ``source_id``/``table``, ``sample_size``,
            ``kpis``, ``analyzers``, ``analyzer_context``.
        :param token: Bearer JWT token.
        :returns: Dict with ``job_id``, ``status``, ``summary``,
            ``artifacts``, ``manifest``.
        """
        payload: dict[str, Any] = {}
        for key in (
            "source_id",
            "table",
            "tables",
            "sample_size",
            "kpis",
            "analyzers",
            "analyzer_context",
            "profile",
            "run_analyzers",
            "generate_artifacts",
        ):
            if key in dataset:
                payload[key] = dataset[key]
        response = await self._client.post(
            f"{self.base_url}/api/v1/analyze",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.info("Analysis started: %s", data.get("job_id"))
        return data

    # ── SQL Execution (apps.sql.api sql_router) ──────────────────────────

    async def execute_sql(
        self,
        query: str,
        catalog: str,
        token: str,
        limit: int = 1000,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute SQL via Trino.

        Maps to ``POST /api/v1/sql/query``.
        Used by: analytics_v2, campaigns.

        :param query: SQL SELECT statement.
        :param catalog: Trino catalog (e.g. ``"iceberg"``).
        :param token: Bearer JWT token.
        :param limit: Max rows (default: 1000).
        :param parameters: Optional parameterized values.
        :returns: Dict with ``columns``, ``rows``, ``row_count``,
            ``truncated``, ``execution_time_ms``, ``query_id``.
        """
        payload: dict[str, Any] = {"sql": query, "limit": limit}
        if parameters is not None:
            payload["parameters"] = parameters
        response = await self._client.post(
            f"{self.base_url}/api/v1/sql/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Trino-Catalog": catalog,
            },
        )
        response.raise_for_status()
        return response.json()

    async def list_tables(
        self,
        catalog: str,
        token: str,
        schema: str | None = None,
    ) -> dict[str, Any]:
        """List available tables via Trino.

        Maps to ``GET /api/v1/sql/tables``.
        """
        params: dict[str, Any] = {}
        if schema is not None:
            params["schema"] = schema
        response = await self._client.get(
            f"{self.base_url}/api/v1/sql/tables",
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Trino-Catalog": catalog,
            },
        )
        response.raise_for_status()
        return response.json()

    # ── Semantic Search (apps.search.api) ────────────────────────────────

    async def search_similar(
        self,
        query: str,
        collection: str,
        limit: int,
        token: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search via Milvus.

        Maps to ``POST /api/v1/search/query``.
        Used by: ai_agents (memory retrieval).

        :param query: Text query.
        :param collection: Collection to search.
        :param limit: Max results.
        :param token: Bearer JWT token.
        :param filters: Optional metadata filters.
        :returns: List of dicts with ``id``, ``score``, ``metadata``.
        """
        payload: dict[str, Any] = {"query": query, "limit": limit}
        if filters is not None:
            payload["filters"] = filters
        response = await self._client.post(
            f"{self.base_url}/api/v1/search/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Collection": collection,
            },
        )
        response.raise_for_status()
        return response.json()

    async def index_document(
        self,
        text: str,
        metadata: dict[str, Any] | None,
        token: str,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        """Index a document for semantic search.

        Maps to ``POST /api/v1/search/index``.
        """
        payload: dict[str, Any] = {"text": text}
        if metadata is not None:
            payload["metadata"] = metadata
        if item_id is not None:
            payload["item_id"] = item_id
        response = await self._client.post(
            f"{self.base_url}/api/v1/search/index",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def delete_indexed_document(self, item_id: str, token: str) -> dict[str, str]:
        """Delete an indexed document.

        Maps to ``DELETE /api/v1/search/{item_id}``.
        """
        response = await self._client.delete(
            f"{self.base_url}/api/v1/search/{item_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    # ── Web Scraping (apps.scraper.api) ──────────────────────────────────

    async def scrape_url(
        self,
        url: str,
        selectors: dict[str, Any] | None,
        token: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Start a scrape job for a URL.

        Maps to ``POST /api/v1/scrape/start``.
        Used by: web_scraping_v2, strategy.
        """
        payload: dict[str, Any] = {"urls": [url]}
        if selectors is not None:
            payload["selectors"] = selectors
        if options is not None:
            payload["options"] = options
        response = await self._client.post(
            f"{self.base_url}/api/v1/scrape/start",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.info("Scrape started: %s (url=%s)", data["job_id"], url)
        return data

    async def scrape_multiple(
        self,
        urls: list[str],
        selectors: dict[str, Any] | None,
        token: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Start a batch scrape job for multiple URLs.

        Maps to ``POST /api/v1/scrape/start``.
        """
        payload: dict[str, Any] = {"urls": urls}
        if selectors is not None:
            payload["selectors"] = selectors
        if options is not None:
            payload["options"] = options
        response = await self._client.post(
            f"{self.base_url}/api/v1/scrape/start",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.info("Batch scrape started: %s (%d urls)", data["job_id"], len(urls))
        return data

    async def get_scrape_status(self, job_id: str, token: str) -> dict[str, Any]:
        """Check scrape job status.

        Maps to ``GET /api/v1/scrape/status/{job_id}``.
        """
        response = await self._client.get(
            f"{self.base_url}/api/v1/scrape/status/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def get_scrape_result(self, job_id: str, token: str) -> dict[str, Any]:
        """Get scrape job results.

        Maps to ``GET /api/v1/scrape/result/{job_id}``.
        """
        response = await self._client.get(
            f"{self.base_url}/api/v1/scrape/result/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def extract_from_html(
        self,
        html: str,
        selectors: dict[str, Any],
        token: str,
    ) -> dict[str, Any]:
        """Extract data from HTML using CSS/XPath selectors.

        Maps to ``POST /api/v1/scrape/extract``.
        """
        response = await self._client.post(
            f"{self.base_url}/api/v1/scrape/extract",
            json={"html": html, "selectors": selectors},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def ocr_image(
        self,
        image_url: str,
        token: str,
        language: str = "spa+eng",
    ) -> dict[str, Any]:
        """OCR an image via Tesseract.

        Maps to ``POST /api/v1/scrape/ocr``.
        Used by: web_scraping_v2, billing.

        :param image_url: URL or MinIO path to the image.
        :param token: Bearer JWT token.
        :param language: OCR language pack (default: ``"spa+eng"``).
        :returns: Dict with ``text`` and optional ``confidence``.
        """
        response = await self._client.post(
            f"{self.base_url}/api/v1/scrape/ocr",
            json={"image_url": image_url, "language": language},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    # ── Data Sources (apps.discovery.api) ────────────────────────────────

    async def list_sources(self, token: str) -> list[dict[str, Any]]:
        """List data sources for the current tenant.

        Maps to ``GET /api/v1/sources``.
        """
        response = await self._client.get(
            f"{self.base_url}/api/v1/sources",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def get_source(self, source_id: str, token: str) -> dict[str, Any]:
        """Get a specific data source.

        Maps to ``GET /api/v1/sources/{source_id}``.
        """
        response = await self._client.get(
            f"{self.base_url}/api/v1/sources/{source_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    # ── Health ───────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Check Voyant health (unauthenticated, for K8s probes).

        Maps to ``GET /health``.
        """
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the HTTP client and release connections."""
        await self._client.aclose()
        logger.debug("VoyantClient closed")

    async def __aenter__(self) -> VoyantClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()


# Singleton instance
voyant_client: VoyantClient = VoyantClient()
