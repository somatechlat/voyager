"""Content optimization model.

Defines ContentOptimization for NLP-powered content analysis
with readability scoring, topic coverage, and competitor benchmarking.
"""

from __future__ import annotations

import uuid

from django.db import models


class ContentOptimization(models.Model):
    """A content optimization analysis result.

    Stores readability scores, keyword density analysis, topic coverage,
    competitor benchmark data, and optimization recommendations.
    """

    class Priority(models.TextChoices):
        """Recommendation priority levels."""

        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    url = models.URLField(max_length=2048, blank=True, help_text="URL of analyzed content")
    content_hash = models.CharField(
        max_length=64, blank=True, db_index=True, help_text="SHA-256 hash of content"
    )

    # Target keywords
    target_keywords_json = models.JSONField(default=list, blank=True)
    competitor_urls_json = models.JSONField(default=list, blank=True)

    # Content metrics
    word_count = models.PositiveIntegerField(default=0)
    sentence_count = models.PositiveIntegerField(default=0)
    paragraph_count = models.PositiveIntegerField(default=0)

    # Readability
    flesch_reading_ease = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    flesch_kincaid_grade = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    smog_index = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )

    # Keyword analysis
    keyword_density_json = models.JSONField(
        default=dict, blank=True, help_text="Keyword density percentages per target"
    )
    lsi_keywords_json = models.JSONField(
        default=list, blank=True, help_text="Latent Semantic Indexing keywords found"
    )
    keyword_placement_json = models.JSONField(
        default=dict, blank=True, help_text="Keyword positions in content"
    )

    # Topic coverage
    entities_json = models.JSONField(
        default=list, blank=True, help_text="Named entities extracted"
    )
    topics_covered_json = models.JSONField(
        default=list, blank=True, help_text="Topics detected in content"
    )
    missing_topics_json = models.JSONField(
        default=list, blank=True, help_text="Topics competitors cover but this content doesn't"
    )

    # Competitor benchmark
    competitor_avg_word_count = models.PositiveIntegerField(
        null=True, blank=True
    )
    competitor_avg_readability = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    competitor_common_topics_json = models.JSONField(default=list, blank=True)

    # Headings
    heading_structure_json = models.JSONField(
        default=list, blank=True, help_text="H1-H6 structure"
    )

    # Scoring
    content_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, help_text="Overall score 0-100"
    )
    readability_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    seo_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    uniqueness_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Recommendations
    recommendations_json = models.JSONField(
        default=list, blank=True, help_text="Optimization recommendations with priority"
    )

    # Meta suggestions
    suggested_title = models.TextField(blank=True)
    suggested_meta_description = models.TextField(blank=True)

    metadata_json = models.JSONField(default=dict, blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_content_optimization"
        verbose_name = "Content Optimization"
        verbose_name_plural = "Content Optimizations"
        ordering = ["-analyzed_at"]
        indexes = [
            models.Index(fields=["tenant_id", "url"]),
            models.Index(fields=["tenant_id", "content_hash"]),
            models.Index(fields=["tenant_id", "-content_score"]),
            models.Index(fields=["tenant_id", "-analyzed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.url} (score={self.content_score})"
