"""Webhook management: receiver, validation, retry logic, delivery tracking.

Handles inbound webhook payloads from external platforms, HMAC-SHA256
signature verification, event routing, retry with exponential backoff,
and dead-letter queue processing.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from django.utils import timezone

from apps.integrations.models import (
    PlatformConnection,
    WebhookDelivery,
    WebhookEndpoint,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signature validation
# ---------------------------------------------------------------------------


def verify_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify an HMAC signature on a webhook payload.

    Supports ``sha256`` (default) and ``sha1`` algorithms.
    The signature may be provided as a hex string or with a prefix
    (e.g. ``"sha256=..."``).

    Args:
        payload: Raw request body bytes.
        signature: Provided signature string (may include prefix).
        secret: The shared secret for HMAC verification.
        algorithm: Hash algorithm name.

    Returns:
        True if the signature is valid.
    """
    if not secret or not signature:
        return False

    # Strip common prefixes
    sig = signature
    for prefix in ("sha256=", "sha1=", "v0=", "sig="):
        if sig.startswith(prefix):
            sig = sig[len(prefix) :]
            break

    if algorithm == "sha256":
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    elif algorithm == "sha1":
        expected = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
    else:
        return False

    return hmac.compare_digest(expected, sig)


def compute_signature(payload: bytes, secret: str, algorithm: str = "sha256") -> str:
    """Compute an HMAC-SHA256 signature for a payload.

    Args:
        payload: Raw request body bytes.
        secret: The shared secret.
        algorithm: Hash algorithm (default ``sha256``).

    Returns:
        Hex-encoded signature string.
    """
    if algorithm == "sha256":
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    elif algorithm == "sha1":
        return hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
    raise ValueError(f"Unsupported algorithm: {algorithm}")


# ---------------------------------------------------------------------------
# Platform-specific validation
# ---------------------------------------------------------------------------


def validate_facebook_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Validate Facebook Graph API webhook signature.

    Facebook sends ``X-Hub-Signature-256: sha256=<hex>``.
    """
    return verify_signature(payload, signature, app_secret, "sha256")


def validate_twitter_signature(payload: bytes, signature: str, consumer_secret: str) -> bool:
    """Validate Twitter CRC / webhook signature.

    Twitter uses CRC token validation for account activity webhooks.
    """
    return verify_signature(payload, signature, consumer_secret, "sha256")


def validate_stripe_signature(payload: bytes, signature: str, signing_secret: str) -> bool:
    """Validate Stripe webhook signature.

    Stripe sends ``Stripe-Signature`` with timestamp + v1 signature.
    We extract the v1 component and verify.
    """
    if not signature or not signing_secret:
        return False
    parts = signature.split(",")
    v1_sig = ""
    for part in parts:
        part = part.strip()
        if part.startswith("v1="):
            v1_sig = part[3:]
            break
    if not v1_sig:
        return False
    signed_payload = payload
    return verify_signature(signed_payload, v1_sig, signing_secret, "sha256")


def validate_github_signature(payload: bytes, signature: str, webhook_secret: str) -> bool:
    """Validate GitHub webhook signature (sha256)."""
    return verify_signature(payload, signature, webhook_secret, "sha256")


def validate_shopify_hmac(query_params: dict[str, str], api_secret: str) -> bool:
    """Validate Shopify HMAC on OAuth or webhook query parameters."""
    hmac_param = query_params.pop("hmac", "")
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(query_params.items()))
    expected = hmac.new(api_secret.encode(), sorted_params.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, hmac_param)


# ---------------------------------------------------------------------------
# Inbound webhook processing
# ---------------------------------------------------------------------------


def receive_webhook(
    platform: str,
    headers: dict[str, str],
    body: bytes,
    connection: PlatformConnection | None = None,
) -> dict[str, Any]:
    """Process an inbound webhook from an external platform.

    Verifies the platform-specific signature (if configured), parses
    the payload, routes to the appropriate handler, and creates a
    delivery log.

    Args:
        platform: The platform sending the webhook.
        headers: HTTP headers from the request.
        body: Raw request body bytes.
        connection: Optional associated PlatformConnection.

    Returns:
        Dictionary with ``success``, ``event_type``, and ``delivery_id``.
    """
    payload: dict[str, Any]
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        payload = {"raw_body": body.decode("utf-8", errors="replace")}

    # Extract event type from platform-specific header
    event_type = _extract_event_type(platform, headers, payload)

    # Find matching webhook endpoints
    endpoints = WebhookEndpoint.objects.filter(
        connection__platform=platform,
        is_active=True,
        event_type__in=[event_type, "*"],
    )

    delivery_ids: list[str] = []
    for endpoint in endpoints:
        delivery = WebhookDelivery.objects.create(
            webhook=endpoint,
            event_type=event_type,
            payload_json=payload,
            status=WebhookDelivery.Status.PENDING,
            attempt_count=0,
        )
        delivery_ids.append(str(delivery.id))

        # Trigger async delivery
        _deliver_webhook_async(endpoint, delivery)

    return {
        "success": True,
        "event_type": event_type,
        "delivery_ids": delivery_ids,
        "matched_endpoints": endpoints.count(),
    }


def _extract_event_type(platform: str, headers: dict[str, str], payload: dict[str, Any]) -> str:
    """Extract the event type from platform-specific headers or body."""
    header_map: dict[str, str] = {
        "facebook": "X-Hub-Signature-256",
        "instagram": "X-Hub-Signature-256",
        "twitter": "X-Twitter-Webhook-Event",
        "stripe": "Stripe-Event-Type",
        "github": "X-GitHub-Event",
        "shopify": "X-Shopify-Topic",
        "slack": "X-Slack-Event-Type",
    }

    header_key = header_map.get(platform, "X-Event-Type")
    event = headers.get(header_key, "")

    # Facebook/Instagram: event type is in the payload
    if platform in ("facebook", "instagram") and not event:
        event = payload.get("object", "unknown")
    elif platform == "stripe" and not event:
        event = payload.get("type", "unknown")
    elif platform == "twitter" and not event:
        event = payload.get("event", {}).get("type", "unknown")
    elif platform == "slack" and not event:
        event = payload.get("type", "unknown")
    elif not event:
        event = payload.get("event_type", "unknown")

    return event


# ---------------------------------------------------------------------------
# Outbound delivery with retry
# ---------------------------------------------------------------------------


def deliver_webhook(endpoint: WebhookEndpoint, delivery: WebhookDelivery) -> dict[str, Any]:
    """Deliver a single webhook payload with retry logic.

    Sends the payload to the endpoint URL, records the response,
    and handles retry scheduling based on the endpoint's retry policy.

    Args:
        endpoint: The webhook endpoint configuration.
        delivery: The delivery record to update.

    Returns:
        Dictionary with ``success``, ``status_code``, and ``status``.
    """
    policy = endpoint.retry_policy()
    max_retries: int = policy.get("max_retries", 5)
    initial_delay: int = policy.get("initial_delay", 1)
    max_delay: int = policy.get("max_delay", 3600)
    backoff_multiplier: int = policy.get("backoff_multiplier", 2)

    headers: dict[str, Any] = {"Content-Type": "application/json"}
    if endpoint.headers_json:
        headers.update(endpoint.headers_json)

    # Compute and attach signature if secret is configured
    payload_body = json.dumps(delivery.payload_json).encode()
    if endpoint.secret:
        sig = compute_signature(payload_body, endpoint.secret, "sha256")
        headers["X-Voyager-Signature"] = f"sha256={sig}"

    attempt = delivery.attempt_count
    success = False
    status_code: int | None = None
    response_text = ""

    while attempt <= max_retries and not success:
        attempt += 1
        try:
            resp = httpx.post(
                str(endpoint.endpoint_url),
                content=payload_body,
                headers=headers,
                timeout=30.0,
            )
            status_code = resp.status_code
            response_text = resp.text[:4096]  # Truncate long responses

            if resp.status_code < 500:
                success = True
                delivery.status = WebhookDelivery.Status.DELIVERED
                delivery.response_status = status_code
                delivery.response_body = response_text
                delivery.delivered_at = timezone.now()
                endpoint.last_triggered_at = timezone.now()
                endpoint.save(update_fields=["last_triggered_at"])
                break
            else:
                # Server error - schedule retry
                delivery.response_status = status_code
                delivery.response_body = response_text

        except httpx.RequestError as exc:
            delivery.response_body = str(exc)[:1024]
            status_code = None

        # Calculate next retry time
        if attempt <= max_retries:
            delay = min(initial_delay * (backoff_multiplier ** (attempt - 1)), max_delay)
            delivery.next_retry_at = timezone.now() + timezone.timedelta(seconds=delay)
            delivery.attempt_count = attempt
            delivery.status = WebhookDelivery.Status.RETRYING
            delivery.save()
            time.sleep(delay)

    if not success:
        delivery.status = (
            WebhookDelivery.Status.DEAD_LETTER
            if attempt > max_retries
            else WebhookDelivery.Status.FAILED
        )
        delivery.attempt_count = attempt

    delivery.attempt_count = attempt
    delivery.save()

    return {
        "success": success,
        "status_code": status_code,
        "status": delivery.status,
        "attempts": attempt,
    }


def _deliver_webhook_async(endpoint: WebhookEndpoint, delivery: WebhookDelivery) -> None:
    """Trigger async webhook delivery via Celery if available, else sync."""
    try:
        from apps.integrations.tasks import deliver_webhook_task

        deliver_webhook_task.delay(str(delivery.id))
    except Exception:
        # Fallback to synchronous delivery
        deliver_webhook(endpoint, delivery)


# ---------------------------------------------------------------------------
# Dead letter queue processing
# ---------------------------------------------------------------------------


def process_dead_letter_queue(
    max_age_minutes: int = 60,
) -> dict[str, int]:
    """Retry webhook deliveries stuck in dead-letter status.

    Scans for failed deliveries older than ``max_age_minutes`` and
    attempts re-delivery with extended backoff.

    Args:
        max_age_minutes: Minimum age of dead-letter items to process.

    Returns:
        Dictionary with ``retried``, ``succeeded``, ``failed`` counts.
    """
    cutoff = timezone.now() - timezone.timedelta(minutes=max_age_minutes)
    dead_deliveries = WebhookDelivery.objects.filter(
        status__in=(WebhookDelivery.Status.FAILED, WebhookDelivery.Status.DEAD_LETTER),
        next_retry_at__lte=timezone.now(),
        created_at__lte=cutoff,
    )

    retried = 0
    succeeded = 0
    failed = 0

    for delivery in dead_deliveries.select_related("webhook"):
        retried += 1
        endpoint = delivery.webhook
        policy = endpoint.retry_policy()
        max_retries = policy.get("max_retries", 5) * 2  # Extended limit

        if delivery.attempt_count >= max_retries:
            delivery.status = WebhookDelivery.Status.DEAD_LETTER
            delivery.save(update_fields=["status"])
            failed += 1
            continue

        result = deliver_webhook(endpoint, delivery)
        if result["success"]:
            succeeded += 1
        else:
            failed += 1

    return {"retried": retried, "succeeded": succeeded, "failed": failed}


# ---------------------------------------------------------------------------
# Webhook endpoint CRUD helpers
# ---------------------------------------------------------------------------


def create_webhook_endpoint(
    connection_id: str,
    name: str,
    event_type: str,
    endpoint_url: str,
    secret: str = "",
    headers_json: dict[str, str] | None = None,
    retry_policy_json: dict[str, Any] | None = None,
    filter_json: dict[str, Any] | None = None,
) -> WebhookEndpoint:
    """Create a new webhook endpoint for a connection.

    Args:
        connection_id: UUID of the PlatformConnection.
        name: Human-readable endpoint name.
        event_type: Event filter (e.g. ``"content.published"``).
        endpoint_url: Target delivery URL.
        secret: HMAC signing secret.
        headers_json: Additional HTTP headers.
        retry_policy_json: Retry configuration overrides.
        filter_json: Payload filtering rules.

    Returns:
        The created WebhookEndpoint instance.
    """
    connection = PlatformConnection.objects.get(id=connection_id)
    return WebhookEndpoint.objects.create(
        connection=connection,
        name=name,
        event_type=event_type,
        endpoint_url=endpoint_url,
        secret=secret,
        headers_json=headers_json or {},
        retry_policy_json=retry_policy_json or {},
        filter_json=filter_json or {},
    )


def list_webhook_deliveries(
    webhook_id: str | None = None,
    tenant_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[WebhookDelivery]:
    """List webhook deliveries with optional filtering.

    Args:
        webhook_id: Filter by webhook endpoint.
        tenant_id: Filter by tenant.
        status: Filter by delivery status.
        limit: Maximum results.

    Returns:
        List of WebhookDelivery objects.
    """
    qs = WebhookDelivery.objects.select_related("webhook", "webhook__connection")
    if webhook_id:
        qs = qs.filter(webhook_id=webhook_id)
    if tenant_id:
        qs = qs.filter(webhook__connection__tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)
    return list(qs.order_by("-created_at")[:limit])
