"""API Gateway with rate limiting and circuit breaker.

Multi-tier Redis-based rate limiting (tenant, endpoint, user) and
a circuit breaker state machine (closed / open / half-open) with
exponential backoff for external service calls.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

import httpx

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Redis helpers (graceful fallback to in-memory dict)
# ---------------------------------------------------------------------------


class _RateLimitStore:
    """Simple in-memory rate-limit counter store.

    In production this is backed by Redis; here we use a dict so the
    module works standalone and falls back gracefully when Redis is
    unavailable.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[int, float]] = {}  # key -> (count, expiry_ts)

    def _clean_expired(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._data.items() if now > exp]
        for k in expired:
            self._data.pop(k, None)

    def incr(self, key: str) -> int:
        """Increment a counter and return the new value."""
        self._clean_expired()
        count, expiry = self._data.get(key, (0, 0.0))
        if time.time() > expiry:
            count = 0
            expiry = time.time() + 3600
        count += 1
        self._data[key] = (count, expiry)
        return count

    def ttl(self, key: str) -> int:
        """Return remaining TTL in seconds."""
        _, expiry = self._data.get(key, (0, 0.0))
        remaining = int(expiry - time.time())
        return max(0, remaining)

    def reset(self, key: str) -> None:
        self._data.pop(key, None)


_rate_store = _RateLimitStore()

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


@dataclass
class RateLimitResult:
    """Result of a rate-limit check."""

    allowed: bool
    remaining: int = 0
    limit: int = 0
    retry_after: int = 0
    reset_at: int = 0


def check_rate_limit(
    tenant_id: str,
    user_id: str,
    endpoint: str,
    tenant_limit: int = 1000,
    endpoint_limits: dict[str, int] | None = None,
    user_limit: int = 500,
) -> RateLimitResult:
    """Check multi-tier rate limits for a request.

    Applies per-tenant, per-endpoint, and per-user limits. All windows
    are 1 hour (3600 s).

    Args:
        tenant_id: The tenant making the request.
        user_id: The user making the request.
        endpoint: The API endpoint path.
        tenant_limit: Max requests per tenant per hour.
        endpoint_limits: Map of endpoint path -> limit.
        user_limit: Max requests per user per hour.

    Returns:
        RateLimitResult indicating whether the request is allowed.
    """
    # Tier 1: per-tenant
    tenant_key = f"ratelimit:tenant:{tenant_id}"
    tenant_count = _rate_store.incr(tenant_key)
    if tenant_count > tenant_limit:
        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=tenant_limit,
            retry_after=_rate_store.ttl(tenant_key),
            reset_at=int(time.time() + _rate_store.ttl(tenant_key)),
        )

    # Tier 2: per-endpoint
    endpoint_limit_map = endpoint_limits or {}
    ep_limit = endpoint_limit_map.get(endpoint, 100)
    endpoint_key = f"ratelimit:endpoint:{endpoint}"
    endpoint_count = _rate_store.incr(endpoint_key)
    if endpoint_count > ep_limit:
        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=ep_limit,
            retry_after=_rate_store.ttl(endpoint_key),
            reset_at=int(time.time() + _rate_store.ttl(endpoint_key)),
        )

    # Tier 3: per-user
    user_key = f"ratelimit:user:{user_id}"
    user_count = _rate_store.incr(user_key)
    if user_count > user_limit:
        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=user_limit,
            retry_after=_rate_store.ttl(user_key),
            reset_at=int(time.time() + _rate_store.ttl(user_key)),
        )

    return RateLimitResult(
        allowed=True,
        remaining=tenant_limit - tenant_count,
        limit=tenant_limit,
        retry_after=0,
        reset_at=int(time.time() + _rate_store.ttl(tenant_key)),
    )


def rate_limit(
    tenant_limit: int = 1000,
    user_limit: int = 500,
) -> Callable[[F], F]:
    """Decorator that applies rate limiting to a Django-Ninja endpoint.

    Usage::

        @router.get("/items")
        @rate_limit(tenant_limit=500)
        def list_items(request):
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = args[0] if args else None
            tenant_id = getattr(request, "tenant_id", "default") if request else "default"
            user_id = getattr(request, "user_id", "anonymous") if request else "anonymous"
            endpoint = getattr(request, "path", "/")

            result = check_rate_limit(
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                endpoint=str(endpoint),
                tenant_limit=tenant_limit,
                user_limit=user_limit,
            )
            if not result.allowed:
                from django.http import JsonResponse

                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "retry_after": result.retry_after,
                    },
                    status=429,
                )
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    half_open_max_requests: int = 5


@dataclass
class CircuitBreaker:
    """Circuit breaker state machine for a single service."""

    service_id: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    half_open_successes: int = 0
    half_open_requests: int = 0
    opened_at: float = 0.0
    last_failure_at: float = 0.0

    def record_success(self) -> None:
        """Record a successful call outcome."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            self.half_open_requests += 1
            if self.half_open_successes >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.consecutive_failures = 0
                self.half_open_successes = 0
                self.half_open_requests = 0
                logger.info("Circuit breaker CLOSED for %s", self.service_id)
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed call outcome."""
        now = time.time()
        self.last_failure_at = now
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_requests += 1
            self.state = CircuitState.OPEN
            self.opened_at = now
            self.half_open_successes = 0
            logger.warning("Circuit breaker OPENED for %s (half-open failure)", self.service_id)
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = now
                logger.warning(
                    "Circuit breaker OPENED for %s (%d consecutive failures)",
                    self.service_id,
                    self.consecutive_failures,
                )

    def can_execute(self) -> bool:
        """Return True if the circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.opened_at > self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
                self.half_open_requests = 0
                logger.info("Circuit breaker HALF-OPEN for %s", self.service_id)
                return self.half_open_requests < self.config.half_open_max_requests
            return False
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_requests < self.config.half_open_max_requests
        return True

    def retry_after(self) -> int:
        """Return seconds until the circuit may allow requests again."""
        if self.state != CircuitState.OPEN:
            return 0
        remaining = int(self.config.recovery_timeout - (time.time() - self.opened_at))
        return max(0, remaining)


# In-memory circuit breaker registry
circuit_registry: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    service_id: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker for a service."""
    if service_id not in circuit_registry:
        circuit_registry[service_id] = CircuitBreaker(
            service_id=service_id,
            config=config or CircuitBreakerConfig(),
        )
    return circuit_registry[service_id]


def reset_circuit_breaker(service_id: str) -> None:
    """Manually reset a circuit breaker to CLOSED."""
    if service_id in circuit_registry:
        cb = circuit_registry[service_id]
        cb.state = CircuitState.CLOSED
        cb.consecutive_failures = 0
        cb.half_open_successes = 0
        cb.half_open_requests = 0
        cb.opened_at = 0.0
        logger.info("Circuit breaker manually reset for %s", service_id)


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open."""

    def __init__(self, service_id: str, retry_after: int) -> None:
        self.service_id = service_id
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker open for {service_id}; retry in {retry_after}s")


def call_with_circuit_breaker(
    service_id: str,
    call: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a call through a circuit breaker.

    Args:
        service_id: Identifier for the external service.
        call: Callable to execute.
        *args: Positional arguments for the call.
        **kwargs: Keyword arguments for the call.

    Returns:
        The result of the call.

    Raises:
        CircuitBreakerOpenError: If the circuit is open.
        Exception: If the call fails (after updating breaker state).
    """
    breaker = get_circuit_breaker(service_id)

    if not breaker.can_execute():
        raise CircuitBreakerOpenError(service_id, breaker.retry_after())

    try:
        result = call(*args, **kwargs)
        breaker.record_success()
        return result
    except Exception:
        breaker.record_failure()
        raise


def circuit_breaker(
    service_id: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 3,
) -> Callable[[F], F]:
    """Decorator that wraps a function with circuit breaker protection.

    Usage::

        @circuit_breaker("meta_graph_api")
        def fetch_meta_data(access_token: str) -> dict:
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return call_with_circuit_breaker(
                service_id,
                func,
                *args,
                **kwargs,
            )

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# HTTP client with circuit breaker and retry
# ---------------------------------------------------------------------------


def make_request(
    service_id: str,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    json_data: dict[str, Any] | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    backoff_base: float = 1.0,
) -> dict[str, Any]:
    """Make an HTTP request through the circuit breaker with retries.

    Args:
        service_id: Service identifier for circuit breaker tracking.
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        headers: Optional request headers.
        params: Optional query parameters.
        json_data: Optional JSON body.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.
        backoff_base: Base for exponential backoff (seconds).

    Returns:
        Dictionary with ``status_code``, ``headers``, ``body``.

    Raises:
        CircuitBreakerOpenError: If the circuit breaker is open.
        httpx.HTTPError: If all retries are exhausted.
    """
    breaker = get_circuit_breaker(service_id)
    if not breaker.can_execute():
        raise CircuitBreakerOpenError(service_id, breaker.retry_after())

    last_error: Exception | None = None
    attempt = 0

    while attempt <= max_retries:
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )
                resp.raise_for_status()
                breaker.record_success()
                return {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.json() if _is_json(resp) else resp.text,
                }
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_error = exc
            attempt += 1
            if attempt <= max_retries:
                sleep_time = backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    "Request to %s failed (attempt %d/%d), retrying in %.1fs: %s",
                    service_id,
                    attempt,
                    max_retries + 1,
                    sleep_time,
                    exc,
                )
                time.sleep(sleep_time)

    breaker.record_failure()
    raise last_error or RuntimeError(f"Request to {service_id} failed after {max_retries} retries")


def _is_json(response: httpx.Response) -> bool:
    """Check if a response has JSON content type."""
    content_type = response.headers.get("content-type", "")
    return "application/json" in content_type
