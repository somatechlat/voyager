"""Video generation from scripts with platform optimization."""

from __future__ import annotations

import time
from typing import Any


def generate_video(
    script: str,
    platform: str,
    voice_id: str = "default",
    music_genre: str = "corporate",
    subtitle_language: str = "en",
    style: str = "modern",
    duration: str = "auto",
    brand_kit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a marketing video from a script.

    Parses the script into scenes, determines dimensions per platform,
    and returns a video generation plan.

    Args:
        script: Video script (50-10000 chars).
        platform: Target platform.
        voice_id: ElevenLabs voice ID.
        music_genre: Background music genre.
        subtitle_language: Subtitle language code.
        style: Visual style.
        duration: Target duration.
        brand_kit: Optional brand kit.

    Returns:
        Dict with video metadata, scenes, and generation plan.
    """
    start_time = time.monotonic()

    # Parse script into scenes
    scenes = _parse_script_into_scenes(script)

    # Platform dimensions
    dimensions = _resolve_video_dimensions(platform)

    generation_time_ms = int((time.monotonic() - start_time) * 1000)

    return {
        "video_url": "",
        "platform": platform,
        "dimensions": dimensions,
        "scenes": scenes,
        "voice_id": voice_id,
        "music_genre": music_genre,
        "subtitle_language": subtitle_language,
        "style": style,
        "duration": duration,
        "scene_count": len(scenes),
        "generation_time_ms": generation_time_ms,
        "brand_applied": bool(brand_kit),
    }


def _resolve_video_dimensions(platform: str) -> dict[str, int]:
    """Get video dimensions for a platform."""
    dims = {
        "tiktok": {"width": 1080, "height": 1920},
        "instagram_reels": {"width": 1080, "height": 1920},
        "youtube": {"width": 1920, "height": 1080},
        "linkedin": {"width": 1080, "height": 1080},
        "facebook": {"width": 1080, "height": 1080},
    }
    return dims.get(platform, {"width": 1920, "height": 1080})


def _parse_script_into_scenes(script: str) -> list[dict[str, Any]]:
    """Split a script into scenes based on paragraph breaks.

    Estimates duration per scene using word count at 150 WPM.

    Args:
        script: Video script text.

    Returns:
        List of scene dicts with text and estimated duration.
    """
    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    scenes = []
    for i, para in enumerate(paragraphs, start=1):
        words = len(para.split())
        duration_sec = max(3, int(words / 2.5))  # ~150 WPM
        scenes.append(
            {
                "scene_number": i,
                "text": para[:300],
                "word_count": words,
                "estimated_duration_sec": duration_sec,
            }
        )
    return scenes
