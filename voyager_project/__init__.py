"""Voyager Django project package."""

from __future__ import annotations

# This ensures the Celery app is loaded when Django starts
from .celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)
