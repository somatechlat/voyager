"""Price extraction and currency normalization.

Extracts prices from web pages using CSS selectors, JSON-LD,
regex patterns, and normalizes currencies for comparison.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Default exchange rates (production would fetch from an API)
DEFAULT_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.0"),
    "EUR": Decimal("1.08"),
    "GBP": Decimal("1.27"),
    "JPY": Decimal("0.0067"),
    "CAD": Decimal("0.74"),
    "AUD": Decimal("0.66"),
    "CHF": Decimal("1.13"),
    "CNY": Decimal("0.14"),
    "INR": Decimal("0.012"),
    "BRL": Decimal("0.20"),
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}


def _get_exchange_rates() -> dict[str, Decimal]:
    """Fetch cached exchange rates, falling back to defaults.

    Returns:
        Dict mapping currency codes to USD rates.
    """
    cached = cache.get("ws:exchange_rates")
    if cached:
        return {k: Decimal(str(v)) for k, v in cached.items()}
    return DEFAULT_RATES.copy()


class PriceExtractor:
    """Extracts prices from web page content.

    Uses three methods in order of reliability:
    1. CSS selectors (most precise)
    2. JSON-LD structured data
    3. Regex fallback (most general)
    """

    def extract(
        self,
        content: str,
        selector: str | None = None,
        json_ld_data: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract all prices from page content.

        Args:
            content: Page text or HTML content.
            selector: Optional CSS selector for targeted extraction.
            json_ld_data: Optional parsed JSON-LD data.

        Returns:
            List of price dicts with amount, currency, and source.
        """
        prices: list[dict[str, Any]] = []

        # Method 1: CSS selector
        if selector and content:
            selector_prices = self._extract_via_selector(content, selector)
            prices.extend(selector_prices)

        # Method 2: JSON-LD
        if json_ld_data:
            jsonld_prices = self._extract_via_json_ld(json_ld_data)
            prices.extend(jsonld_prices)

        # Method 3: Regex fallback (only if no prices found)
        if not prices:
            regex_prices = self._extract_via_regex(content or "")
            prices.extend(regex_prices)

        return prices

    def _extract_via_selector(self, content: str, selector: str) -> list[dict[str, Any]]:
        """Extract prices using CSS selectors.

        Args:
            content: HTML content.
            selector: CSS selector string.

        Returns:
            List of price dicts.
        """
        prices: list[dict[str, Any]] = []
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            elements = soup.select(selector)
            for el in elements:
                text = el.get_text(strip=True)
                parsed = self._parse_price_text(text)
                if parsed:
                    parsed["source"] = "css"
                    prices.append(parsed)
        except ImportError:
            logger.warning("BeautifulSoup not installed; skipping CSS extraction")
        except Exception as exc:
            logger.error("CSS extraction failed: %s", exc)
        return prices

    def _extract_via_json_ld(
        self, json_ld_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract prices from JSON-LD Product structured data.

        Args:
            json_ld_data: List of parsed JSON-LD objects.

        Returns:
            List of price dicts.
        """
        prices: list[dict[str, Any]] = []
        for item in json_ld_data:
            if item.get("@type") == "Product":
                offers = item.get("offers", {})
                if isinstance(offers, dict):
                    price = offers.get("price")
                    currency = offers.get("priceCurrency", "USD")
                    if price is not None:
                        try:
                            prices.append(
                                {
                                    "amount": Decimal(str(price)),
                                    "currency": currency,
                                    "source": "json-ld",
                                    "product_name": item.get("name", ""),
                                }
                            )
                        except Exception:
                            continue
            elif item.get("@type") == "AggregateOffer":
                low_price = item.get("lowPrice")
                currency = item.get("priceCurrency", "USD")
                if low_price is not None:
                    try:
                        prices.append(
                            {
                                "amount": Decimal(str(low_price)),
                                "currency": currency,
                                "source": "json-ld",
                            }
                        )
                    except Exception:
                        continue
        return prices

    def _extract_via_regex(self, text: str) -> list[dict[str, Any]]:
        """Extract prices using regex patterns.

        Args:
            text: Page text content.

        Returns:
            List of price dicts.
        """
        prices: list[dict[str, Any]] = []

        # Symbol-based patterns
        symbol_pattern = r"([$€£¥])\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
        for match in re.finditer(symbol_pattern, text):
            symbol = match.group(1)
            amount_str = match.group(2).replace(",", "")
            currency = CURRENCY_SYMBOLS.get(symbol, "USD")
            try:
                prices.append(
                    {
                        "amount": Decimal(amount_str),
                        "currency": currency,
                        "source": "regex",
                    }
                )
            except Exception:
                continue

        # Word-based patterns
        word_pattern = r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|EUR|GBP|JPY|CAD|AUD)"
        for match in re.finditer(word_pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(",", "")
            curr_word = match.group(0).upper()[-3:]
            currency_map = {
                "USD": "USD",
                "EUR": "EUR",
                "GBP": "GBP",
                "JPY": "JPY",
                "CAD": "CAD",
                "AUD": "AUD",
            }
            currency = currency_map.get(curr_word, "USD")
            try:
                prices.append(
                    {
                        "amount": Decimal(amount_str),
                        "currency": currency,
                        "source": "regex",
                    }
                )
            except Exception:
                continue

        return prices

    def _parse_price_text(self, text: str) -> dict[str, Any] | None:
        """Parse a single price string into amount and currency.

        Args:
            text: Raw price text (e.g., ``"€49.99"``).

        Returns:
            Dict with amount and currency, or None if not parseable.
        """
        text = text.strip()
        if not text:
            return None

        # Try symbol prefix
        match = re.match(r"([$€£¥])\s*([\d,]+\.?\d*)", text)
        if match:
            symbol = match.group(1)
            amount_str = match.group(2).replace(",", "")
            try:
                return {
                    "amount": Decimal(amount_str),
                    "currency": CURRENCY_SYMBOLS.get(symbol, "USD"),
                }
            except Exception:
                return None

        # Try number followed by currency
        match = re.match(r"([\d,]+\.?\d*)\s*([A-Z]{3})", text)
        if match:
            amount_str = match.group(1).replace(",", "")
            currency = match.group(2).upper()
            try:
                return {"amount": Decimal(amount_str), "currency": currency}
            except Exception:
                return None

        return None


class CurrencyNormalizer:
    """Normalizes prices to a common currency for comparison."""

    def __init__(self, target_currency: str = "USD") -> None:
        """Initialize the normalizer.

        Args:
            target_currency: Target currency code (default USD).
        """
        self.target_currency = target_currency
        self.rates = _get_exchange_rates()

    def normalize(
        self,
        amount: Decimal,
        from_currency: str,
    ) -> dict[str, Any]:
        """Convert a price to the target currency.

        Args:
            amount: The price amount.
            from_currency: Source currency code.

        Returns:
            Dict with normalized amount, currency, rate used, and original.
        """
        from_currency = from_currency.upper()
        if from_currency == self.target_currency:
            return {
                "amount": round(amount, 2),
                "currency": self.target_currency,
                "rate": Decimal("1.0"),
                "original": {"amount": amount, "currency": from_currency},
            }

        from_rate = self.rates.get(from_currency)
        to_rate = self.rates.get(self.target_currency, Decimal("1.0"))

        if from_rate is None:
            logger.warning("Unknown currency: %s", from_currency)
            return {
                "amount": amount,
                "currency": from_currency,
                "rate": None,
                "original": {"amount": amount, "currency": from_currency},
            }

        # Convert: amount * (to_rate / from_rate)
        rate_ratio = to_rate / from_rate
        normalized = amount * rate_ratio

        return {
            "amount": round(normalized, 2),
            "currency": self.target_currency,
            "rate": float(rate_ratio),
            "original": {"amount": amount, "currency": from_currency},
        }

    def refresh_rates(self) -> None:
        """Refresh exchange rates from cache."""
        self.rates = _get_exchange_rates()
