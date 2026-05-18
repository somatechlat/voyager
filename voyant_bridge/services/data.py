"""VoyantDataService — Data ingestion and source management."""

from __future__ import annotations

import logging
from typing import Any

from voyant_bridge.client import voyant_client

logger = logging.getLogger(__name__)


class VoyantDataService:
    """Service for data ingestion and processing via Voyant.

    Wraps the ``/api/v1/jobs/ingest`` and ``/api/v1/sources`` endpoints
    to provide a task-oriented interface for Voyager modules.
    """

    async def sync_platform_metrics(
        self,
        platform: str,
        date_range: dict[str, str],
        tenant_id: str,
        token: str,
        source_id: str | None = None,
        tables: list[str] | None = None,
    ) -> str:
        """Sync metrics from a social platform.

        Used by: ``analytics_v2.tasks`` (scheduled metric sync).

        :param platform: Platform name (e.g. ``"meta"``, ``"google_ads"``).
        :param date_range: Dict with ``start`` and ``end`` ISO date strings.
        :param tenant_id: Tenant identifier for scoping.
        :param token: Bearer JWT token.
        :param source_id: Optional existing Voyant source ID.
        :param tables: Optional list of table names to sync.
        :returns: The UUID ``job_id`` of the ingestion job.
        """
        resolved_source_id = source_id
        if resolved_source_id is None:
            sources = await voyant_client.list_sources(token)
            for src in sources:
                if src.get("source_type") == platform:
                    resolved_source_id = src["source_id"]
                    break
            if resolved_source_id is None:
                raise ValueError(
                    f"No Voyant source found for platform '{platform}'. "
                    "Create a source first or pass source_id explicitly."
                )

        source_config: dict[str, Any] = {
            "source_id": resolved_source_id,
            "tenant_id": tenant_id,
            "mode": "incremental",
        }
        if tables is not None:
            source_config["tables"] = tables

        job_id = await voyant_client.ingest_data(source_config, token)
        logger.info(
            "Platform metrics sync started: platform=%s source=%s job=%s",
            platform,
            resolved_source_id,
            job_id,
        )
        return job_id

    async def ingest_csv(
        self,
        file_key: str,
        mapping: dict[str, str],
        tenant_id: str,
        token: str,
        source_id: str | None = None,
    ) -> str:
        """Ingest CSV data from MinIO.

        Used by: integrations sync (CSV file ingestion).

        :param file_key: MinIO object key for the CSV file.
        :param mapping: Dict mapping CSV column names to target table columns.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param source_id: Optional Voyant source ID for the CSV bucket.
        :returns: The UUID ``job_id`` of the ingestion job.
        """
        resolved_source_id = source_id
        if resolved_source_id is None:
            sources = await voyant_client.list_sources(token)
            for src in sources:
                if src.get("source_type") == "csv" or "csv" in src.get("name", "").lower():
                    resolved_source_id = src["source_id"]
                    break
            if resolved_source_id is None:
                raise ValueError(
                    "No CSV source found in Voyant. "
                    "Create a source with source_type='csv' first."
                )

        source_config: dict[str, Any] = {
            "source_id": resolved_source_id,
            "tenant_id": tenant_id,
            "mode": "full",
        }

        job_id = await voyant_client.ingest_data(source_config, token)
        logger.info(
            "CSV ingestion started: file=%s source=%s job=%s mapping=%s",
            file_key,
            resolved_source_id,
            job_id,
            mapping,
        )
        return job_id

    async def get_ingestion_status(self, job_id: str, token: str) -> dict[str, Any]:
        """Poll the status of an ingestion job.

        :param job_id: UUID of the ingestion job.
        :param token: Bearer JWT token.
        :returns: Dict with ``job_id``, ``status``, ``progress``, ``stage``.
        """
        return await voyant_client.get_job_status(job_id, token)

    async def cancel_ingestion(self, job_id: str, token: str) -> dict[str, str]:
        """Cancel a running ingestion job.

        :param job_id: UUID of the ingestion job.
        :param token: Bearer JWT token.
        :returns: Dict with ``status`` and ``job_id``.
        """
        return await voyant_client.cancel_job(job_id, token)
