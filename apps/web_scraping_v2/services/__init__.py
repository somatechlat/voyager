"""Web Scraping v2 services.

Business logic for scraping, competitor monitoring, price tracking,
trend detection, sentiment analysis, SERP tracking, and OCR processing.
"""

from .competitors import CompetitorAnalyzer
from .ocr import OCRProcessor
from .prices import CurrencyNormalizer, PriceExtractor
from .scraper import PlaywrightScraper, ProxyPool
from .sentiment import SentimentAnalyzer
from .serp import SERPTracker
from .trends import TrendAnalyzer

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
