"""Editorial Calendar model — SP-004.

Stores editorial calendar entries with content type color coding,
workload tracking, and publishing pipeline status.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class EditorialCalendar(UUIDModel, TimeStampedModel, TenantModel):
    """An editorial calendar entry for content planning and workload tracking.

    Attributes:
        title: Content piece title.
        content_type: Type of content (blog_post, social_post, video, etc.).
        platform: Target platform (e.g. 'linkedin', 'instagram').
        strategy: Optional parent content strategy.
        campaign_id: Optional linked campaign UUID.
        assignee_id: UUID of assigned team member.
        due_date: Internal deadline.
        publish_date: Scheduled publication date.
        status: Pipeline stage (ideation → published).
        priority: Priority level 1-5 (1 = highest).
        estimated_hours: Estimated work hours.
        actual_hours: Actual hours logged.
        notes: Additional planning notes.
    """

    class ContentType(models.TextChoices):
        BLOG_POST = "blog_post", "Blog Post"
        SOCIAL_POST = "social_post", "Social Post"
        VIDEO = "video", "Video"
        EMAIL = "email", "Email"
        INFOGRAPHIC = "infographic", "Infographic"
        PODCAST = "podcast", "Podcast"
        CASE_STUDY = "case_study", "Case Study"
        WEBINAR = "webinar", "Webinar"
        WHITEPAPER = "whitepaper", "Whitepaper"
        PRESS_RELEASE = "press_release", "Press Release"

    class Status(models.TextChoices):
        IDEATION = "ideation", "Ideation"
        IN_CREATION = "in_creation", "In Creation"
        REVIEW = "review", "Review"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"

    # Content type color mapping (hex codes for frontend)
    CONTENT_TYPE_COLORS = {
        "blog_post": "#3B82F6",
        "social_post": "#10B981",
        "video": "#8B5CF6",
        "email": "#F59E0B",
        "infographic": "#EC4899",
        "podcast": "#6366F1",
        "case_study": "#14B8A6",
        "webinar": "#EF4444",
        "whitepaper": "#D97706",
        "press_release": "#6B7280",
    }

    title = models.CharField(
        max_length=500,
        help_text="Content piece title",
    )
    content_type = models.CharField(
        max_length=50,
        choices=ContentType.choices,
        db_index=True,
        help_text="Type of content",
    )
    platform = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Target platform (e.g. 'linkedin', 'instagram')",
    )
    strategy = models.ForeignKey(
        "strategy.ContentStrategy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_entries",
        help_text="Parent content strategy",
    )
    campaign_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Linked campaign UUID",
    )
    assignee_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Assigned team member UUID",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Internal deadline",
    )
    publish_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Scheduled publication date",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.IDEATION,
        db_index=True,
        help_text="Pipeline stage",
    )
    priority = models.PositiveSmallIntegerField(
        default=3,
        help_text="Priority 1-5 (1 = highest, 5 = lowest)",
    )
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated work hours",
    )
    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual hours logged",
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional planning notes",
    )

    class Meta:
        db_table = "voyager_editorial_calendar"
        verbose_name = "Editorial Calendar Entry"
        verbose_name_plural = "Editorial Calendar Entries"
        ordering = ["publish_date", "priority"]
        indexes = [
            models.Index(fields=["tenant_id", "publish_date"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "assignee_id"]),
            models.Index(fields=["tenant_id", "content_type"]),
            models.Index(fields=["tenant_id", "campaign_id"]),
            models.Index(fields=["tenant_id", "due_date"]),
            models.Index(fields=["tenant_id", "priority"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.content_type}) — {self.status}"

    @property
    def color_code(self) -> str:
        """Return the hex color code for this content type."""
        return self.CONTENT_TYPE_COLORS.get(self.content_type, "#6B7280")
