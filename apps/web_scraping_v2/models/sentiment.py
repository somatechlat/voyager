"""SentimentScore model — multi-model sentiment analysis results."""

from __future__ import annotations

import uuid

from django.db import models


class SentimentScore(models.Model):
    """Sentiment analysis result for a piece of text.

    Supports multi-model analysis (BERT for short text, GPT for long)
    with aspect-based breakdown and emotion detection.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        text: The analyzed text content.
        text_hash: SHA-256 hash of text for caching/duplicate detection.
        source_type: Type of content (mention, review, article, etc.).
        source_id: Optional reference to the source record.
        model: The model used for analysis.
        overall_sentiment: Primary sentiment label.
        overall_score: Numeric score from -1.0 (negative) to 1.0 (positive).
        confidence: Confidence level of the analysis (0-1).
        aspects: JSON list of aspect-based sentiments.
        emotions: JSON mapping of emotion labels to scores.
        language: Detected language code.
        analyzed_at: When the analysis was performed.
        created_at: Record creation timestamp.
    """

    class Sentiment(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEGATIVE = "negative", "Negative"
        NEUTRAL = "neutral", "Neutral"
        MIXED = "mixed", "Mixed"

    class ModelType(models.TextChoices):
        BERT = "bert", "BERT"
        GPT = "gpt", "GPT"
        AUTO = "auto", "Auto"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    text = models.TextField()
    text_hash = models.CharField(max_length=64, db_index=True)
    source_type = models.CharField(max_length=50, blank=True, default="")
    source_id = models.CharField(max_length=64, blank=True, default="")
    model = models.CharField(max_length=10, choices=ModelType.choices, default=ModelType.AUTO)
    overall_sentiment = models.CharField(max_length=20, choices=Sentiment.choices)
    overall_score = models.DecimalField(max_digits=4, decimal_places=3)
    confidence = models.DecimalField(max_digits=4, decimal_places=3)
    aspects = models.JSONField(default=list, blank=True)
    emotions = models.JSONField(default=dict, blank=True)
    language = models.CharField(max_length=10, default="en")
    analyzed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ws_sentiment_scores"
        indexes = [
            models.Index(fields=["tenant_id", "analyzed_at"]),
            models.Index(fields=["text_hash"]),
            models.Index(fields=["overall_sentiment"]),
        ]
        ordering = ["-analyzed_at"]

    def __str__(self) -> str:
        return f"Sentiment({self.overall_sentiment}, score={self.overall_score})"
