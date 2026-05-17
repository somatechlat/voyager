"""WebSocket URL routing for the realtime app.

Maps WebSocket URL patterns to their respective consumer classes.
All routes are relative to the WebSocket root and are composed
into the main ASGI application via ProtocolTypeRouter.
"""

from __future__ import annotations

from django.urls import re_path

from . import consumers

# Type alias matching channels.routing.URLRouter expectations.
websocket_urlpatterns: list = [
    # Notifications stream — real-time user notifications
    re_path(
        r"ws/notifications/$",
        consumers.NotificationConsumer.as_asgi(),
    ),
    # Task progress stream — Celery task progress updates
    re_path(
        r"ws/progress/$",
        consumers.TaskProgressConsumer.as_asgi(),
    ),
    # Social feed stream — real-time social media feed
    re_path(
        r"ws/social/$",
        consumers.SocialFeedConsumer.as_asgi(),
    ),
]
