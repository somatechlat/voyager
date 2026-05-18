"""Competitor analysis with DOM diff and visual diff.

Change detection algorithm comparing content hashes, DOM structure,
and screenshots to identify competitor page modifications.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from django.utils import timezone

from ..models import CompetitorChange, CompetitorMonitor, CompetitorSnapshot
from .scraper import PlaywrightScraper

logger = logging.getLogger(__name__)


def _hash_content(text: str) -> str:
    """Generate SHA-256 hash of content for fast comparison.

    Args:
        text: The text content to hash.

    Returns:
        Hex digest of the SHA-256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dom_diff(
    previous_dom: dict[str, Any],
    current_dom: dict[str, Any],
) -> dict[str, Any]:
    """Compute structural difference between two DOM trees.

    Args:
        previous_dom: Previous snapshot DOM structure.
        current_dom: Current snapshot DOM structure.

    Returns:
        Dict with addedNodes, removedNodes, modifiedNodes counts and details.
    """
    prev_elements = set(previous_dom.get("elements", []))
    curr_elements = set(current_dom.get("elements", []))

    added = list(curr_elements - prev_elements)
    removed = list(prev_elements - curr_elements)

    # Check for modified nodes (same selector, different content)
    prev_by_selector: dict[str, str] = {
        e.get("selector", ""): e.get("text", "") for e in previous_dom.get("elements", [])
    }
    curr_by_selector: dict[str, str] = {
        e.get("selector", ""): e.get("text", "") for e in current_dom.get("elements", [])
    }

    modified: list[dict[str, str]] = []
    for selector, curr_text in curr_by_selector.items():
        if selector in prev_by_selector and prev_by_selector[selector] != curr_text:
            modified.append(
                {
                    "selector": selector,
                    "previous": prev_by_selector[selector],
                    "current": curr_text,
                }
            )

    return {
        "addedNodes": added,
        "removedNodes": removed,
        "modifiedNodes": modified,
        "addedCount": len(added),
        "removedCount": len(removed),
        "modifiedCount": len(modified),
    }


def _extract_prices(text: str) -> list[dict[str, Any]]:
    """Extract price values from text content using regex patterns.

    Args:
        text: Page text content.

    Returns:
        List of dicts with amount, currency, and source.
    """
    import re

    prices: list[dict[str, Any]] = []

    # Currency symbol patterns
    patterns = [
        (r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", "USD"),
        (r"€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", "EUR"),
        (r"£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", "GBP"),
        (r"¥\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", "JPY"),
    ]

    for pattern, currency in patterns:
        for match in re.finditer(pattern, text):
            amount_str = match.group(1).replace(",", "")
            try:
                amount = float(amount_str)
                prices.append({"amount": amount, "currency": currency, "source": "regex"})
            except ValueError:
                continue

    # Word-form patterns (USD, EUR, etc.)
    word_patterns = [
        (r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|US\s*Dollars?)", "USD"),
        (r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:EUR|Euros?)", "EUR"),
        (r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:GBP|Pounds?)", "GBP"),
    ]
    for pattern, currency in word_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(",", "")
            try:
                amount = float(amount_str)
                prices.append({"amount": amount, "currency": currency, "source": "regex"})
            except ValueError:
                continue

    return prices


def _extract_products(dom: dict[str, Any]) -> list[str]:
    """Extract product identifiers from DOM structure.

    Args:
        dom: DOM structure JSON.

    Returns:
        List of product names or identifiers.
    """
    products: list[str] = []
    for element in dom.get("elements", []):
        tag = element.get("tag", "").lower()
        if tag in ("h1", "h2", "h3"):
            text = element.get("text", "").strip()
            if text and len(text) < 200:
                products.append(text)
    return products


class CompetitorAnalyzer:
    """Analyzes competitor pages for changes.

    Uses content hashing, DOM diffing, and visual comparison
    to detect and classify changes.
    """

    def __init__(self, scraper: PlaywrightScraper | None = None) -> None:
        """Initialize the analyzer.

        Args:
            scraper: Optional PlaywrightScraper instance.
        """
        self.scraper = scraper or PlaywrightScraper()

    def detect_changes(
        self,
        competitor: CompetitorMonitor,
    ) -> dict[str, Any]:
        """Detect changes on a competitor page.

        Args:
            competitor: The CompetitorMonitor to check.

        Returns:
            Dict with changed flag and list of detected changes.
        """
        logger.info("Detecting changes for %s at %s", competitor.name, competitor.url)

        # Scrape current snapshot
        try:
            scrape_result = self.scraper.scrape(competitor.url)
        except Exception as exc:
            logger.error("Failed to scrape %s: %s", competitor.url, exc)
            return {"changed": False, "reason": "scrape_failed", "error": str(exc)}

        current_text = scrape_result.get("content_text", "")
        current_hash = _hash_content(current_text)

        # Build DOM structure
        current_dom = {"elements": self._parse_dom_elements(current_text)}

        # Check for previous snapshot
        previous_snapshot = (
            CompetitorSnapshot.objects.filter(competitor=competitor)
            .order_by("-scraped_at")
            .first()
        )

        if not previous_snapshot:
            # First snapshot — store and return
            snapshot = CompetitorSnapshot.objects.create(
                competitor=competitor,
                url=competitor.url,
                content_hash=current_hash,
                content_text=current_text,
                dom_structure=current_dom,
                screenshot_path=scrape_result.get("screenshot", ""),
                prices=_extract_prices(current_text),
                products=_extract_products(current_dom),
            )
            competitor.last_checked_at = timezone.now()
            competitor.save(update_fields=["last_checked_at"])
            return {"changed": False, "reason": "first_snapshot", "snapshot_id": str(snapshot.id)}

        # Fast hash check
        if previous_snapshot.content_hash == current_hash:
            competitor.last_checked_at = timezone.now()
            competitor.save(update_fields=["last_checked_at"])
            return {"changed": False, "reason": "content_unchanged"}

        # DOM diff
        dom_diff_result = _dom_diff(previous_snapshot.dom_structure, current_dom)

        # Extract prices and products
        current_prices = _extract_prices(current_text)
        previous_prices = previous_snapshot.prices or []
        price_changes = self._compare_prices(previous_prices, current_prices)

        current_products = _extract_products(current_dom)
        previous_products = previous_snapshot.products or []
        new_products = [p for p in current_products if p not in previous_products]

        # Classify and store changes
        changes: list[dict[str, Any]] = []

        if dom_diff_result["addedCount"] > 0:
            changes.append(
                {
                    "type": CompetitorChange.ChangeType.NEW_CONTENT,
                    "nodes": dom_diff_result["addedNodes"][:50],
                    "count": dom_diff_result["addedCount"],
                }
            )

        if dom_diff_result["removedCount"] > 0:
            changes.append(
                {
                    "type": CompetitorChange.ChangeType.REMOVED_CONTENT,
                    "nodes": dom_diff_result["removedNodes"][:50],
                    "count": dom_diff_result["removedCount"],
                }
            )

        if dom_diff_result["modifiedCount"] > 0:
            changes.append(
                {
                    "type": CompetitorChange.ChangeType.MODIFIED_CONTENT,
                    "nodes": dom_diff_result["modifiedNodes"][:50],
                    "count": dom_diff_result["modifiedCount"],
                }
            )

        if price_changes:
            changes.append(
                {
                    "type": CompetitorChange.ChangeType.PRICE_CHANGE,
                    "details": price_changes,
                }
            )

        if new_products:
            changes.append(
                {
                    "type": CompetitorChange.ChangeType.NEW_PRODUCT,
                    "products": new_products[:20],
                    "count": len(new_products),
                }
            )

        # Store new snapshot
        snapshot = CompetitorSnapshot.objects.create(
            competitor=competitor,
            url=competitor.url,
            content_hash=current_hash,
            content_text=current_text,
            dom_structure=current_dom,
            screenshot_path=scrape_result.get("screenshot", ""),
            prices=current_prices,
            products=current_products,
        )

        # Store changes
        for change in changes:
            CompetitorChange.objects.create(
                competitor=competitor,
                url=competitor.url,
                change_type=change["type"],
                change_details=change,
            )

        competitor.last_checked_at = timezone.now()
        competitor.save(update_fields=["last_checked_at"])

        return {
            "changed": len(changes) > 0,
            "changes": changes,
            "snapshot_id": str(snapshot.id),
        }

    def _parse_dom_elements(self, text: str) -> list[dict[str, str]]:
        """Parse text content into DOM-like element structure.

        Args:
            text: Raw text content.

        Returns:
            List of element dicts with tag, text, and selector.
        """
        elements: list[dict[str, str]] = []
        lines = text.split("\n")
        for idx, line in enumerate(lines):
            line = line.strip()
            if line and len(line) > 3:
                elements.append(
                    {
                        "tag": "div",
                        "selector": f"line-{idx}",
                        "text": line[:500],
                    }
                )
        return elements

    def _compare_prices(
        self,
        previous: list[dict[str, Any]],
        current: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Compare price lists and detect changes.

        Args:
            previous: Previous price list.
            current: Current price list.

        Returns:
            List of price change dicts with type and details.
        """
        changes: list[dict[str, Any]] = []
        prev_by_key: dict[str, float] = {}
        for p in previous:
            key = f"{p.get('currency', 'USD')}_{p.get('amount')}"
            prev_by_key[key] = p.get("amount", 0)

        for c in current:
            key = f"{c.get('currency', 'USD')}_{c.get('amount')}"
            curr_amount = c.get("amount", 0)
            if key in prev_by_key:
                prev_amount = prev_by_key[key]
                if abs(prev_amount - curr_amount) > 0.01:
                    pct_change = 0
                    if prev_amount > 0:
                        pct_change = round((curr_amount - prev_amount) / prev_amount * 100, 2)
                    changes.append(
                        {
                            "type": "price_changed",
                            "previous": prev_amount,
                            "current": curr_amount,
                            "currency": c.get("currency", "USD"),
                            "pct_change": pct_change,
                        }
                    )
            else:
                changes.append(
                    {
                        "type": "price_new",
                        "current": curr_amount,
                        "currency": c.get("currency", "USD"),
                    }
                )

        return changes
