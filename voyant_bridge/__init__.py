"""Voyant Bridge — Data Processing Integration for Voyager.

Provides async HTTP client and high-level services that expose Voyant's
data intelligence capabilities to Voyager modules:

* **Data Ingestion** — Sync platform metrics, CSV ingest via MinIO
* **Statistical Analysis** — Competitor content NLP, anomaly detection, sentiment
* **SQL Execution** — Campaign queries, dashboard metrics via Trino
* **Semantic Search** — Agent memory retrieval/storage via Milvus
* **Web Scraping** — Competitor monitoring, OCR via Playwright/Tesseract

Usage::

    from voyant_bridge.client import voyant_client
    from voyant_bridge.services import (
        VoyantDataService,
        VoyantAnalysisService,
        VoyantSQLService,
        VoyantSearchService,
        VoyantScraperService,
    )
"""

from voyant_bridge.client import VoyantClient, voyant_client
from voyant_bridge.services import (
    VoyantAnalysisService,
    VoyantDataService,
    VoyantScraperService,
    VoyantSearchService,
    VoyantSQLService,
)

__all__ = [
    "VoyantClient",
    "voyant_client",
    "VoyantDataService",
    "VoyantAnalysisService",
    "VoyantSQLService",
    "VoyantSearchService",
    "VoyantScraperService",
]
