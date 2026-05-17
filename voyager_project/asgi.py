"""ASGI config for Voyager."""

from __future__ import annotations

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyager_project.settings")

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# Import routing after Django setup to ensure apps are loaded
from apps.core import routing as core_routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(core_routing.websocket_urlpatterns)),
    }
)
