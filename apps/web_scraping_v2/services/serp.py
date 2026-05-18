"""SERP tracking with rank monitoring and feature detection.

Tracks search engine rankings for keywords with location/device-specific
results and SERP feature detection.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache

from ..models import SERPTracking

logger = logging.getLogger(__name__)

# SERP feature CSS selectors for detection
SERP_FEATURES: dict[str, dict[str, str]] = {
    "featured_snippet": {
        "selector": ".c2xzTb, .xpdopen, . vk_c",
        "description": "Position 0 snippet",
    },
    "knowledge_panel": {
        "selector": ".kp-wholepage, .knowledge-panel",
        "description": "Right-side knowledge panel",
    },
    "local_pack": {
        "selector": ".rllt__details, .dbg0pd",
        "description": "Local business results",
    },
    "people_also_ask": {
        "selector": ".related-question-pair, .mgfMef",
        "description": "PAA box",
    },
    "image_pack": {
        "selector": "#imagebox_bigimages, .LYgfHb",
        "description": "Image carousel",
    },
    "video_carousel": {
        "selector": "#video-carousel, .dXiKIc",
        "description": "Video results",
    },
    "top_stories": {
        "selector": ".g-blk, .WlydOe",
        "description": "News results",
    },
    "shopping_results": {
        "selector": ".commercial-unit-desktop-top, .sh-dgr__grid-result",
        "description": "Shopping ads",
    },
    "ads_top": {
        "selector": "#tads, .uEiDHr",
        "description": "Top ad positions",
    },
    "ads_bottom": {
        "selector": "#tadsb",
        "description": "Bottom ad positions",
    },
    "site_links": {
        "selector": ".ajlcT, .osl",
        "description": "Sitelinks",
    },
    "rich_results": {
        "selector": ".ThbG9d, .yStFkb",
        "description": "Rich results",
    },
}

# Max SERP checks per hour
MAX_CHECKS_PER_HOUR: int = getattr(settings, "WS_SERP_MAX_CHECKS_HOUR", 1000)


def _rate_limit_serp() -> bool:
    """Enforce SERP check rate limiting.

    Returns:
        True if check is allowed, False if rate limited.
    """
    key = "ws:serp:hourly_count"
    current = cache.get(key, 0)
    if current >= MAX_CHECKS_PER_HOUR:
        logger.warning(
            "SERP rate limit reached: %s/%s checks this hour", current, MAX_CHECKS_PER_HOUR
        )
        return False
    cache.set(key, current + 1, timeout=3600)
    return True


class SERPTracker:
    """Tracks search engine rankings for keywords.

    Monitors organic position, detects SERP features, and tracks
    position changes over time.
    """

    def __init__(self) -> None:
        """Initialize the SERP tracker."""
        self.scraper = None

    def _get_scraper(self) -> Any:
        """Lazy-load the Playwright scraper.

        Returns:
            PlaywrightScraper instance.
        """
        if self.scraper is None:
            from .scraper import PlaywrightScraper

            self.scraper = PlaywrightScraper()
        return self.scraper

    def track(
        self,
        keyword: str,
        tenant_id: str = "",
        location_country: str = "us",
        location_region: str = "",
        language: str = "en",
        device: str = "desktop",
        target_url: str = "",
    ) -> dict[str, Any]:
        """Track SERP rankings for a keyword.

        Args:
            keyword: The search keyword.
            tenant_id: Tenant scope identifier.
            location_country: ISO country code.
            location_region: Region name.
            language: Language code.
            device: Device type (desktop, mobile, tablet).
            target_url: Optional URL to find in results.

        Returns:
            Dict with organic results, detected features, and metadata.
        """
        if not _rate_limit_serp():
            return {"error": "Rate limit exceeded", "keyword": keyword}

        # Build Google search URL
        params: dict[str, str] = {
            "q": keyword,
            "gl": location_country.lower(),
            "hl": language,
            "num": "100",
        }
        if device == "mobile":
            params["uivb"] = "1"

        search_url = f"https://www.google.com/search?{urlencode(params)}"

        logger.info("Tracking SERP for '%s' in %s on %s", keyword, location_country, device)

        try:
            scraper = self._get_scraper()
            result = scraper.scrape(search_url)
            html = result.get("content_html", "")

            # Parse organic results
            organic_results = self._parse_organic_results(html, keyword)

            # Detect SERP features
            features = self._detect_features(html)

            # Find target URL position
            position = None
            if target_url:
                for r in organic_results:
                    if target_url in r.get("url", ""):
                        position = r["position"]
                        break

            # Calculate position change
            position_change = 0
            if position is not None:
                previous = (
                    SERPTracking.objects.filter(
                        tenant_id=tenant_id,
                        keyword=keyword,
                        location_country=location_country,
                        device=device,
                    )
                    .exclude(position__isnull=True)
                    .order_by("-tracked_at")
                    .first()
                )
                if previous and previous.position:
                    position_change = previous.position - position

            # Persist
            if tenant_id:
                serp_record = SERPTracking.objects.create(
                    tenant_id=tenant_id,
                    keyword=keyword,
                    location_country=location_country,
                    location_region=location_region,
                    language=language,
                    device=device,
                    position=position,
                    url=target_url,
                    serp_features=features,
                    position_change=position_change,
                )
            else:
                serp_record = None

            return {
                "keyword": keyword,
                "location_country": location_country,
                "device": device,
                "organic_results": organic_results[:20],
                "features": features,
                "position": position,
                "position_change": position_change,
                "result_count": len(organic_results),
                "record_id": str(serp_record.id) if serp_record else None,
            }

        except Exception as exc:
            logger.error("SERP tracking failed for '%s': %s", keyword, exc)
            return {
                "error": str(exc),
                "keyword": keyword,
                "organic_results": [],
                "features": [],
            }

    def _parse_organic_results(self, html: str, keyword: str) -> list[dict[str, Any]]:
        """Parse organic search results from SERP HTML.

        Args:
            html: SERP HTML content.
            keyword: The tracked keyword.

        Returns:
            List of result dicts with position, url, title, description.
        """
        results: list[dict[str, Any]] = []

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Organic result selectors
            selectors = [
                "div.g",
                "div.Gx5Zad",
                "div.tF2Cxc",
                "div.yuRUbf",
                "div.MjjYud",
                "div.N54PNb",
            ]

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    position = 1
                    for element in elements:
                        link_el = element.select_one("a")
                        if not link_el:
                            continue
                        url = link_el.get("href", "")
                        if not url or url.startswith("/"):
                            continue

                        title_el = element.select_one("h3, .DKV0Md")
                        title = title_el.get_text(strip=True) if title_el else ""

                        desc_el = element.select_one(".VwiC3b, .s3v94d, .lEBKkf, .aCOpRe")
                        description = desc_el.get_text(strip=True) if desc_el else ""

                        results.append(
                            {
                                "position": position,
                                "url": url,
                                "title": title,
                                "description": description,
                            }
                        )
                        position += 1
                    break

        except ImportError:
            logger.warning("BeautifulSoup not installed; skipping organic result parsing")
        except Exception as exc:
            logger.error("Failed to parse organic results: %s", exc)

        return results

    def _detect_features(self, html: str) -> list[str]:
        """Detect SERP features in HTML.

        Args:
            html: SERP HTML content.

        Returns:
            List of detected feature names.
        """
        features: list[str] = []

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            for feature_name, config in SERP_FEATURES.items():
                selectors = config["selector"].split(", ")
                for sel in selectors:
                    if soup.select_one(sel):
                        features.append(feature_name)
                        break

        except ImportError:
            logger.warning("BeautifulSoup not installed; skipping feature detection")
        except Exception as exc:
            logger.error("Failed to detect SERP features: %s", exc)

        return features

    def batch_track(
        self,
        keywords: list[str],
        tenant_id: str = "",
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Track multiple keywords in batch.

        Args:
            keywords: List of keywords to track.
            tenant_id: Tenant scope identifier.
            **kwargs: Additional params passed to track().

        Returns:
            List of track result dicts.
        """
        results: list[dict[str, Any]] = []
        for keyword in keywords:
            result = self.track(keyword, tenant_id=tenant_id, **kwargs)
            results.append(result)
            time.sleep(1)  # Polite delay between requests
        return results
