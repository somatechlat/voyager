"""Django Admin for Social Media app.

Registers InboxMessage, SocialComment, CommunityMember,
HashtagResearch, and InfluencerProfile models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.social_media.models import (
    CommunityMember,
    HashtagResearch,
    InboxMessage,
    InfluencerProfile,
    SocialComment,
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


@admin.register(InboxMessage)
class InboxMessageAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for InboxMessage model."""

    list_display = (
        "platform",
        "type",
        "author_name",
        "text_preview",
        "sentiment",
        "status",
        "assigned_to",
        "response_time_minutes",
        "received_at",
    )
    list_filter = (
        "platform",
        "type",
        "sentiment",
        "status",
        "received_at",
    )
    search_fields = (
        "author_name",
        "author_platform_id",
        "text",
        "platform_message_id",
        "post_id",
        "tenant_id",
    )
    ordering = ("-received_at",)
    readonly_fields = ("id", "received_at", "created_at", "updated_at")
    date_hierarchy = "received_at"

    @admin.display(description="Text")
    def text_preview(self, obj: InboxMessage) -> str:
        return obj.text[:50] if obj.text else "—"


@admin.register(SocialComment)
class SocialCommentAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for SocialComment model."""

    list_display = (
        "platform",
        "author_name",
        "text_preview",
        "sentiment",
        "is_spam",
        "is_hidden",
        "moderation_action",
        "like_count",
        "received_at",
    )
    list_filter = (
        "platform",
        "sentiment",
        "is_spam",
        "is_hidden",
        "moderation_action",
        "received_at",
    )
    search_fields = (
        "author_name",
        "text",
        "post_id",
        "platform_comment_id",
        "tenant_id",
    )
    ordering = ("-received_at",)
    readonly_fields = ("id", "received_at", "created_at", "updated_at")
    date_hierarchy = "received_at"

    @admin.display(description="Text")
    def text_preview(self, obj: SocialComment) -> str:
        return obj.text[:50] if obj.text else "—"

    @admin.display(description="Spam Reasons")
    def display_spam_reasons(self, obj: SocialComment) -> str:
        return self._format_json(obj.spam_reasons, 150)

    @admin.display(description="AI Suggestions")
    def display_suggestions(self, obj: SocialComment) -> str:
        return self._format_json(obj.ai_suggestions, 200)


@admin.register(CommunityMember)
class CommunityMemberAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for CommunityMember model."""

    list_display = (
        "name",
        "platform",
        "followers",
        "engagement_score",
        "influence_score",
        "vip_score",
        "tier",
        "total_interactions",
        "last_active_at",
    )
    list_filter = (
        "platform",
        "tier",
        "first_seen_at",
        "last_active_at",
    )
    search_fields = (
        "name",
        "platform_user_id",
        "bio",
        "tenant_id",
    )
    ordering = ("-vip_score", "-engagement_score")
    readonly_fields = (
        "id",
        "first_seen_at",
        "last_active_at",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Interactions")
    def display_interactions(self, obj: CommunityMember) -> str:
        return self._format_json(obj.interaction_breakdown, 200)


@admin.register(HashtagResearch)
class HashtagResearchAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for HashtagResearch model."""

    list_display = (
        "hashtag",
        "platform",
        "total_posts",
        "posts_last_week",
        "competition_score",
        "opportunity_score",
        "recommendation",
        "trend_direction",
        "category",
    )
    list_filter = (
        "platform",
        "recommendation",
        "trend_direction",
        "category",
    )
    search_fields = (
        "hashtag",
        "category",
        "tenant_id",
    )
    ordering = ("-opportunity_score", "-posts_last_week")
    readonly_fields = ("id", "researched_at", "created_at", "updated_at")


@admin.register(InfluencerProfile)
class InfluencerProfileAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for InfluencerProfile model."""

    list_display = (
        "name",
        "platform",
        "followers",
        "engagement_rate",
        "authenticity_score",
        "content_quality_score",
        "match_score",
        "status",
        "outreach_status",
        "created_at",
    )
    list_filter = (
        "platform",
        "status",
        "outreach_status",
        "created_at",
    )
    search_fields = (
        "name",
        "platform_user_id",
        "bio",
        "contact_email",
        "tenant_id",
    )
    ordering = ("-match_score", "-engagement_rate")
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Demographics")
    def display_demographics(self, obj: InfluencerProfile) -> str:
        return self._format_json(obj.audience_demographics, 200)

    @admin.display(description="Red Flags")
    def display_flags(self, obj: InfluencerProfile) -> str:
        return self._format_json(obj.red_flags, 200)

    @admin.display(description="Niche")
    def display_niche(self, obj: InfluencerProfile) -> str:
        return self._format_json(obj.niche, 150)
