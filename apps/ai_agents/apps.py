"""App configuration for AI Agents."""

from django.apps import AppConfig


class AIAgentsConfig(AppConfig):
    """Configuration for the AI Agents Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_agents"
    verbose_name = "AI Agents"
