"""Backward-compat shim for generation service.

Imports from the generation subpackage to preserve existing import paths.
"""

from __future__ import annotations

from apps.content_creation.services.generation.image import generate_image
from apps.content_creation.services.generation.text import (
    _flesch_kincaid,
    _select_model,
    generate_text,
)
from apps.content_creation.services.generation.video import generate_video

__all__ = [
    "generate_text",
    "generate_image",
    "generate_video",
    "_select_model",
    "_flesch_kincaid",
]
