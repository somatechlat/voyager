"""Web Scraping v2 services.

Business logic for scraping, competitor monitoring, price tracking,
trend detection, sentiment analysis, SERP tracking, and OCR processing.
"""

from .scraper import PlaywrightScraper, ProxyPool
from .competitors import CompetitorAnalyzer
from .prices import PriceExtractor, CurrencyNormalizer
from .trends import TrendAnalyzer
from .sentiment import SentimentAnalyzer
from .serp import SERPTracker
from .ocr import OCRProcessor

__all__ = [
    "PlaywrightScraper",
    "ProxyPool",
    "CompetitorAnalyzer",
    "PriceExtractor",
    "CurrencyNormalizer",
    "TrendAnalyzer",
    "SentimentAnalyzer",
    "SERPTracker",
    "OCRProcessor",
]
