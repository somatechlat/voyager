"""VoyagerKeycloakBearer — Django Ninja HttpBearer integration."""

from __future__ import annotations

from ninja.security import HttpBearer

from .user import VoyagerUser


class VoyagerKeycloakBearer(HttpBearer):
    """Django Ninja ``HttpBearer`` using Keycloak JWT validation for Voyager.

    Usage:
        ```python
        from ninja import Router
        from apps.rbac.auth import VoyagerKeycloakBearer

        router = Router(auth=VoyagerKeycloakBearer())

        @router.get("/campaigns")
        def list_campaigns(request):
            user = request.auth  # VoyagerUser instance
            ...
        ```
    """

    def authenticate(self, request, token: str) -> VoyagerUser | None:
        """Authenticate an incoming request by validating the Bearer token.

        Args:
            request: Django HTTP request object.
            token: JWT token extracted from the ``Authorization`` header.

        Returns:
            A ``VoyagerUser`` if the token is valid, otherwise ``None``.

        Raises:
            HttpError: 401 if the token is invalid or expired.
        """
        from .dependencies import get_auth

        return get_auth().validate_token(token)
