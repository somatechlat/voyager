"""Tests for integrations services — OAuth, webhooks, sync."""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.integrations.models import (
    PlatformConnection,
    WebhookDelivery,
    WebhookEndpoint,
)
from apps.integrations.services import oauth as oauth_service
from apps.integrations.services import sync as sync_service
from apps.integrations.services import webhooks as webhook_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-int"


@pytest.fixture
def create_connection(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "platform": PlatformConnection.Platform.FACEBOOK,
            "connection_type": PlatformConnection.ConnectionType.OAUTH2,
            "status": PlatformConnection.Status.ACTIVE,
            "scopes_json": ["read", "write"],
            "token_type": "Bearer",
        }
        defaults.update(kwargs)
        return PlatformConnection.objects.create(**defaults)

    return _create


@pytest.fixture
def create_webhook_endpoint(create_connection, db):
    def _create(**kwargs):
        connection = kwargs.pop("connection", None) or create_connection()
        defaults = {
            "connection": connection,
            "name": f"Webhook {uuid.uuid4().hex[:8]}",
            "event_type": "content.published",
            "endpoint_url": "https://example.com/webhook",
            "secret": "webhook-secret",
            "is_active": True,
            "headers_json": {"X-Custom": "value"},
            "retry_policy_json": {"max_retries": 3},
        }
        defaults.update(kwargs)
        return WebhookEndpoint.objects.create(**defaults)

    return _create


@pytest.fixture
def create_webhook_delivery(create_webhook_endpoint, db):
    def _create(**kwargs):
        endpoint = kwargs.pop("endpoint", None) or create_webhook_endpoint()
        defaults = {
            "webhook": endpoint,
            "event_type": "content.published",
            "payload_json": {"id": "123", "text": "Hello"},
            "status": WebhookDelivery.Status.PENDING,
            "attempt_count": 0,
        }
        defaults.update(kwargs)
        return WebhookDelivery.objects.create(**defaults)

    return _create


# ── OAuth Service Tests ───────────────────────────────────────────


class TestOAuthService:
    def test_initiate_oauth_flow_unsupported_platform(self, tenant_id):
        with pytest.raises(ValueError):
            oauth_service.initiate_oauth_flow(tenant_id, "nonexistent_platform")

    @patch.dict(
        "apps.integrations.services.oauth.PLATFORM_CONFIG",
        {
            "test_platform": {
                "auth_endpoint": "https://example.com/oauth",
                "token_endpoint": "https://example.com/token",
                "default_scopes": ["read"],
                "scope_separator": " ",
            }
        },
        clear=False,
    )
    @patch("apps.integrations.services.oauth._get_client_credentials")
    @patch("apps.integrations.services.oauth._get_redirect_uri")
    def test_initiate_oauth_flow_success(self, mock_redirect, mock_creds, tenant_id):
        mock_creds.return_value = ("client_id_123", "client_secret")
        mock_redirect.return_value = "https://app.com/callback"
        result = oauth_service.initiate_oauth_flow(tenant_id, "test_platform")
        assert "auth_url" in result
        assert "state" in result
        assert "test_platform" in result["auth_url"] or "example.com" in result["auth_url"]

    @patch.dict(
        "apps.integrations.services.oauth.PLATFORM_CONFIG",
        {
            "test_callback": {
                "auth_endpoint": "https://example.com/oauth",
                "token_endpoint": "https://example.com/token",
                "default_scopes": ["read"],
                "scope_separator": " ",
            }
        },
        clear=False,
    )
    @patch("apps.integrations.services.oauth._load_state")
    @patch("apps.integrations.services.oauth._get_client_credentials")
    @patch("apps.integrations.services.oauth._get_redirect_uri")
    @patch("httpx.post")
    def test_handle_oauth_callback_success(
        self, mock_post, mock_redirect, mock_creds, mock_load_state, tenant_id, db
    ):
        mock_load_state.return_value = {
            "tenant_id": tenant_id,
            "platform": "test_callback",
            "scopes": ["read"],
        }
        mock_creds.return_value = ("client_id", "secret")
        mock_redirect.return_value = "https://app.com/callback"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "read write",
        }
        mock_post.return_value = mock_response

        result = oauth_service.handle_oauth_callback("auth_code_123", "state_123")
        assert result["success"] is True
        assert "connection_id" in result
        assert PlatformConnection.objects.filter(id=result["connection_id"]).exists()

    @patch("apps.integrations.services.oauth._load_state")
    def test_handle_oauth_callback_invalid_state(self, mock_load_state):
        mock_load_state.return_value = None
        with pytest.raises(ValueError):
            oauth_service.handle_oauth_callback("code", "invalid_state")

    def test_refresh_access_token_no_refresh_token(self, create_connection):
        conn = create_connection(refresh_token="")
        conn.status = PlatformConnection.Status.ACTIVE
        conn.save()
        with pytest.raises(RuntimeError):
            oauth_service.refresh_access_token(conn)

    def test_revoke_connection(self, create_connection):
        conn = create_connection(
            access_token="test_token",
            refresh_token="test_refresh",
            status=PlatformConnection.Status.ACTIVE,
        )
        oauth_service.revoke_connection(conn)
        conn.refresh_from_db()
        assert conn.status == PlatformConnection.Status.REVOKED
        assert conn.access_token == ""
        assert conn.refresh_token == ""

    def test_get_expiring_connections(self, create_connection):
        create_connection(
            expires_at=timezone.now() + timedelta(minutes=15),
            connection_type=PlatformConnection.ConnectionType.OAUTH2,
            status=PlatformConnection.Status.ACTIVE,
        )
        create_connection(
            expires_at=timezone.now() + timedelta(hours=2),
            connection_type=PlatformConnection.ConnectionType.OAUTH2,
            status=PlatformConnection.Status.ACTIVE,
        )
        result = oauth_service.get_expiring_connections(minutes=30)
        assert len(result) == 1


# ── Webhook Service Tests ─────────────────────────────────────────


class TestWebhookService:
    def test_verify_signature_valid(self):
        payload = b'{"event": "test"}'
        import hashlib
        import hmac

        secret = "my-secret"
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        result = webhook_service.verify_signature(payload, expected, secret)
        assert result is True

    def test_verify_signature_invalid(self):
        payload = b'{"event": "test"}'
        result = webhook_service.verify_signature(payload, "invalid_sig", "my-secret")
        assert result is False

    def test_verify_signature_empty_secret(self):
        result = webhook_service.verify_signature(b"test", "sig", "")
        assert result is False

    def test_compute_signature_sha256(self):
        payload = b"test payload"
        import hashlib
        import hmac

        expected = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
        result = webhook_service.compute_signature(payload, "secret", "sha256")
        assert result == expected

    def test_compute_signature_sha1(self):
        payload = b"test payload"
        import hashlib
        import hmac

        expected = hmac.new(b"secret", payload, hashlib.sha1).hexdigest()
        result = webhook_service.compute_signature(payload, "secret", "sha1")
        assert result == expected

    def test_compute_signature_invalid_algorithm(self):
        with pytest.raises(ValueError):
            webhook_service.compute_signature(b"test", "secret", "md5")

    def test_validate_facebook_signature(self):
        payload = b"test"
        import hashlib
        import hmac

        sig = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
        result = webhook_service.validate_facebook_signature(payload, sig, "secret")
        assert result is True

    def test_validate_stripe_signature(self):
        payload = b"test"
        import hashlib
        import hmac

        v1_sig = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
        stripe_sig = f"t=1234567890,v1={v1_sig}"
        result = webhook_service.validate_stripe_signature(payload, stripe_sig, "secret")
        assert result is True

    def test_validate_github_signature(self):
        payload = b"test"
        import hashlib
        import hmac

        sig = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
        result = webhook_service.validate_github_signature(payload, sig, "secret")
        assert result is True

    def test_validate_shopify_hmac(self):
        params = {"shop": "test.myshopify.com", "timestamp": "1234567890", "hmac": ""}
        import hashlib
        import hmac

        sorted_params = "shop=test.myshopify.com&timestamp=1234567890"
        expected_hmac = hmac.new(b"api_secret", sorted_params.encode(), hashlib.sha256).hexdigest()
        params["hmac"] = expected_hmac
        result = webhook_service.validate_shopify_hmac(params.copy(), "api_secret")
        assert result is True

    def test_create_webhook_endpoint(self, create_connection):
        conn = create_connection()
        endpoint = webhook_service.create_webhook_endpoint(
            connection_id=str(conn.id),
            name="Test Endpoint",
            event_type="user.created",
            endpoint_url="https://hooks.example.com/new",
            secret="test-secret",
        )
        assert endpoint is not None
        assert endpoint.name == "Test Endpoint"
        assert WebhookEndpoint.objects.filter(id=endpoint.id).exists()

    def test_list_webhook_deliveries(self, create_webhook_delivery):
        create_webhook_delivery()
        create_webhook_delivery()
        result = webhook_service.list_webhook_deliveries()
        assert len(result) >= 2

    def test_list_webhook_deliveries_filtered(self, create_webhook_delivery):
        d = create_webhook_delivery()
        result = webhook_service.list_webhook_deliveries(webhook_id=str(d.webhook_id))
        assert all(str(item.webhook_id) == str(d.webhook_id) for item in result)

    def test_extract_event_type_facebook(self):
        event = webhook_service._extract_event_type("facebook", {}, {"object": "page"})
        assert event == "page"

    def test_extract_event_type_stripe(self):
        event = webhook_service._extract_event_type(
            "stripe", {}, {"type": "payment_intent.succeeded"}
        )
        assert event == "payment_intent.succeeded"

    def test_extract_event_type_unknown_platform(self):
        event = webhook_service._extract_event_type("unknown", {}, {"event_type": "my.event"})
        assert event == "my.event"


# ── Sync Service Tests ────────────────────────────────────────────


class TestSyncService:
    def test_conflict_resolver_source_wins(self):
        source = {"name": "Source"}
        target = {"name": "Target"}
        result = sync_service.ConflictResolver.resolve(source, target, "source_wins")
        assert result == source

    def test_conflict_resolver_target_wins(self):
        source = {"name": "Source"}
        target = {"name": "Target"}
        result = sync_service.ConflictResolver.resolve(source, target, "target_wins")
        assert result == target

    def test_conflict_resolver_last_write_wins(self):
        source = {"name": "Source"}
        target = {"name": "Target"}
        result = sync_service.ConflictResolver.resolve(
            source,
            target,
            "last_write_wins",
            source_updated="2024-01-02T00:00:00Z",
            target_updated="2024-01-01T00:00:00Z",
        )
        assert result == source

    def test_conflict_resolver_manual(self):
        source = {"name": "Source"}
        target = {"name": "Target"}
        result = sync_service.ConflictResolver.resolve(source, target, "manual")
        assert result is None

    def test_conflict_resolver_unknown_strategy(self):
        source = {"name": "Source"}
        target = {"name": "Target"}
        result = sync_service.ConflictResolver.resolve(source, target, "unknown_strategy")
        assert result == source

    def test_apply_field_mapping(self):
        record = {"first_name": "John", "last_name": "Doe"}
        mappings = [
            sync_service.FieldMapping("first_name", "fname"),
            sync_service.FieldMapping("last_name", "lname", "uppercase"),
        ]
        result = sync_service.apply_field_mapping(record, mappings)
        assert result["fname"] == "John"
        assert result["lname"] == "DOE"

    def test_compute_record_hash_stable(self):
        record = {"name": "Test", "id": 1}
        h1 = sync_service.compute_record_hash(record)
        h2 = sync_service.compute_record_hash(record)
        assert h1 == h2

    def test_compute_diff_creates(self):
        source = [{"id": "1", "name": "New"}]
        target = []
        changes = sync_service.compute_diff(source, target)
        assert len(changes) == 1
        assert changes[0].change_type == "create"

    def test_compute_diff_deletes(self):
        source = []
        target = [{"id": "1", "name": "Old"}]
        changes = sync_service.compute_diff(source, target)
        assert len(changes) == 1
        assert changes[0].change_type == "delete"

    def test_compute_diff_unchanged(self):
        data = [{"id": "1", "name": "Same"}]
        changes = sync_service.compute_diff(data, data)
        assert len(changes) == 0

    def test_compute_diff_updates(self):
        source = [{"id": "1", "name": "Updated"}]
        target = [{"id": "1", "name": "Original"}]
        changes = sync_service.compute_diff(source, target)
        assert len(changes) == 1
        assert changes[0].change_type == "update"

    def test_run_sync(self):
        config = sync_service.SyncConfig(
            connection_id="test-conn",
            sync_type="contacts",
            source_data=[{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}],
            target_data=[{"id": "2", "name": "Robert"}],
        )
        result = sync_service.run_sync(config)
        assert result.created == 1
        assert result.updated == 1
        assert result.conflicts == 0

    def test_compute_delta(self):
        previous = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
        current = [{"id": "1", "name": "Alice Updated"}, {"id": "3", "name": "Charlie"}]
        delta = sync_service.compute_delta(current, previous)
        assert delta["added_count"] == 1
        assert delta["modified_count"] == 1
        assert delta["removed_count"] == 1

    def test_sync_result_to_dict(self):
        result = sync_service.SyncResult(created=5, updated=3, deleted=2, conflicts=1)
        d = result.to_dict()
        assert d["created"] == 5
        assert d["updated"] == 3
        assert d["total_changes"] == 11
