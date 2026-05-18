"""On-page audit model.

Defines OnPageAudit for comprehensive page-level SEO auditing
with issue detection, scoring, and recommendations.
"""

from __future__ import annotations

import uuid

from django.db import models


class OnPageAudit(models.Model):
    """A comprehensive on-page SEO audit result.

    Stores crawl results, detected issues, SEO score, grade,
    technical details, and fix recommendations for a single URL.
    """

    class Grade(models.TextChoices):
        """SEO grade based on audit score."""

        A = "A", "A (90-100)"
        B = "B", "B (75-89)"
        C = "C", "C (60-74)"
        D = "D", "D (45-59)"
        F = "F", "F (0-44)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    url = models.URLField(max_length=2048, db_index=True, help_text="Audited URL")
    target_keywords_json = models.JSONField(
        default=list, blank=True, help_text="Keywords targeted for this page"
    )

    # Scoring
    score = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.0, help_text="SEO score 0-100"
    )
    grade = models.CharField(
        max_length=1, choices=Grade.choices, default=Grade.A, help_text="Letter grade"
    )

    # Page elements
    title = models.TextField(blank=True, help_text="Title tag content")
    title_length = models.PositiveIntegerField(default=0)
    meta_description = models.TextField(blank=True)
    meta_description_length = models.PositiveIntegerField(default=0)
    h1 = models.TextField(blank=True)
    h1_count = models.PositiveIntegerField(default=0)
    canonical = models.URLField(max_length=2048, blank=True)
    word_count = models.PositiveIntegerField(default=0)

    # Content quality
    readability_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, help_text="Flesch-Kincaid score"
    )
    keyword_density_json = models.JSONField(
        default=dict, blank=True, help_text="Keyword density percentages"
    )

    # Links
    internal_links = models.PositiveIntegerField(default=0)
    external_links = models.PositiveIntegerField(default=0)
    images_total = models.PositiveIntegerField(default=0)
    images_with_alt = models.PositiveIntegerField(default=0)

    # Structured data
    schema_count = models.PositiveIntegerField(
        default=0, help_text="Number of JSON-LD schema blocks"
    )
    schemas_json = models.JSONField(default=list, blank=True)

    # Issues and recommendations
    issues_json = models.JSONField(
        default=list, blank=True, help_text="Detected issues with severity"
    )
    recommendations_json = models.JSONField(
        default=list, blank=True, help_text="Generated fix recommendations"
    )

    # Open Graph / Twitter Cards
    og_tags_json = models.JSONField(default=dict, blank=True)
    twitter_tags_json = models.JSONField(default=dict, blank=True)

    # Heading hierarchy
    headings_json = models.JSONField(
        default=list, blank=True, help_text="Extracted heading structure"
    )

    metadata_json = models.JSONField(default=dict, blank=True)
    audited_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_onpage_audit"
        verbose_name = "On-Page Audit"
        verbose_name_plural = "On-Page Audits"
        ordering = ["-audited_at"]
        indexes = [
            models.Index(fields=["tenant_id", "url"]),
            models.Index(fields=["tenant_id", "-score"]),
            models.Index(fields=["tenant_id", "-audited_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.url} [{self.grade}]"

    def set_grade(self) -> None:
        """Set the letter grade based on the current score."""
        score_val = float(self.score) if self.score else 100.0
        if score_val >= 90:
            self.grade = self.Grade.A
        elif score_val >= 75:
            self.grade = self.Grade.B
        elif score_val >= 60:
            self.grade = self.Grade.C
        elif score_val >= 45:
            self.grade = self.Grade.D
        else:
            self.grade = self.Grade.F
