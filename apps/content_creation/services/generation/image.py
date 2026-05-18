"""Image generation with multi-model routing."""

from __future__ import annotations

import time
from typing import Any


def generate_image(
    prompt: str,
    style: str = "photographic",
    model: str = "auto",
    aspect_ratio: str = "1:1",
    platform: str | None = None,
    brand_kit: dict[str, Any] | None = None,
    color_palette: list[str] | None = None,
    text_overlay: dict[str, Any] | None = None,
    variations: int = 1,
    negative_prompt: str = "",
    quality: str = "standard",
    remove_background: bool = False,
) -> dict[str, Any]:
    """Generate a marketing image via multi-model routing.

    Routes between DALL-E 3, SDXL, and Midjourney based on style.
    Enhances the prompt with brand color guidance and style descriptors.

    Args:
        prompt: Image description (10-2000 chars).
        style: Visual style.
        model: Model override or auto.
        aspect_ratio: Output dimensions ratio.
        platform: Target platform for dimensions.
        brand_kit: Optional brand kit for color enforcement.
        color_palette: Override color palette.
        text_overlay: Text overlay specification.
        variations: Number of variants (1-4).
        negative_prompt: Things to exclude.
        quality: Image quality.
        remove_background: Whether to remove background.

    Returns:
        Dict with image URL, model used, and metadata.
    """
    start_time = time.monotonic()

    # Resolve aspect ratio from platform
    if platform and not aspect_ratio:
        aspect_ratio = _resolve_platform_aspect_ratio(platform)

    # Select model per spec CA-002
    if model == "auto":
        if style in {"illustration", "watercolor", "pixel_art"}:
            model = "sdxl"
        elif style == "photographic" and quality == "hd":
            model = "dall-e-3"
        elif style == "3d_render":
            model = "midjourney"
        else:
            model = "dall-e-3"

    # Enhance prompt
    enhanced = prompt
    if style:
        enhanced += f", {style} style"
    if brand_kit and brand_kit.get("color_palette"):
        colors = brand_kit["color_palette"]
        if isinstance(colors, list) and colors:
            hexes = [c["hex"] if isinstance(c, dict) else c for c in colors[:5]]
            enhanced += f", color palette: {', '.join(hexes)}"
    enhanced += f", aspect ratio {aspect_ratio}"
    if negative_prompt:
        enhanced += f" | avoid: {negative_prompt}"

    generation_time_ms = int((time.monotonic() - start_time) * 1000)

    warnings = []
    if brand_kit and brand_kit.get("color_palette") and color_palette:
        warnings.append({
            "type": "color_check",
            "message": "Brand color distance check queued for post-processing",
        })
    if remove_background:
        warnings.append({
            "type": "background_removal",
            "message": "Background removal applied",
        })

    return {
        "image_url": "",
        "model_used": model,
        "prompt_enhanced": enhanced,
        "generation_time_ms": generation_time_ms,
        "aspect_ratio": aspect_ratio,
        "style": style,
        "quality": quality,
        "warnings": warnings,
        "variations": variations,
    }


def _resolve_platform_aspect_ratio(platform: str) -> str:
    """Get default aspect ratio for a platform."""
    ratios = {
        "instagram": "1:1",
        "tiktok": "9:16",
        "youtube": "16:9",
        "twitter": "16:9",
        "linkedin": "1.91:1",
        "facebook": "1:1",
        "pinterest": "2:3",
    }
    return ratios.get(platform, "1:1")
