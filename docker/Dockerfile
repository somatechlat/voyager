# =============================================================================
# VOYAGER - Production Dockerfile
# =============================================================================
# Multi-stage build: builder + runtime
# Python 3.12 slim, non-root user, health check, Daphne ASGI server
# =============================================================================

# -----------------------------------------------------------------------------
# STAGE 1: Builder - compile dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specification
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir . && \
    /opt/venv/bin/pip install --no-cache-dir \
        daphne \
        channels \
        channels-redis \
        django-celery-beat \
        django-celery-results \
        uvicorn[standard]

# -----------------------------------------------------------------------------
# STAGE 2: Runtime - minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    DJANGO_SETTINGS_MODULE=voyager_project.settings \
    PATH="/opt/venv/bin:$PATH"

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user (uid 1000)
RUN groupadd -r voyager -g 1000 && \
    useradd -r -g voyager -u 1000 voyager --create-home && \
    chown -R voyager:voyager /app

# Copy application code
COPY --chown=voyager:voyager manage.py ./manage.py
COPY --chown=voyager:voyager apps/ ./apps/
COPY --chown=voyager:voyager voyager_project/ ./voyager_project/
COPY --chown=voyager:voyager vortex_bridge/ ./vortex_bridge/

# Switch to non-root user
USER voyager

# Collect static files (optional, can be overridden at runtime)
# RUN python manage.py collectstatic --noinput

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=30s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run Daphne ASGI server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "voyager_project.asgi:application"]
