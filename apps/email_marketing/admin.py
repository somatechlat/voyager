"""Django Admin for Email Marketing app.

Registers EmailTemplate, EmailCampaign, AutomationSequence,
and AudienceSegment models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.email_marketing.models import (
    AudienceSegment,
    AutomationSequence,
    EmailCampaign,
    EmailTemplate,
)


class _JSONMixin:
    """Mixin for formatting JSON fields."""

    @staticmethod
    def _format_json(value: object, max_len: int = 200) -> str:
        if not value:
            return "—"
        if isinstance(value, (dict, list)):
            text = json.dumps(value, indent=2, default=str)
            if len(text) > max_len:
                return text[:max_len] + "..."
            return text
        return str(value)[:max_len]


class _TenantIdMixin:
    """Mixin for shortening tenant_id display."""

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj):
        tid = getattr(obj, "tenant_id", "")
        return tid[:12] + "..." if len(str(tid)) > 12 else str(tid)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for EmailTemplate model."""

    list_display = (
        "name",
        "category",
        "is_amp",
        "compatibility_score",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("category", "is_amp", "created_at")
    search_fields = ("name", "preheader_text", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Brand Kit")
    def display_brand(self, obj: EmailTemplate) -> str:
        return self._format_json(obj.brand_kit, 150)

    @admin.display(description="Compatibility")
    def display_compat(self, obj: EmailTemplate) -> str:
        return self._format_json(obj.compatibility_results, 200)

    @admin.display(description="Design")
    def display_design(self, obj: EmailTemplate) -> str:
        return self._format_json(obj.json_design, 200)


@admin.register(EmailCampaign)
class EmailCampaignAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for EmailCampaign model."""

    list_display = (
        "name",
        "status",
        "subject_line",
        "from_email",
        "total_recipients",
        "delivered",
        "unique_opens",
        "unique_clicks",
        "bounce_rate_display",
        "scheduled_at",
        "sent_at",
    )
    list_filter = (
        "status",
        "scheduled_at",
        "sent_at",
        "created_at",
    )
    search_fields = (
        "name",
        "subject_line",
        "from_email",
        "reply_to",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "total_recipients",
        "delivered",
        "opens",
        "unique_opens",
        "clicks",
        "unique_clicks",
        "bounces",
        "hard_bounces",
        "spam_complaints",
        "unsubscribes",
        "revenue",
        "send_progress_pct",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "scheduled_at"
    list_select_related = ("template",)

    @admin.display(description="Open Rate")
    def open_rate_display(self, obj: EmailCampaign) -> str:
        return f"{obj.open_rate:.1f}%"

    @admin.display(description="Click Rate")
    def click_rate_display(self, obj: EmailCampaign) -> str:
        return f"{obj.click_rate:.1f}%"

    @admin.display(description="Bounce Rate")
    def bounce_rate_display(self, obj: EmailCampaign) -> str:
        return f"{obj.bounce_rate:.1f}%"

    @admin.display(description="Delivery Rate")
    def delivery_rate_display(self, obj: EmailCampaign) -> str:
        return f"{obj.delivery_rate:.1f}%"


@admin.register(AutomationSequence)
class AutomationSequenceAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for AutomationSequence model."""

    list_display = (
        "name",
        "trigger_type",
        "status",
        "total_enrolled",
        "total_completed",
        "completion_rate",
        "frequency_cap",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "trigger_type",
        "status",
        "created_at",
    )
    search_fields = ("name", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "total_enrolled",
        "total_completed",
        "total_exited",
        "avg_completion_time_hours",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Steps")
    def display_steps(self, obj: AutomationSequence) -> str:
        return self._format_json(obj.steps, 300)

    @admin.display(description="Trigger Config")
    def display_trigger(self, obj: AutomationSequence) -> str:
        return self._format_json(obj.trigger_config, 200)

    @admin.display(description="Entry Criteria")
    def display_entry(self, obj: AutomationSequence) -> str:
        return self._format_json(obj.entry_criteria, 150)

    @admin.display(description="Exit Criteria")
    def display_exit(self, obj: AutomationSequence) -> str:
        return self._format_json(obj.exit_criteria, 150)


@admin.register(AudienceSegment)
class AudienceSegmentAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for AudienceSegment model."""

    list_display = (
        "name",
        "segment_type",
        "subscriber_count",
        "predictive_type",
        "is_system",
        "rfm_enabled",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "segment_type",
        "predictive_type",
        "is_system",
        "rfm_enabled",
        "created_at",
    )
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Rules")
    def display_rules(self, obj: AudienceSegment) -> str:
        return self._format_json(obj.rules, 250)

    @admin.display(description="RFM Config")
    def display_rfm(self, obj: AudienceSegment) -> str:
        return self._format_json(obj.rfm_config, 200)
