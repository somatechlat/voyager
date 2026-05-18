"""VoyantAnalysisService — Statistical analysis and NLP."""

from __future__ import annotations

import logging
from typing import Any

from voyant_bridge.client import voyant_client

logger = logging.getLogger(__name__)


class VoyantAnalysisService:
    """Service for statistical analysis via Voyant.

    Wraps the ``/api/v1/analyze`` endpoint for competitor analysis,
    anomaly detection, sentiment analysis, and data profiling.
    """

    async def analyze_competitor_content(
        self,
        competitor_urls: list[str],
        tenant_id: str,
        token: str,
        sample_size: int = 5000,
    ) -> dict[str, Any]:
        """NLP analysis of competitor content.

        Used by: ``strategy.services.competitors``.

        Scrapes the competitor URLs, then runs Voyant analysis with NLP
        analyzers to extract keywords, sentiment, topics, and readability.

        :param competitor_urls: List of competitor webpage URLs.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param sample_size: Max content sample size (default: 5000).
        :returns: Analysis result dict with ``summary``, ``artifacts``,
            ``manifest``.
        """
        from voyant_bridge.client import VoyantClient

        client = VoyantClient()
        try:
            scrape_results = []
            for url in competitor_urls:
                result = await client.scrape_url(
                    url=url,
                    selectors={
                        "content": "body",
                        "title": "title",
                        "headings": "h1, h2, h3",
                    },
                    token=token,
                    options={"engine": "playwright", "scroll": True},
                )
                scrape_results.append(result)

            combined_text = "\n\n".join(
                r.get("artifacts", [{}])[0].get("storage_path", "")
                for r in scrape_results
                if r.get("artifacts")
            )

            dataset: dict[str, Any] = {
                "table": "competitor_content",
                "sample_size": sample_size,
                "analyzers": ["nlp", "sentiment", "keywords", "readability"],
                "analyzer_context": {
                    "content": combined_text,
                    "urls": competitor_urls,
                    "tenant_id": tenant_id,
                },
            }
            result = await voyant_client.analyze_data(dataset, token)
            logger.info(
                "Competitor analysis completed: %d urls, job=%s",
                len(competitor_urls),
                result.get("job_id"),
            )
            return result
        finally:
            await client.close()

    async def detect_anomalies(
        self,
        metric_series: list[dict[str, Any]],
        method: str,
        token: str,
        table: str = "metric_series",
    ) -> dict[str, Any]:
        """Statistical anomaly detection on a metric time series.

        Used by: ``analytics_v2.services.anomaly``.

        :param metric_series: List of dicts with ``timestamp``, ``value``.
        :param method: Detection method (``"iqr"``, ``"zscore"``,
            ``"isolation_forest"``).
        :param token: Bearer JWT token.
        :param table: Target analysis table name.
        :returns: Analysis result with anomaly flags in ``summary``.
        """
        dataset: dict[str, Any] = {
            "table": table,
            "analyzers": ["anomaly"],
            "analyzer_context": {
                "metric_series": metric_series,
                "method": method,
            },
            "sample_size": len(metric_series),
        }
        result = await voyant_client.analyze_data(dataset, token)
        logger.info(
            "Anomaly detection completed: method=%s points=%d job=%s",
            method,
            len(metric_series),
            result.get("job_id"),
        )
        return result

    async def sentiment_analysis(
        self,
        texts: list[str],
        model: str,
        token: str,
    ) -> dict[str, Any]:
        """Multi-model sentiment analysis on a batch of texts.

        Used by: ``social_media`` (post sentiment), ``web_scraping_v2``
        (review sentiment).

        :param texts: List of text strings to analyze.
        :param model: Sentiment model (``"vader"``, ``"transformer"``,
            ``"textblob"``).
        :param token: Bearer JWT token.
        :returns: Analysis result with per-text sentiment scores.
        """
        dataset: dict[str, Any] = {
            "table": "sentiment_batch",
            "analyzers": ["sentiment"],
            "analyzer_context": {
                "texts": texts,
                "model": model,
            },
            "sample_size": len(texts),
        }
        result = await voyant_client.analyze_data(dataset, token)
        logger.info(
            "Sentiment analysis completed: model=%s texts=%d job=%s",
            model,
            len(texts),
            result.get("job_id"),
        )
        return result

    async def profile_dataset(
        self,
        source_id: str,
        table: str,
        token: str,
        sample_size: int = 10000,
    ) -> dict[str, Any]:
        """Run data profiling on a source table.

        Used by: analytics_v2 (data quality checks).

        :param source_id: Voyant source ID.
        :param table: Table name to profile.
        :param token: Bearer JWT token.
        :param sample_size: Rows to sample (default: 10000).
        :returns: Analysis result with column statistics.
        """
        dataset: dict[str, Any] = {
            "source_id": source_id,
            "table": table,
            "sample_size": sample_size,
            "analyzers": ["profile"],
            "profile": True,
        }
        result = await voyant_client.analyze_data(dataset, token)
        logger.info(
            "Dataset profiling completed: source=%s table=%s job=%s",
            source_id,
            table,
            result.get("job_id"),
        )
        return result
