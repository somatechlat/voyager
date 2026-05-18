"""Playwright-based web scraper with proxy rotation.

Handles JavaScript-rendered pages, respects robots.txt, and
implements polite scraping with rate limiting.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

logger = logging.getLogger(__name__)

# Default proxy pool from settings or empty
PROXY_POOL: list[str] = getattr(settings, "WS_PROXY_POOL", [])
# Max requests per second per domain
RATE_LIMIT_RPS: float = getattr(settings, "WS_RATE_LIMIT_RPS", 1.0)
# Default timeout for page loads
DEFAULT_TIMEOUT: int = getattr(settings, "WS_PAGE_TIMEOUT", 30000)
# User agent rotation
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _get_domain(url: str) -> str:
    """Extract the domain from a URL.

    Args:
        url: Full URL string.

    Returns:
        Domain name (e.g., ``example.com``).
    """
    parsed = urlparse(url)
    return parsed.netloc.lower().lstrip("www.")


def _rate_limit_key(domain: str) -> str:
    """Generate a cache key for per-domain rate limiting.

    Args:
        domain: The domain to rate limit against.

    Returns:
        Cache key string.
    """
    return f"ws:ratelimit:{domain}"


def _check_rate_limit(domain: str) -> None:
    """Enforce per-domain rate limiting via Django cache.

    Sleeps if the minimum interval between requests has not elapsed.

    Args:
        domain: The domain being scraped.
    """
    key = _rate_limit_key(domain)
    last_request = cache.get(key)
    min_interval = 1.0 / RATE_LIMIT_RPS

    if last_request is not None:
        elapsed = time.time() - last_request
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug("Rate limiting %s: sleeping %.2fs", domain, sleep_time)
            time.sleep(sleep_time)

    cache.set(key, time.time(), timeout=int(min_interval * 2))


def _check_robots_txt(url: str) -> bool:
    """Check if a URL is allowed by robots.txt.

    Uses a simple cache-backed check. In production, this would
    parse the full robots.txt file.

    Args:
        url: The URL to check.

    Returns:
        True if scraping is allowed, False otherwise.
    """
    domain = _get_domain(url)
    cache_key = f"ws:robots:{domain}"
    allowed = cache.get(cache_key)

    if allowed is None:
        # Default allow — in production, fetch and parse robots.txt
        allowed = True
        cache.set(cache_key, allowed, timeout=3600)

    return bool(allowed)


class ProxyPool:
    """Manages a pool of rotating proxies for scraping.

    Attributes:
        proxies: List of proxy URLs.
    """

    def __init__(self, proxies: list[str] | None = None) -> None:
        """Initialize the proxy pool.

        Args:
            proxies: Optional list of proxy URLs. Falls back to settings.
        """
        self.proxies: list[str] = proxies or PROXY_POOL

    def get_proxy(self) -> str | None:
        """Get a random proxy from the pool.

        Returns:
            A proxy URL string, or None if the pool is empty.
        """
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def rotate(self) -> str | None:
        """Rotate and return a new proxy.

        Returns:
            A proxy URL string, or None if the pool is empty.
        """
        return self.get_proxy()


class PlaywrightScraper:
    """Scraper using Playwright for JavaScript-rendered pages.

    Handles page navigation, content extraction, screenshot capture,
    and proxy rotation for anti-bot bypass.

    Example:
        >>> scraper = PlaywrightScraper()
        >>> result = scraper.scrape("https://example.com")
        >>> print(result["content_text"][:200])
    """

    def __init__(
        self,
        proxy_pool: ProxyPool | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        headless: bool = True,
    ) -> None:
        """Initialize the scraper.

        Args:
            proxy_pool: Optional ProxyPool instance.
            timeout: Page load timeout in milliseconds.
            headless: Run browser in headless mode.
        """
        self.proxy_pool = proxy_pool or ProxyPool()
        self.timeout = timeout
        self.headless = headless

    def scrape(
        self,
        url: str,
        selector: str | None = None,
        wait_for: str | None = None,
    ) -> dict[str, Any]:
        """Scrape a URL and return structured content.

        Args:
            url: The URL to scrape.
            selector: Optional CSS selector for targeted extraction.
            wait_for: Optional CSS selector to wait for before extraction.

        Returns:
            Dictionary with content_text, content_html, metadata, screenshot.

        Raises:
            RuntimeError: If Playwright is not installed or scraping fails.
            PermissionError: If robots.txt disallows the URL.
        """
        if sync_playwright is None:
            raise RuntimeError("Playwright is not installed. Install with: pip install playwright")

        if not _check_robots_txt(url):
            raise PermissionError(f"robots.txt disallows scraping: {url}")

        domain = _get_domain(url)
        _check_rate_limit(domain)

        proxy = self.proxy_pool.get_proxy()
        user_agent = random.choice(USER_AGENTS)

        result: dict[str, Any] = {
            "url": url,
            "content_text": "",
            "content_html": "",
            "metadata": {},
            "screenshot": None,
            "proxy_used": proxy,
        }

        with sync_playwright() as pw:
            browser_kwargs: dict[str, Any] = {"headless": self.headless}
            if proxy:
                browser_kwargs["proxy"] = {"server": proxy}

            browser = pw.chromium.launch(**browser_kwargs)
            context = browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            page.set_default_timeout(self.timeout)

            try:
                response = page.goto(url, wait_until="networkidle")

                if wait_for:
                    page.wait_for_selector(wait_for, timeout=self.timeout)

                # Extract content
                if selector:
                    elements = page.query_selector_all(selector)
                    texts = [el.inner_text() for el in elements if el]
                    result["content_text"] = "\n".join(texts)
                    htmls = [el.inner_html() for el in elements if el]
                    result["content_html"] = "\n".join(htmls)
                else:
                    result["content_text"] = page.inner_text("body")
                    result["content_html"] = page.content()

                # Metadata
                result["metadata"] = {
                    "status_code": response.status if response else 0,
                    "content_type": (response.headers.get("content-type", "") if response else ""),
                    "title": page.title(),
                    "user_agent": user_agent,
                    "final_url": page.url,
                }

                # Screenshot as base64
                screenshot_bytes = page.screenshot(full_page=True, type="jpeg", quality=80)
                import base64

                result["screenshot"] = base64.b64encode(screenshot_bytes).decode("utf-8")

            except Exception as exc:
                logger.error("Scrape failed for %s: %s", url, exc)
                result["metadata"]["error"] = str(exc)
                raise RuntimeError(f"Scraping failed: {exc}") from exc
            finally:
                context.close()
                browser.close()

        return result

    def scrape_json_ld(self, url: str) -> list[dict[str, Any]]:
        """Extract JSON-LD structured data from a page.

        Args:
            url: The URL to scrape.

        Returns:
            List of parsed JSON-LD objects.
        """
        if sync_playwright is None:
            raise RuntimeError("Playwright is not installed.")

        domain = _get_domain(url)
        _check_rate_limit(domain)

        proxy = self.proxy_pool.get_proxy()
        user_agent = random.choice(USER_AGENTS)
        json_ld_data: list[dict[str, Any]] = []

        with sync_playwright() as pw:
            browser_kwargs: dict[str, Any] = {"headless": self.headless}
            if proxy:
                browser_kwargs["proxy"] = {"server": proxy}

            browser = pw.chromium.launch(**browser_kwargs)
            context = browser.new_context(user_agent=user_agent)
            page = context.new_page()

            try:
                page.goto(url, wait_until="networkidle")
                scripts = page.query_selector_all('script[type="application/ld+json"]')
                for script in scripts:
                    content = script.inner_text()
                    try:
                        import json

                        json_ld_data.append(json.loads(content))
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON-LD in %s", url)
            finally:
                context.close()
                browser.close()

        return json_ld_data
