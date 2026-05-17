"""Django app configuration for the realtime WebSocket module."""

from __future__ import annotations

from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    """Configuration for the realtime app providing WebSocket consumers."""

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "apps.realtime"
    label: str = "realtime"
    verbose_name: str = "Realtime (WebSocket)"
