"""VoyantScraperService — Web scraping via Voyant/Playwright."""

from __future__ import annotations

import logging
from typing import Any

from voyant_bridge.client import voyant_client

logger = logging.getLogger(__name__)


class VoyantScraperService:
    """Service for web scraping via Voyant/Playwright.

    Wraps ``/api/v1/scrape/start``, ``/api/v1/scrape/ocr``, and
    related endpoints for competitor monitoring and document processing.
    """

    async def monitor_competitor(
        self,
        url: str,
        selectors: dict[str, Any],
        tenant_id: str,
        token: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Scrape and monitor a competitor website.

        Used by: ``web_scraping_v2.services.competitors``.

        :param url: Competitor URL to scrape.
        :param selectors: CSS/XPath selectors for data extraction.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param options: Optional scrape options (engine, timeout, scroll).
        :returns: Scrape job dict with ``job_id``, ``status``, ``artifacts``.
        """
        merged_options: dict[str, Any] = {
            "engine": "playwright",
            "scroll": True,
            "timeout": 30,
        }
        if options:
            merged_options.update(options)

        job = await voyant_client.scrape_url(
            url=url,
            selectors=selectors,
            token=token,
            options=merged_options,
        )
        logger.info(
            "Competitor monitoring started: tenant=%s url=%s job=%s",
            tenant_id,
            url,
            job["job_id"],
        )
        return job

    async def monitor_competitor_batch(
        self,
        urls: list[str],
        selectors: dict[str, Any],
        tenant_id: str,
        token: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Scrape multiple competitor URLs in a single batch job.

        Used by: strategy (batch competitor analysis).

        :param urls: List of competitor URLs to scrape.
        :param selectors: CSS/XPath selectors.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param options: Optional scrape options.
        :returns: Scrape job dict.
        """
        merged_options: dict[str, Any] = {
            "engine": "playwright",
            "scroll": True,
            "timeout": 30,
        }
        if options:
            merged_options.update(options)

        job = await voyant_client.scrape_multiple(
            urls=urls,
            selectors=selectors,
            token=token,
            options=merged_options,
        )
        logger.info(
            "Competitor batch monitoring started: tenant=%s urls=%d job=%s",
            tenant_id,
            len(urls),
            job["job_id"],
        )
        return job

    async def get_scrape_status(self, job_id: str, token: str) -> dict[str, Any]:
        """Poll the status of a scrape job.

        :param job_id: UUID of the scrape job.
        :param token: Bearer JWT token.
        :returns: Dict with ``job_id``, ``status``, ``pages_fetched``,
            ``artifact_count``, ``error_count``.
        """
        return await voyant_client.get_scrape_status(job_id, token)

    async def get_scrape_result(self, job_id: str, token: str) -> dict[str, Any]:
        """Get the results of a completed scrape job.

        :param job_id: UUID of the scrape job.
        :param token: Bearer JWT token.
        :returns: Dict with ``job_id``, ``status``, ``artifacts``.
        """
        return await voyant_client.get_scrape_result(job_id, token)

    async def extract_receipt_data(
        self,
        image_key: str,
        tenant_id: str,
        token: str,
    ) -> dict[str, Any]:
        """OCR a receipt image and extract structured data.

        Used by: ``billing.services.expenses``.

        :param image_key: MinIO object key for the receipt image.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :returns: Dict with ``text`` (raw OCR), ``structured`` (parsed
            fields: vendor, date, total, items).
        """
        ocr_result = await voyant_client.ocr_image(
            image_url=image_key,
            token=token,
            language="spa+eng",
        )
        raw_text: str = ocr_result.get("text", "")

        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        total = 0.0
        vendor = lines[0] if lines else ""
        date_str = ""

        for line in lines:
            lower = line.lower()
            if "total" in lower:
                parts = line.replace("$", "").replace(",", "").split()
                for p in parts:
                    try:
                        val = float(p)
                        if val > total:
                            total = val
                    except ValueError:
                        continue
            if any(c.isdigit() for c in line) and "-" in line and not date_str:
                date_str = line

        structured: dict[str, Any] = {
            "vendor": vendor,
            "date": date_str,
            "total": round(total, 2),
            "items": [],
            "raw_text": raw_text,
            "tenant_id": tenant_id,
        }
        logger.info(
            "Receipt OCR completed: tenant=%s image=%s total=%.2f",
            tenant_id,
            image_key,
            total,
        )
        return structured

    async def extract_from_html(
        self,
        html: str,
        selectors: dict[str, Any],
        token: str,
    ) -> dict[str, Any]:
        """Extract structured data from HTML using CSS/XPath selectors.

        Used by: ``web_scraping_v2`` (SERP parsing, review extraction).

        :param html: Raw HTML content string.
        :param selectors: Dict mapping field names to CSS/XPath selectors.
        :param token: Bearer JWT token.
        :returns: Dict mapping field names to extracted values.
        """
        return await voyant_client.extract_from_html(html, selectors, token)

    async def ocr_image(
        self,
        image_url: str,
        tenant_id: str,
        token: str,
        language: str = "spa+eng",
    ) -> dict[str, Any]:
        """OCR an image and return extracted text.

        :param image_url: URL or MinIO path to the image.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param language: OCR language pack (default: ``"spa+eng"``).
        :returns: Dict with ``text``, ``language``, ``confidence``.
        """
        result = await voyant_client.ocr_image(image_url, token, language)
        logger.info(
            "Image OCR completed: tenant=%s image=%s chars=%d",
            tenant_id,
            image_url,
            len(result.get("text", "")),
        )
        return result
