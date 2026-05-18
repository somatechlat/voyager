"""AI content generation with multi-model routing.

Re-exports the public API for text, image, and video generation.
"""

from __future__ import annotations

from .image import generate_image
from .text import (
    _flesch_kincaid,
    _select_model,
    generate_text,
)
from .video import generate_video

__all__ = [
    "generate_text",
    "generate_image",
    "generate_video",
    "_select_model",
    "_flesch_kincaid",
]
