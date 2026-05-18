"""Deliverability monitoring model for sender reputation tracking."""

from __future__ import annotations

from django.db import models


class DeliverabilityMonitor(models.Model):
    """Tracks sender reputation, authentication, and deliverability metrics.

    Monitors SPF, DKIM, DMARC, BIMI authentication, bounce rates,
    spam complaints, blacklist status, and overall sender reputation.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        domain: The sending domain being monitored.
        spf_configured: Whether SPF record is present.
        spf_valid: Whether SPF record is valid.
        spf_includes: SPF include mechanisms.
        dkim_configured: Whether DKIM record is present.
        dkim_valid: Whether DKIM record is valid.
        dkim_selector: DKIM selector used.
        dmarc_configured: Whether DMARC record is present.
        dmarc_policy: DMARC policy (none, quarantine, reject).
        dmarc_rua: DMARC aggregate report URI.
        dmarc_ruf: DMARC forensic report URI.
        bimi_configured: Whether BIMI record is present.
        bimi_logo_url: BIMI logo URL.
        reputation_score: Overall sender reputation score (0-100).
        reputation_grade: Letter grade (A, B, C, F).
        bounce_rate: Current bounce rate.
        spam_complaint_rate: Current spam complaint rate.
        blacklist_status: JSON blacklist check results.
        volume_24h: Emails sent in last 24 hours.
        volume_7d: Emails sent in last 7 days.
        volume_30d: Emails sent in last 30 days.
        inbox_placement_pct: Inbox placement rate.
        checked_at: Last check timestamp.
        recommendations: JSON array of improvement recommendations.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class DmarcPolicy(models.TextChoices):
        """DMARC policy options."""

        NONE = "none", "None"
        QUARANTINE = "quarantine", "Quarantine"
        REJECT = "reject", "Reject"
        UNKNOWN = "unknown", "Unknown"

    class Grade(models.TextChoices):
        """Reputation grade options."""

        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"
        F = "F", "F"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    domain = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Sending domain being monitored",
    )
    spf_configured = models.BooleanField(
        default=False,
        help_text="Whether SPF record is present",
    )
    spf_valid = models.BooleanField(
        default=False,
        help_text="Whether SPF record is valid",
    )
    spf_includes = models.JSONField(
        default=list,
        blank=True,
        help_text="SPF include mechanisms",
    )
    dkim_configured = models.BooleanField(
        default=False,
        help_text="Whether DKIM record is present",
    )
    dkim_valid = models.BooleanField(
        default=False,
        help_text="Whether DKIM record is valid",
    )
    dkim_selector = models.CharField(
        max_length=50,
        blank=True,
        default="default",
        help_text="DKIM selector used",
    )
    dmarc_configured = models.BooleanField(
        default=False,
        help_text="Whether DMARC record is present",
    )
    dmarc_policy = models.CharField(
        max_length=20,
        choices=DmarcPolicy.choices,
        default=DmarcPolicy.UNKNOWN,
        help_text="DMARC policy",
    )
    dmarc_rua = models.URLField(
        blank=True,
        help_text="DMARC aggregate report URI",
    )
    dmarc_ruf = models.URLField(
        blank=True,
        help_text="DMARC forensic report URI",
    )
    bimi_configured = models.BooleanField(
        default=False,
        help_text="Whether BIMI record is present",
    )
    bimi_logo_url = models.URLField(
        blank=True,
        help_text="BIMI logo URL",
    )
    reputation_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Overall sender reputation score (0-100)",
    )
    reputation_grade = models.CharField(
        max_length=1,
        choices=Grade.choices,
        default=Grade.F,
        help_text="Letter grade",
    )
    bounce_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0.0000,
        help_text="Current bounce rate",
    )
    spam_complaint_rate = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        default=0.000000,
        help_text="Current spam complaint rate",
    )
    blacklist_status = models.JSONField(
        default=dict,
        blank=True,
        help_text="Blacklist check results",
    )
    volume_24h = models.PositiveIntegerField(
        default=0,
        help_text="Emails sent in last 24 hours",
    )
    volume_7d = models.PositiveIntegerField(
        default=0,
        help_text="Emails sent in last 7 days",
    )
    volume_30d = models.PositiveIntegerField(
        default=0,
        help_text="Emails sent in last 30 days",
    )
    inbox_placement_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Inbox placement rate",
    )
    checked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last check timestamp",
    )
    recommendations = models.JSONField(
        default=list,
        blank=True,
        help_text="Improvement recommendations",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_deliverability_monitor"
        verbose_name = "Deliverability Monitor"
        verbose_name_plural = "Deliverability Monitors"
        ordering = ["-checked_at", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "domain"]),
            models.Index(fields=["tenant_id", "reputation_score"]),
            models.Index(fields=["tenant_id", "checked_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.domain} (Score: {self.reputation_score}, Grade: {self.reputation_grade})"

    @property
    def authentication_score(self) -> int:
        """Calculate authentication score from SPF, DKIM, DMARC, BIMI.

        Returns:
            Score from 0-100 based on authentication configuration.
        """
        score = 0
        if self.spf_configured and self.spf_valid:
            score += 25
        elif self.spf_configured:
            score += 10
        if self.dkim_configured and self.dkim_valid:
            score += 25
        elif self.dkim_configured:
            score += 10
        if self.dmarc_configured:
            if self.dmarc_policy == self.DmarcPolicy.REJECT:
                score += 30
            elif self.dmarc_policy == self.DmarcPolicy.QUARANTINE:
                score += 20
            elif self.dmarc_policy == self.DmarcPolicy.NONE:
                score += 10
        if self.bimi_configured:
            score += 20
        return score

    @property
    def is_healthy(self) -> bool:
        """Return whether the domain's deliverability is healthy."""
        return (
            self.reputation_score is not None
            and self.reputation_score >= 75
            and not self.blacklist_status.get("listed", False)
        )
