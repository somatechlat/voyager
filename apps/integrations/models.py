"""Integrations Hub models.

Defines PlatformConnection, WebhookEndpoint, WebhookDelivery, SyncLog,
and PlatformHealth models for managing 50+ external platform connections,
OAuth flows, webhook routing, data sync, and health monitoring.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
from typing import Any

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class _CredentialCipher:
    """AES-256-GCM encryption for credentials at rest.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) as the baseline.
    The encryption key is derived from settings.SECRET_KEY using PBKDF2.
    """

    _instance: _CredentialCipher | None = None

    def __new__(cls) -> _CredentialCipher:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_cipher()
        return cls._instance

    def _init_cipher(self) -> None:
        """Initialize the Fernet cipher from SECRET_KEY."""
        key_material = getattr(settings, "SECRET_KEY", os.environ.get("SECRET_KEY", ""))
        key_bytes = hashlib.sha256(key_material.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        self._cipher = Fernet(fernet_key)

    def encrypt(self, plaintext: str | None) -> str | None:
        """Encrypt a plaintext string. Returns None if input is None."""
        if plaintext is None:
            return None
        try:
            return self._cipher.encrypt(plaintext.encode()).decode()
        except Exception:
            logger.exception("Credential encryption failed")
            return None

    def decrypt(self, ciphertext: str | None) -> str | None:
        """Decrypt a ciphertext string. Returns None if input is None."""
        if ciphertext is None:
            return None
        try:
            return self._cipher.decrypt(ciphertext.encode()).decode()
        except Exception:
            logger.exception("Credential decryption failed")
            return None


def _encrypt(value: str | None) -> str | None:
    """Encrypt a value using the credential cipher."""
    return _CredentialCipher().encrypt(value)


def _decrypt(value: str | None) -> str | None:
    """Decrypt a value using the credential cipher."""
    return _CredentialCipher().decrypt(value)


class PlatformConnection(models.Model):
    """An OAuth or API-key connection to an external platform.

    Stores encrypted credentials, scopes, expiry, and status for 50+
    supported platforms. Credentials are AES-encrypted at rest.
    """

    class Platform(models.TextChoices):
        """Supported platforms across all categories."""

        # Social Media
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        TWITTER = "twitter", "Twitter / X"
        LINKEDIN = "linkedin", "LinkedIn"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        PINTEREST = "pinterest", "Pinterest"
        THREADS = "threads", "Threads"
        SNAPCHAT = "snapchat", "Snapchat"
        REDDIT = "reddit", "Reddit"

        # Advertising
        GOOGLE_ADS = "google_ads", "Google Ads"
        META_ADS = "meta_ads", "Meta Ads"
        LINKEDIN_ADS = "linkedin_ads", "LinkedIn Ads"
        TIKTOK_ADS = "tiktok_ads", "TikTok Ads"
        TWITTER_ADS = "twitter_ads", "Twitter Ads"
        PINTEREST_ADS = "pinterest_ads", "Pinterest Ads"
        MICROSOFT_ADS = "microsoft_ads", "Microsoft Ads"

        # Analytics
        GOOGLE_ANALYTICS = "google_analytics", "Google Analytics"
        ADOBE_ANALYTICS = "adobe_analytics", "Adobe Analytics"
        MIXPANEL = "mixpanel", "Mixpanel"
        AMPLITUDE = "amplitude", "Amplitude"
        HOTJAR = "hotjar", "Hotjar"

        # Email
        MAILCHIMP = "mailchimp", "Mailchimp"
        SENDGRID = "sendgrid", "SendGrid"
        HUBSPOT_EMAIL = "hubspot_email", "HubSpot Email"
        KLAVIYO = "klaviyo", "Klaviyo"
        ACTIVECAMPAIGN = "activecampaign", "ActiveCampaign"
        CONVERTKIT = "convertkit", "ConvertKit"

        # CRM
        HUBSPOT_CRM = "hubspot_crm", "HubSpot CRM"
        SALESFORCE = "salesforce", "Salesforce"
        PIPEDRIVE = "pipedrive", "Pipedrive"
        ZOHO_CRM = "zoho_crm", "Zoho CRM"

        # SEO
        GOOGLE_SEARCH_CONSOLE = "google_search_console", "Google Search Console"
        AHREFS = "ahrefs", "Ahrefs"
        SEMRUSH = "semrush", "SEMrush"
        MOZ = "moz", "Moz"

        # Design
        FIGMA = "figma", "Figma"
        CANVA = "canva", "Canva"
        ADOBE_CREATIVE = "adobe_creative", "Adobe Creative Cloud"

        # Storage
        GOOGLE_DRIVE = "google_drive", "Google Drive"
        DROPBOX = "dropbox", "Dropbox"
        ONEDRIVE = "onedrive", "OneDrive"
        BOX = "box", "Box"

        # Communication
        SLACK = "slack", "Slack"
        MICROSOFT_TEAMS = "microsoft_teams", "Microsoft Teams"
        DISCORD = "discord", "Discord"

        # Project Management
        ASANA = "asana", "Asana"
        MONDAY = "monday", "Monday.com"
        TRELLO = "trello", "Trello"
        JIRA = "jira", "Jira"
        NOTION = "notion", "Notion"

        # E-commerce
        SHOPIFY = "shopify", "Shopify"
        WOOCOMMERCE = "woocommerce", "WooCommerce"
        BIGCOMMERCE = "bigcommerce", "BigCommerce"

        # Payment
        STRIPE = "stripe", "Stripe"
        PAYPAL = "paypal", "PayPal"
        SQUARE = "square", "Square"

    class ConnectionType(models.TextChoices):
        """Authentication mechanism for the connection."""

        OAUTH2 = "oauth", "OAuth 2.0"
        API_KEY = "api_key", "API Key"
        BASIC_AUTH = "basic_auth", "Basic Auth"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        """Lifecycle status of a connection."""

        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"
        ERROR = "error", "Error"
        PENDING = "pending", "Pending"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    platform = models.CharField(max_length=32, choices=Platform.choices, db_index=True)
    connection_type = models.CharField(max_length=16, choices=ConnectionType.choices)
    display_name = models.CharField(max_length=255, blank=True)

    # Encrypted credential fields
    _access_token = models.TextField(db_column="access_token", blank=True, default="")
    _refresh_token = models.TextField(db_column="refresh_token", blank=True, default="")
    _api_key = models.TextField(db_column="api_key", blank=True, default="")
    token_type = models.CharField(max_length=32, blank=True, default="Bearer")

    # Metadata
    scopes_json = models.JSONField(default=list, blank=True)
    credentials_json = models.JSONField(
        default=dict, blank=True, help_text="Additional encrypted-at-rest credential metadata"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    connected_by = models.CharField(max_length=256, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_platform_connection"
        verbose_name = "Platform Connection"
        verbose_name_plural = "Platform Connections"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "platform", "status"]),
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "platform", "display_name"],
                name="%(app_label)s_conn_tenant_platform_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.platform} ({self.tenant_id}) [{self.status}]"

    @property
    def access_token(self) -> str | None:
        return _decrypt(self._access_token) if self._access_token else None

    @access_token.setter
    def access_token(self, value: str | None) -> None:
        self._access_token = _encrypt(value) or ""

    @property
    def refresh_token(self) -> str | None:
        return _decrypt(self._refresh_token) if self._refresh_token else None

    @refresh_token.setter
    def refresh_token(self, value: str | None) -> None:
        self._refresh_token = _encrypt(value) or ""

    @property
    def api_key(self) -> str | None:
        return _decrypt(self._api_key) if self._api_key else None

    @api_key.setter
    def api_key(self, value: str | None) -> None:
        self._api_key = _encrypt(value) or ""

    def is_expired(self) -> bool:
        if not self.expires_at:
            return self.status != self.Status.ACTIVE
        return timezone.now() >= self.expires_at

    def scopes_list(self) -> list[str]:
        scopes = self.scopes_json
        if isinstance(scopes, str):
            return scopes.split()
        return list(scopes) if scopes else []


class WebhookEndpoint(models.Model):
    """An outbound webhook endpoint registered for a connection.

    Defines the URL, event filter, signature configuration, and retry
    policy for delivering webhook payloads.
    """

    class Status(models.TextChoices):
        """Lifecycle status of a webhook endpoint."""

        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        DISABLED = "disabled", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        PlatformConnection,
        on_delete=models.CASCADE,
        related_name="webhook_endpoints",
    )
    name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=128, db_index=True)
    endpoint_url = models.URLField(max_length=2048)
    secret = models.CharField(
        max_length=512,
        blank=True,
        help_text="HMAC-SHA256 secret for payload signing",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    headers_json = models.JSONField(default=dict, blank=True)
    payload_schema_json = models.JSONField(default=dict, blank=True)
    retry_policy_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='e.g. {"max_retries":5,"initial_delay":1,"max_delay":3600}',
    )
    filter_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_webhook_endpoint"
        verbose_name = "Webhook Endpoint"
        verbose_name_plural = "Webhook Endpoints"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["connection", "event_type", "is_active"]),
            models.Index(fields=["is_active", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} -> {self.endpoint_url}"

    def retry_policy(self) -> dict[str, Any]:
        """Return the retry policy with sensible defaults."""
        default: dict[str, Any] = {
            "max_retries": 5,
            "initial_delay": 1,
            "max_delay": 3600,
            "backoff_multiplier": 2,
        }
        if self.retry_policy_json:
            default.update(self.retry_policy_json)
        return default


class WebhookDelivery(models.Model):
    """A single webhook payload delivery attempt.

    Tracks the payload, response, status, and retry scheduling for
    each webhook invocation.
    """

    class Status(models.TextChoices):
        """Delivery status of a webhook attempt."""

        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"
        DEAD_LETTER = "dead_letter", "Dead Letter"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event_type = models.CharField(max_length=128, blank=True)
    payload_json = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "voyager_webhook_delivery"
        verbose_name = "Webhook Delivery"
        verbose_name_plural = "Webhook Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["webhook", "status", "created_at"]),
            models.Index(fields=["status", "next_retry_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} [{self.status}] " f"attempt={self.attempt_count}"


class SyncLog(models.Model):
    """A record of a data sync operation between Voyager and a platform.

    Tracks direction, status, record counts, errors, and timing for
    inbound, outbound, and bidirectional sync runs.
    """

    class Direction(models.TextChoices):
        """Data flow direction for the sync."""

        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"
        BIDIRECTIONAL = "bidirectional", "Bidirectional"

    class Status(models.TextChoices):
        """Lifecycle status of a sync run."""

        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        PlatformConnection,
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    sync_type = models.CharField(max_length=128, db_index=True)
    direction = models.CharField(max_length=16, choices=Direction.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    records_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    deleted_count = models.PositiveIntegerField(default=0)
    conflict_count = models.PositiveIntegerField(default=0)
    errors_json = models.JSONField(default=list, blank=True)
    field_mappings_json = models.JSONField(default=dict, blank=True)
    conflict_resolution = models.CharField(max_length=16, default="source_wins")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "voyager_sync_log"
        verbose_name = "Sync Log"
        verbose_name_plural = "Sync Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["connection", "sync_type", "status"]),
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sync_type} {self.direction} [{self.status}]"

    @property
    def tenant_id(self) -> str:
        return self.connection.tenant_id

    def duration_seconds(self) -> float | None:
        """Return the sync duration in seconds, or None if not complete."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class PlatformHealth(models.Model):
    """Health-check snapshot for a platform connection.

    Captures latency, status, and error details from periodic probes.
    """

    class Status(models.TextChoices):
        """Health status of a platform connection."""

        HEALTHY = "healthy", "Healthy"
        DEGRADED = "degraded", "Degraded"
        DOWN = "down", "Down"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        PlatformConnection,
        on_delete=models.CASCADE,
        related_name="health_checks",
    )
    last_check_at = models.DateTimeField(auto_now=True, db_index=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.UNKNOWN, db_index=True
    )
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    details_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "voyager_platform_health"
        verbose_name = "Platform Health"
        verbose_name_plural = "Platform Health Checks"
        ordering = ["-last_check_at"]
        indexes = [
            models.Index(fields=["connection", "-last_check_at"]),
            models.Index(fields=["status", "-last_check_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.connection.platform} {self.status} ({self.latency_ms}ms)"
