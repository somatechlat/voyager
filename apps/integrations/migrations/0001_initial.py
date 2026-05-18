"""Initial migration for the Integrations Hub.

Creates PlatformConnection, WebhookEndpoint, WebhookDelivery, SyncLog,
and PlatformHealth models with full indexes and constraints.
"""

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration for integrations app."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        # -- PlatformConnection -----------------------------------------------
        migrations.CreateModel(
            name="PlatformConnection",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(db_index=True, max_length=128),
                ),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            # Social Media
                            ("facebook", "Facebook"),
                            ("instagram", "Instagram"),
                            ("twitter", "Twitter / X"),
                            ("linkedin", "LinkedIn"),
                            ("tiktok", "TikTok"),
                            ("youtube", "YouTube"),
                            ("pinterest", "Pinterest"),
                            ("threads", "Threads"),
                            ("snapchat", "Snapchat"),
                            ("reddit", "Reddit"),
                            # Advertising
                            ("google_ads", "Google Ads"),
                            ("meta_ads", "Meta Ads"),
                            ("linkedin_ads", "LinkedIn Ads"),
                            ("tiktok_ads", "TikTok Ads"),
                            ("twitter_ads", "Twitter Ads"),
                            ("pinterest_ads", "Pinterest Ads"),
                            ("microsoft_ads", "Microsoft Ads"),
                            # Analytics
                            ("google_analytics", "Google Analytics"),
                            ("adobe_analytics", "Adobe Analytics"),
                            ("mixpanel", "Mixpanel"),
                            ("amplitude", "Amplitude"),
                            ("hotjar", "Hotjar"),
                            # Email
                            ("mailchimp", "Mailchimp"),
                            ("sendgrid", "SendGrid"),
                            ("hubspot_email", "HubSpot Email"),
                            ("klaviyo", "Klaviyo"),
                            ("activecampaign", "ActiveCampaign"),
                            ("convertkit", "ConvertKit"),
                            # CRM
                            ("hubspot_crm", "HubSpot CRM"),
                            ("salesforce", "Salesforce"),
                            ("pipedrive", "Pipedrive"),
                            ("zoho_crm", "Zoho CRM"),
                            # SEO
                            ("google_search_console", "Google Search Console"),
                            ("ahrefs", "Ahrefs"),
                            ("semrush", "SEMrush"),
                            ("moz", "Moz"),
                            # Design
                            ("figma", "Figma"),
                            ("canva", "Canva"),
                            ("adobe_creative", "Adobe Creative Cloud"),
                            # Storage
                            ("google_drive", "Google Drive"),
                            ("dropbox", "Dropbox"),
                            ("onedrive", "OneDrive"),
                            ("box", "Box"),
                            # Communication
                            ("slack", "Slack"),
                            ("microsoft_teams", "Microsoft Teams"),
                            ("discord", "Discord"),
                            # Project Management
                            ("asana", "Asana"),
                            ("monday", "Monday.com"),
                            ("trello", "Trello"),
                            ("jira", "Jira"),
                            ("notion", "Notion"),
                            # E-commerce
                            ("shopify", "Shopify"),
                            ("woocommerce", "WooCommerce"),
                            ("bigcommerce", "BigCommerce"),
                            # Payment
                            ("stripe", "Stripe"),
                            ("paypal", "PayPal"),
                            ("square", "Square"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                (
                    "connection_type",
                    models.CharField(
                        choices=[
                            ("oauth", "OAuth 2.0"),
                            ("api_key", "API Key"),
                            ("basic_auth", "Basic Auth"),
                            ("custom", "Custom"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "display_name",
                    models.CharField(blank=True, max_length=255),
                ),
                (
                    "access_token",
                    models.TextField(blank=True, db_column="access_token", default=""),
                ),
                (
                    "refresh_token",
                    models.TextField(blank=True, db_column="refresh_token", default=""),
                ),
                ("api_key", models.TextField(blank=True, db_column="api_key", default="")),
                (
                    "token_type",
                    models.CharField(blank=True, default="Bearer", max_length=32),
                ),
                ("scopes_json", models.JSONField(blank=True, default=list)),
                (
                    "credentials_json",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional encrypted-at-rest credential metadata",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("expired", "Expired"),
                            ("revoked", "Revoked"),
                            ("error", "Error"),
                            ("pending", "Pending"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("connected_by", models.CharField(blank=True, max_length=256)),
                (
                    "expires_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("last_refreshed_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_platform_connection",
                "verbose_name": "Platform Connection",
                "verbose_name_plural": "Platform Connections",
                "ordering": ["-created_at"],
            },
        ),
        # -- PlatformConnection indexes & constraints -------------------------
        migrations.AddIndex(
            model_name="platformconnection",
            index=models.Index(
                fields=["tenant_id", "platform", "status"],
                name="voyager_conn_tenant_plat_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="platformconnection",
            index=models.Index(
                fields=["status", "expires_at"],
                name="voyager_conn_status_expires_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="platformconnection",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="voyager_conn_tenant_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="platformconnection",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "platform", "display_name"],
                name="voyager_integrations_conn_tenant_platform_name_uniq",
            ),
        ),
        # -- WebhookEndpoint --------------------------------------------------
        migrations.CreateModel(
            name="WebhookEndpoint",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("event_type", models.CharField(db_index=True, max_length=128)),
                ("endpoint_url", models.URLField(max_length=2048)),
                (
                    "secret",
                    models.CharField(
                        blank=True,
                        help_text="HMAC-SHA256 secret for payload signing",
                        max_length=512,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("headers_json", models.JSONField(blank=True, default=dict)),
                ("payload_schema_json", models.JSONField(blank=True, default=dict)),
                (
                    "retry_policy_json",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='e.g. {"max_retries":5,"initial_delay":1,"max_delay":3600}',
                    ),
                ),
                ("filter_json", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("paused", "Paused"),
                            ("disabled", "Disabled"),
                        ],
                        default="active",
                        max_length=16,
                    ),
                ),
                ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "connection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webhook_endpoints",
                        to="integrations.platformconnection",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_webhook_endpoint",
                "verbose_name": "Webhook Endpoint",
                "verbose_name_plural": "Webhook Endpoints",
                "ordering": ["-created_at"],
            },
        ),
        # -- WebhookEndpoint indexes ------------------------------------------
        migrations.AddIndex(
            model_name="webhookendpoint",
            index=models.Index(
                fields=["connection", "event_type", "is_active"],
                name="voyager_webhook_conn_event_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="webhookendpoint",
            index=models.Index(
                fields=["is_active", "status"],
                name="voyager_webhook_active_status_idx",
            ),
        ),
        # -- WebhookDelivery --------------------------------------------------
        migrations.CreateModel(
            name="WebhookDelivery",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("event_type", models.CharField(blank=True, max_length=128)),
                ("payload_json", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("delivered", "Delivered"),
                            ("failed", "Failed"),
                            ("retrying", "Retrying"),
                            ("dead_letter", "Dead Letter"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("response_status", models.IntegerField(blank=True, null=True)),
                ("response_body", models.TextField(blank=True)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                (
                    "next_retry_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "webhook",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="integrations.webhookendpoint",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_webhook_delivery",
                "verbose_name": "Webhook Delivery",
                "verbose_name_plural": "Webhook Deliveries",
                "ordering": ["-created_at"],
            },
        ),
        # -- WebhookDelivery indexes ------------------------------------------
        migrations.AddIndex(
            model_name="webhookdelivery",
            index=models.Index(
                fields=["webhook", "status", "created_at"],
                name="voyager_delivery_webhook_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="webhookdelivery",
            index=models.Index(
                fields=["status", "next_retry_at"],
                name="voyager_delivery_status_retry_idx",
            ),
        ),
        # -- SyncLog ----------------------------------------------------------
        migrations.CreateModel(
            name="SyncLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("sync_type", models.CharField(db_index=True, max_length=128)),
                (
                    "direction",
                    models.CharField(
                        choices=[
                            ("inbound", "Inbound"),
                            ("outbound", "Outbound"),
                            ("bidirectional", "Bidirectional"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("partial", "Partial"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("records_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("deleted_count", models.PositiveIntegerField(default=0)),
                ("conflict_count", models.PositiveIntegerField(default=0)),
                ("errors_json", models.JSONField(blank=True, default=list)),
                ("field_mappings_json", models.JSONField(blank=True, default=dict)),
                ("conflict_resolution", models.CharField(default="source_wins", max_length=16)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "connection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sync_logs",
                        to="integrations.platformconnection",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_sync_log",
                "verbose_name": "Sync Log",
                "verbose_name_plural": "Sync Logs",
                "ordering": ["-created_at"],
            },
        ),
        # -- SyncLog indexes --------------------------------------------------
        migrations.AddIndex(
            model_name="synclog",
            index=models.Index(
                fields=["connection", "sync_type", "status"],
                name="voyager_sync_conn_type_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="synclog",
            index=models.Index(
                fields=["status", "started_at"],
                name="voyager_sync_status_started_idx",
            ),
        ),
        # -- PlatformHealth ---------------------------------------------------
        migrations.CreateModel(
            name="PlatformHealth",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("last_check_at", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("healthy", "Healthy"),
                            ("degraded", "Degraded"),
                            ("down", "Down"),
                            ("unknown", "Unknown"),
                        ],
                        db_index=True,
                        default="unknown",
                        max_length=16,
                    ),
                ),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("details_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "connection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="health_checks",
                        to="integrations.platformconnection",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_platform_health",
                "verbose_name": "Platform Health",
                "verbose_name_plural": "Platform Health Checks",
                "ordering": ["-last_check_at"],
            },
        ),
        # -- PlatformHealth indexes -------------------------------------------
        migrations.AddIndex(
            model_name="platformhealth",
            index=models.Index(
                fields=["connection", "-last_check_at"],
                name="voyager_health_conn_check_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="platformhealth",
            index=models.Index(
                fields=["status", "-last_check_at"],
                name="voyager_health_status_check_idx",
            ),
        ),
    ]
