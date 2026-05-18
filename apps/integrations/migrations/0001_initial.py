# Generated initial migration for integrations

import uuid

from django.db import migrations, models


class ConnectionType(models.TextChoices):
    OAUTH2 = "oauth", "OAuth 2.0"
    API_KEY = "api_key", "API Key"
    BASIC_AUTH = "basic_auth", "Basic Auth"
    CUSTOM = "custom", "Custom"


class Platform(models.TextChoices):
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
    GOOGLE_ADS = "google_ads", "Google Ads"
    META_ADS = "meta_ads", "Meta Ads"
    LINKEDIN_ADS = "linkedin_ads", "LinkedIn Ads"
    TIKTOK_ADS = "tiktok_ads", "TikTok Ads"
    TWITTER_ADS = "twitter_ads", "Twitter Ads"
    PINTEREST_ADS = "pinterest_ads", "Pinterest Ads"
    MICROSOFT_ADS = "microsoft_ads", "Microsoft Ads"
    GOOGLE_ANALYTICS = "google_analytics", "Google Analytics"
    ADOBE_ANALYTICS = "adobe_analytics", "Adobe Analytics"
    MIXPANEL = "mixpanel", "Mixpanel"
    AMPLITUDE = "amplitude", "Amplitude"
    HOTJAR = "hotjar", "Hotjar"
    MAILCHIMP = "mailchimp", "Mailchimp"
    SENDGRID = "sendgrid", "SendGrid"
    HUBSPOT_EMAIL = "hubspot_email", "HubSpot Email"
    KLAVIYO = "klaviyo", "Klaviyo"
    ACTIVECAMPAIGN = "activecampaign", "ActiveCampaign"
    CONVERTKIT = "convertkit", "ConvertKit"
    HUBSPOT_CRM = "hubspot_crm", "HubSpot CRM"
    SALESFORCE = "salesforce", "Salesforce"
    PIPEDRIVE = "pipedrive", "Pipedrive"
    ZOHO_CRM = "zoho_crm", "Zoho CRM"
    GOOGLE_SEARCH_CONSOLE = "google_search_console", "Google Search Console"
    AHREFS = "ahrefs", "Ahrefs"
    SEMRUSH = "semrush", "SEMrush"
    MOZ = "moz", "Moz"
    FIGMA = "figma", "Figma"
    CANVA = "canva", "Canva"
    ADOBE_CREATIVE = "adobe_creative", "Adobe Creative Cloud"
    GOOGLE_DRIVE = "google_drive", "Google Drive"
    DROPBOX = "dropbox", "Dropbox"
    ONEDRIVE = "onedrive", "OneDrive"
    BOX = "box", "Box"
    SLACK = "slack", "Slack"
    MICROSOFT_TEAMS = "microsoft_teams", "Microsoft Teams"
    DISCORD = "discord", "Discord"
    ASANA = "asana", "Asana"
    MONDAY = "monday", "Monday.com"
    TRELLO = "trello", "Trello"
    JIRA = "jira", "Jira"
    NOTION = "notion", "Notion"
    SHOPIFY = "shopify", "Shopify"
    WOOCOMMERCE = "woocommerce", "WooCommerce"
    BIGCOMMERCE = "bigcommerce", "BigCommerce"
    STRIPE = "stripe", "Stripe"
    PAYPAL = "paypal", "PayPal"
    SQUARE = "square", "Square"


class Status(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"
    ERROR = "error", "Error"
    PENDING = "pending", "Pending"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PlatformConnection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                (
                    "platform",
                    models.CharField(max_length=32, choices=Platform.choices, db_index=True),
                ),
                (
                    "connection_type",
                    models.CharField(max_length=16, choices=ConnectionType.choices),
                ),
                ("display_name", models.CharField(max_length=255, blank=True)),
                (
                    "_access_token",
                    models.TextField(db_column="access_token", blank=True, default=""),
                ),
                (
                    "_refresh_token",
                    models.TextField(db_column="refresh_token", blank=True, default=""),
                ),
                ("_api_key", models.TextField(db_column="api_key", blank=True, default="")),
                ("token_type", models.CharField(max_length=32, blank=True, default="Bearer")),
                ("scopes_json", models.JSONField(default=list, blank=True)),
                (
                    "credentials_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Additional encrypted-at-rest credential metadata",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                    ),
                ),
                ("connected_by", models.CharField(max_length=256, blank=True)),
                ("expires_at", models.DateTimeField(null=True, blank=True, db_index=True)),
                ("last_refreshed_at", models.DateTimeField(null=True, blank=True)),
                ("last_error", models.TextField(blank=True)),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_platform_connection",
                "verbose_name": "Platform Connection",
                "verbose_name_plural": "Platform Connections",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "platform", "status"]),
                    models.Index(fields=["status", "expires_at"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "platform", "display_name"],
                        name="%(app_label)s_conn_tenant_platform_name_uniq",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="WebhookEndpoint",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "connection",
                    models.ForeignKey(
                        PlatformConnection,
                        on_delete=models.CASCADE,
                        related_name="webhook_endpoints",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("event_type", models.CharField(max_length=128, db_index=True)),
                ("endpoint_url", models.URLField(max_length=2048)),
                (
                    "secret",
                    models.CharField(
                        max_length=512,
                        blank=True,
                        help_text="HMAC-SHA256 secret for payload signing",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                ("headers_json", models.JSONField(default=dict, blank=True)),
                ("payload_schema_json", models.JSONField(default=dict, blank=True)),
                (
                    "retry_policy_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text='e.g. {"max_retries":5,"initial_delay":1,"max_delay":3600}',
                    ),
                ),
                ("filter_json", models.JSONField(default=dict, blank=True)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.ACTIVE,
                    ),
                ),
                ("last_triggered_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_webhook_endpoint",
                "verbose_name": "Webhook Endpoint",
                "verbose_name_plural": "Webhook Endpoints",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["connection", "event_type", "is_active"]),
                    models.Index(fields=["is_active", "status"]),
                ],
            },
        ),
    ]
