"""
Celery configuration for Voyager.

Configures Celery with Redis as the broker and result backend,
with task routing and annotations for all Voyager modules.
"""

from __future__ import annotations

import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyager_project.settings")

# Create the Celery application
app = Celery("voyager")

# Load configuration from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# --- Task Routing ---
# Route tasks to specific queues based on module for workload isolation
app.conf.task_routes = {
    # RBAC and Audit tasks (high priority, low latency)
    "apps.rbac.tasks.*": {"queue": "security"},
    "apps.audit.tasks.*": {"queue": "security"},
    # Content creation and publishing tasks
    "apps.content_creation.tasks.*": {"queue": "content"},
    "apps.publishing.tasks.*": {"queue": "content"},
    # Campaign and strategy tasks
    "apps.campaigns.tasks.*": {"queue": "campaigns"},
    "apps.strategy.tasks.*": {"queue": "campaigns"},
    # Analytics and web scraping tasks (can be long-running)
    "apps.analytics_v2.tasks.*": {"queue": "analytics"},
    "apps.web_scraping_v2.tasks.*": {"queue": "analytics"},
    # AI agent tasks (GPU-intensive, long-running)
    "apps.ai_agents.tasks.*": {"queue": "ai"},
    # Social media and SEO tasks
    "apps.social_media.tasks.*": {"queue": "marketing"},
    "apps.seo.tasks.*": {"queue": "marketing"},
    # Email marketing tasks (high volume)
    "apps.email_marketing.tasks.*": {"queue": "email"},
    # Client and billing tasks
    "apps.clients.tasks.*": {"queue": "business"},
    "apps.billing.tasks.*": {"queue": "business"},
    # Asset processing tasks (can be resource-intensive)
    "apps.assets.tasks.*": {"queue": "assets"},
    # Team and workflow tasks
    "apps.team.tasks.*": {"queue": "operations"},
    "apps.workflows_v2.tasks.*": {"queue": "operations"},
    # Integration and governance tasks
    "apps.integrations.tasks.*": {"queue": "integrations"},
    "apps.governance_v2.tasks.*": {"queue": "integrations"},
}

# --- Task Annotations ---
# Apply default rate limits and retry policies per queue
app.conf.task_annotations = {
    "apps.rbac.tasks.*": {
        "rate_limit": "100/s",
        "max_retries": 3,
        "default_retry_delay": 5,
    },
    "apps.audit.tasks.*": {
        "rate_limit": "500/s",
        "max_retries": 2,
        "default_retry_delay": 10,
    },
    "apps.content_creation.tasks.*": {
        "rate_limit": "50/s",
        "max_retries": 3,
        "default_retry_delay": 30,
    },
    "apps.ai_agents.tasks.*": {
        "rate_limit": "10/s",
        "max_retries": 5,
        "default_retry_delay": 60,
    },
    "apps.email_marketing.tasks.*": {
        "rate_limit": "200/s",
        "max_retries": 3,
        "default_retry_delay": 30,
    },
    "apps.web_scraping_v2.tasks.*": {
        "rate_limit": "20/s",
        "max_retries": 5,
        "default_retry_delay": 60,
    },
    "apps.analytics_v2.tasks.*": {
        "rate_limit": "30/s",
        "max_retries": 3,
        "default_retry_delay": 30,
    },
}

# --- Celery Beat Schedule ---
# Periodic tasks for Voyager operations
app.conf.beat_schedule = {
    # Audit log rotation - daily at 2 AM
    "audit-log-rotation": {
        "task": "apps.audit.tasks.rotate_audit_logs",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "security"},
    },
    # Campaign status update - every 5 minutes
    "campaign-status-update": {
        "task": "apps.campaigns.tasks.update_campaign_statuses",
        "schedule": 300.0,  # 5 minutes
        "options": {"queue": "campaigns"},
    },
    # Social media queue processor - every minute
    "social-media-queue-processor": {
        "task": "apps.social_media.tasks.process_queued_posts",
        "schedule": 60.0,  # 1 minute
        "options": {"queue": "marketing"},
    },
    # Email queue processor - every 30 seconds
    "email-queue-processor": {
        "task": "apps.email_marketing.tasks.process_email_queue",
        "schedule": 30.0,  # 30 seconds
        "options": {"queue": "email"},
    },
    # SEO rank check - daily at 4 AM
    "seo-rank-check": {
        "task": "apps.seo.tasks.check_keyword_rankings",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "marketing"},
    },
    # Analytics aggregation - hourly
    "analytics-aggregation": {
        "task": "apps.analytics_v2.tasks.aggregate_metrics",
        "schedule": 3600.0,  # 1 hour
        "options": {"queue": "analytics"},
    },
    # Web scraping job runner - every 15 minutes
    "web-scraping-runner": {
        "task": "apps.web_scraping_v2.tasks.run_scheduled_scrapes",
        "schedule": 900.0,  # 15 minutes
        "options": {"queue": "analytics"},
    },
    # Billing cycle processor - daily at 1 AM
    "billing-cycle-processor": {
        "task": "apps.billing.tasks.process_billing_cycles",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "business"},
    },
    # Workflow engine heartbeat - every 30 seconds
    "workflow-heartbeat": {
        "task": "apps.workflows_v2.tasks.workflow_heartbeat",
        "schedule": 30.0,  # 30 seconds
        "options": {"queue": "operations"},
    },
    # Integration health check - every 5 minutes
    "integration-health-check": {
        "task": "apps.integrations.tasks.check_integration_health",
        "schedule": 300.0,  # 5 minutes
        "options": {"queue": "integrations"},
    },
    # Asset cleanup - daily at 3 AM
    "asset-cleanup": {
        "task": "apps.assets.tasks.cleanup_expired_assets",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "assets"},
    },
}

# Ensure beat schedule entries have their queues defined
app.conf.task_default_queue = "default"
app.conf.task_queues = {
    "default": {"exchange": "default", "routing_key": "default"},
    "security": {"exchange": "security", "routing_key": "security"},
    "content": {"exchange": "content", "routing_key": "content"},
    "campaigns": {"exchange": "campaigns", "routing_key": "campaigns"},
    "analytics": {"exchange": "analytics", "routing_key": "analytics"},
    "ai": {"exchange": "ai", "routing_key": "ai"},
    "marketing": {"exchange": "marketing", "routing_key": "marketing"},
    "email": {"exchange": "email", "routing_key": "email"},
    "business": {"exchange": "business", "routing_key": "business"},
    "assets": {"exchange": "assets", "routing_key": "assets"},
    "operations": {"exchange": "operations", "routing_key": "operations"},
    "integrations": {"exchange": "integrations", "routing_key": "integrations"},
}
