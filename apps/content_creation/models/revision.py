"""RevisionHistory model — tracks content generation versions.

Stores word-level diffs between versions with metadata about who
made changes and a human-readable change summary.
"""

from __future__ import annotations

from django.db import models

from .base import UUIDModel


class RevisionHistory(UUIDModel):
    """A single revision of a content generation.

    Attributes:
        content_generation_id: The content generation being revised.
        version_number: Sequential version number (1, 2, 3...).
        diff_json: Word-level diff data (additions, deletions, modifications).
        body_text: Full text of this revision.
        changed_by: UUID of the user who made the change.
        change_summary: Human-readable summary of the change.
        created_at: Timestamp when the revision was created.
    """

    content_generation_id = models.UUIDField(
        db_index=True,
        help_text="Content generation being revised",
    )
    version_number = models.PositiveIntegerField(
        help_text="Sequential version number",
    )
    diff_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Word-level diff {additions, deletions, modifications, summary}",
    )
    body_text = models.TextField(
        blank=True,
        help_text="Full text of this revision",
    )
    changed_by = models.CharField(
        max_length=256,
        help_text="UUID of the user who made the change",
    )
    change_summary = models.CharField(
        max_length=512,
        blank=True,
        help_text="Human-readable change summary",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the revision was created",
    )

    class Meta:
        db_table = "voyager_revision_history"
        verbose_name = "Revision History"
        verbose_name_plural = "Revision Histories"
        ordering = ["-version_number"]
        indexes = [
            models.Index(fields=["content_generation_id", "-version_number"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["content_generation_id", "version_number"],
                name="%(app_label)s_rev_content_version_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"v{self.version_number} of {self.content_generation_id}"
