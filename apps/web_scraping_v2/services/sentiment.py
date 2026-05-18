"""Multi-model sentiment analysis with aspect-based and emotion detection.

Supports BERT for short text, GPT for long-form analysis, with
aspect-based breakdown and emotion detection.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from decimal import Decimal
from typing import Any

from django.conf import settings

from ..models import SentimentScore

logger = logging.getLogger(__name__)

# Sentiment keywords for rule-based fallback
POSITIVE_WORDS: set[str] = {
    "good",
    "great",
    "excellent",
    "amazing",
    "love",
    "best",
    "fantastic",
    "wonderful",
    "awesome",
    "perfect",
    "happy",
    "satisfied",
    "recommend",
    "outstanding",
    "superb",
    "brilliant",
    "impressive",
    "nice",
    "beautiful",
    "easy",
    "smooth",
    "fast",
    "reliable",
    "helpful",
    "friendly",
    "professional",
}

NEGATIVE_WORDS: set[str] = {
    "bad",
    "terrible",
    "awful",
    "horrible",
    "hate",
    "worst",
    "poor",
    "disappointing",
    "frustrating",
    "annoying",
    "useless",
    "broken",
    "slow",
    "difficult",
    "expensive",
    "overpriced",
    "rude",
    "unprofessional",
    "disgusting",
    "messy",
    "dirty",
    "unreliable",
    "confusing",
    "complicated",
}

EMOTION_PATTERNS: dict[str, list[str]] = {
    "joy": ["happy", "joyful", "excited", "delighted", "cheerful", "elated"],
    "anger": ["angry", "furious", "irritated", "annoyed", "frustrated", "mad"],
    "fear": ["afraid", "scared", "worried", "anxious", "nervous", "terrified"],
    "sadness": ["sad", "disappointed", "depressed", "gloomy", "heartbroken", "upset"],
    "surprise": ["surprised", "amazed", "shocked", "astonished", "stunned"],
    "disgust": ["disgusted", "repulsed", "revolted", "sickened", "appalled"],
}


def _hash_text(text: str) -> str:
    """Generate SHA-256 hash of text for caching.

    Args:
        text: Input text.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _detect_language(text: str) -> str:
    """Detect the language of text (simple heuristic).

    Args:
        text: Input text.

    Returns:
        ISO language code.
    """
    try:
        from langdetect import detect

        return detect(text[:1000])
    except ImportError:
        return "en"
    except Exception:
        return "en"


class SentimentAnalyzer:
    """Multi-model sentiment analyzer with aspect and emotion detection.

    Auto-selects model based on text length:
    - BERT for short text (< 280 chars)
    - GPT for long text (>= 280 chars)

    Falls back to rule-based analysis if ML libraries are unavailable.
    """

    def __init__(self) -> None:
        """Initialize the analyzer and load models."""
        self._bert_model: Any = None
        self._gpt_client: Any = None
        self._init_models()

    def _init_models(self) -> None:
        """Lazy-load ML models if available."""
        # Try loading BERT model
        try:
            from transformers import pipeline

            self._bert_model = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
            )
            logger.info("BERT sentiment model loaded")
        except ImportError:
            logger.info("transformers not installed; using rule-based fallback")
        except Exception as exc:
            logger.warning("Failed to load BERT model: %s", exc)

        # Try loading OpenAI client
        try:
            import openai

            api_key = getattr(settings, "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
            if api_key:
                self._gpt_client = openai.OpenAI(api_key=api_key)
                logger.info("GPT client initialized")
        except ImportError:
            logger.info("openai not installed; GPT analysis unavailable")
        except Exception as exc:
            logger.warning("Failed to initialize GPT client: %s", exc)

    def _select_model(self, text: str, preferred: str = "auto") -> str:
        """Select the best model for the text.

        Args:
            text: Input text.
            preferred: Preferred model or "auto".

        Returns:
            Model name string.
        """
        if preferred != "auto":
            return preferred
        if len(text) < 280:
            return "bert" if self._bert_model else "rule"
        return "gpt" if self._gpt_client else "rule"

    def analyze(
        self,
        text: str,
        model: str = "auto",
        tenant_id: str = "",
        source_type: str = "",
        source_id: str = "",
    ) -> dict[str, Any]:
        """Analyze sentiment of text with aspect and emotion detection.

        Args:
            text: The text to analyze.
            model: Model to use (``auto``, ``bert``, ``gpt``, ``rule``).
            tenant_id: Tenant scope identifier.
            source_type: Type of source content.
            source_id: Source record identifier.

        Returns:
            Dict with overall sentiment, aspects, emotions, and metadata.
        """
        if not text or not text.strip():
            return {
                "overall": {
                    "sentiment": SentimentScore.Sentiment.NEUTRAL,
                    "score": Decimal("0"),
                    "confidence": Decimal("0"),
                },
                "aspects": [],
                "emotions": {},
                "model": "none",
                "language": "en",
            }

        selected_model = self._select_model(text, model)
        language = _detect_language(text)

        # Overall sentiment
        if selected_model == "bert" and self._bert_model:
            overall = self._analyze_bert(text)
        elif selected_model == "gpt" and self._gpt_client:
            overall = self._analyze_gpt(text)
        else:
            overall = self._analyze_rule_based(text)

        # Aspect-based sentiment
        aspects = self._extract_aspects(text)

        # Emotion detection
        emotions = self._detect_emotions(text)

        result: dict[str, Any] = {
            "overall": overall,
            "aspects": aspects,
            "emotions": emotions,
            "model": selected_model,
            "language": language,
        }

        # Persist if tenant_id provided
        if tenant_id:
            SentimentScore.objects.create(
                tenant_id=tenant_id,
                text=text,
                text_hash=_hash_text(text),
                source_type=source_type,
                source_id=source_id,
                model=selected_model,
                overall_sentiment=overall["sentiment"],
                overall_score=overall["score"],
                confidence=overall["confidence"],
                aspects=aspects,
                emotions=emotions,
                language=language,
            )

        return result

    def _analyze_bert(self, text: str) -> dict[str, Any]:
        """Analyze sentiment using BERT.

        Args:
            text: Input text.

        Returns:
            Dict with sentiment label, score, and confidence.
        """
        try:
            # Truncate to BERT's max length
            truncated = text[:512]
            result = self._bert_model(truncated)[0]
            label = result["label"].lower()
            confidence = Decimal(str(result["score"]))

            if label == "positive":
                sentiment = SentimentScore.Sentiment.POSITIVE
                score = confidence
            elif label == "negative":
                sentiment = SentimentScore.Sentiment.NEGATIVE
                score = -confidence
            else:
                sentiment = SentimentScore.Sentiment.NEUTRAL
                score = Decimal("0")

            return {
                "sentiment": sentiment,
                "score": round(score, 3),
                "confidence": round(confidence, 3),
            }
        except Exception as exc:
            logger.error("BERT analysis failed: %s", exc)
            return self._analyze_rule_based(text)

    def _analyze_gpt(self, text: str) -> dict[str, Any]:
        """Analyze sentiment using GPT.

        Args:
            text: Input text.

        Returns:
            Dict with sentiment label, score, and confidence.
        """
        try:
            response = self._gpt_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Analyze the sentiment of the following text. "
                            "Respond ONLY with a JSON object: "
                            '{"sentiment": "positive|negative|neutral|mixed", '
                            '"score": -1.0 to 1.0, "confidence": 0.0 to 1.0}'
                        ),
                    },
                    {"role": "user", "content": text[:4000]},
                ],
                temperature=0.0,
                max_tokens=150,
            )
            content = response.choices[0].message.content or "{}"
            import json

            parsed = json.loads(content)
            sentiment_str = parsed.get("sentiment", "neutral").lower()
            score = Decimal(str(parsed.get("score", 0)))
            confidence = Decimal(str(parsed.get("confidence", 0.5)))

            sentiment_map: dict[str, str] = {
                "positive": SentimentScore.Sentiment.POSITIVE,
                "negative": SentimentScore.Sentiment.NEGATIVE,
                "neutral": SentimentScore.Sentiment.NEUTRAL,
                "mixed": SentimentScore.Sentiment.MIXED,
            }

            return {
                "sentiment": sentiment_map.get(sentiment_str, SentimentScore.Sentiment.NEUTRAL),
                "score": round(max(Decimal("-1"), min(Decimal("1"), score)), 3),
                "confidence": round(confidence, 3),
            }
        except Exception as exc:
            logger.error("GPT analysis failed: %s", exc)
            return self._analyze_rule_based(text)

    def _analyze_rule_based(self, text: str) -> dict[str, Any]:
        """Rule-based sentiment analysis as fallback.

        Args:
            text: Input text.

        Returns:
            Dict with sentiment label, score, and confidence.
        """
        words = set(re.findall(r"\b\w+\b", text.lower()))

        pos_count = len(words & POSITIVE_WORDS)
        neg_count = len(words & NEGATIVE_WORDS)
        total = pos_count + neg_count

        if total == 0:
            return {
                "sentiment": SentimentScore.Sentiment.NEUTRAL,
                "score": Decimal("0"),
                "confidence": Decimal("0.3"),
            }

        score = Decimal(str((pos_count - neg_count) / total))
        confidence = Decimal(str(min(total / 10, 1.0)))

        if score > Decimal("0.1"):
            sentiment = SentimentScore.Sentiment.POSITIVE
        elif score < Decimal("-0.1"):
            sentiment = SentimentScore.Sentiment.NEGATIVE
        else:
            sentiment = SentimentScore.Sentiment.NEUTRAL

        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
        }

    def _extract_aspects(self, text: str) -> list[dict[str, Any]]:
        """Extract aspect-based sentiments from text.

        Args:
            text: Input text.

        Returns:
            List of aspect dicts with name, sentiment, and mentions.
        """
        # Common aspect categories
        aspect_keywords: dict[str, list[str]] = {
            "price": ["price", "cost", "expensive", "cheap", "affordable", "value"],
            "quality": ["quality", "durability", "build", "material", "craftsmanship"],
            "service": ["service", "support", "help", "staff", "customer service"],
            "delivery": ["delivery", "shipping", "arrived", "package", "box"],
            "usability": ["easy", "simple", "intuitive", "user-friendly", "complicated"],
            "design": ["design", "look", "appearance", "style", "aesthetic", "color"],
            "performance": ["fast", "slow", "performance", "speed", "powerful", "lag"],
        }

        aspects: list[dict[str, Any]] = []
        text_lower = text.lower()

        for aspect, keywords in aspect_keywords.items():
            mention_count = 0
            aspect_sentiment_words: list[str] = []

            for keyword in keywords:
                if keyword in text_lower:
                    mention_count += text_lower.count(keyword)

            if mention_count > 0:
                # Determine aspect sentiment from surrounding context
                score = Decimal("0")
                for keyword in keywords:
                    idx = text_lower.find(keyword)
                    if idx >= 0:
                        # Check surrounding 50 chars
                        start = max(0, idx - 50)
                        end = min(len(text), idx + len(keyword) + 50)
                        context = text[start:end].lower()
                        ctx_words = set(re.findall(r"\b\w+\b", context))
                        pos = len(ctx_words & POSITIVE_WORDS)
                        neg = len(ctx_words & NEGATIVE_WORDS)
                        if pos + neg > 0:
                            score += Decimal(str((pos - neg) / (pos + neg)))

                if score > Decimal("0.1"):
                    aspect_sentiment = SentimentScore.Sentiment.POSITIVE
                elif score < Decimal("-0.1"):
                    aspect_sentiment = SentimentScore.Sentiment.NEGATIVE
                else:
                    aspect_sentiment = SentimentScore.Sentiment.NEUTRAL

                aspects.append(
                    {
                        "aspect": aspect,
                        "sentiment": aspect_sentiment,
                        "mentions": mention_count,
                        "score": round(score, 3),
                    }
                )

        return sorted(aspects, key=lambda x: x["mentions"], reverse=True)

    def _detect_emotions(self, text: str) -> dict[str, Decimal]:
        """Detect emotions in text.

        Args:
            text: Input text.

        Returns:
            Dict mapping emotion names to intensity scores.
        """
        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))
        emotions: dict[str, Decimal] = {}

        for emotion, keywords in EMOTION_PATTERNS.items():
            emotion_words = set(keywords)
            matches = words & emotion_words
            if matches:
                score = min(len(matches) / 3, 1.0)
                emotions[emotion] = Decimal(str(round(score, 3)))

        return emotions
