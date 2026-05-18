"""Web Scraping v2 API.

Endpoints for web scraping and data collection — site crawling,
content extraction, competitor monitoring, price tracking,
trend detection, social listening, sentiment analysis,
SERP tracking, and OCR processing.

All routes are registered through the views subpackage.
"""

from __future__ import annotations

from .views import router
