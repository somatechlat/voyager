"""Content generation endpoints — text, image, video.

POST /api/v1/content/generate  — unified generation entrypoint
GET  /api/v1/content/generations/{id}  — retrieve a generation
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.content_creation.models import ContentGeneration
from apps.content_creation.serializers import (
    GenerateContentIn,
    GenerateImageIn,
    GenerateVideoIn,
    GenerationResponseOut,
)
from apps.content_creation.services.generation import (
    generate_image,
    generate_text,
    generate_video,
)
from apps.core.middleware import get_tenant_id, get_user_id

logger = logging.getLogger(__name__)

router = Router(tags=["Content Generation"])


@router.post("/generate", response=GenerationResponseOut)
def generate_content(request, payload: GenerateContentIn) -> dict[str, Any]:
    """Generate content (text, image, or video) via AI.

    Routes to the appropriate generation service based on the content_type
    field.  Persists the generation record and returns it with scores.
    """
    tenant_id = get_tenant_id(request)
    user_id = get_user_id() or "anonymous"
    start = time.monotonic()

    if payload.content_type == "image":
        return _handle_image_generation(payload, tenant_id, user_id, start)
    if payload.content_type == "video":
        return _handle_video_generation(payload, tenant_id, user_id, start)
    return _handle_text_generation(payload, tenant_id, user_id, start)


def _handle_text_generation(
    payload: GenerateContentIn,
    tenant_id: str,
    user_id: str,
    start: float,
) -> dict[str, Any]:
    """Handle text generation request."""
    result = generate_text(
        brief=payload.brief,
        content_type=payload.content_type,
        platforms=payload.platforms,
        brand_kit=None,
        tone=payload.tone,
        language=payload.language,
        max_length=payload.max_length,
        seo_keywords=payload.seo_keywords,
        include_cta=payload.include_cta,
        variations=payload.variations,
    )

    gen = ContentGeneration.objects.create(
        title=payload.title or f"{payload.content_type} generation",
        prompt=payload.brief,
        content_type=ContentGeneration.ContentType.TEXT,
        status=ContentGeneration.Status.PUBLISHED,
        body_text=result["text"],
        model_used=result["model_used"],
        tokens_used=result["tokens_used"],
        generation_time_ms=result["generation_time_ms"],
        brand_kit_id=payload.brand_kit_id,
        language=payload.language,
        tenant_id=tenant_id,
        created_by=user_id,
        readability_score=result["scores"].get("readability"),
        engagement_prediction=result["scores"].get("engagement_prediction"),
        seo_score=result["scores"].get("seo_score"),
    )

    return {
        "id": gen.id,
        "status": gen.status,
        "content_type": gen.content_type,
        "body_text": gen.body_text,
        "media_urls": [],
        "model_used": gen.model_used,
        "tokens_used": gen.tokens_used or 0,
        "generation_time_ms": gen.generation_time_ms or 0,
        "scores": result["scores"],
        "warnings": result["warnings"],
        "platforms": result["platforms"],
        "created_at": gen.created_at,
    }


def _handle_image_generation(
    payload: GenerateContentIn,
    tenant_id: str,
    user_id: str,
    start: float,
) -> dict[str, Any]:
    """Handle image generation request via unified payload."""
    # Convert unified payload to image params
    result = generate_image(
        prompt=payload.brief,
        style="photographic",
        model="auto",
        aspect_ratio="1:1",
        platforms=payload.platforms,
        brand_kit=None,
        variations=payload.variations,
    )

    gen = ContentGeneration.objects.create(
        title=payload.title or "Image generation",
        prompt=payload.brief,
        content_type=ContentGeneration.ContentType.IMAGE,
        status=ContentGeneration.Status.PUBLISHED,
        body_text=result.get("prompt_enhanced", ""),
        model_used=result["model_used"],
        generation_time_ms=result["generation_time_ms"],
        tenant_id=tenant_id,
        created_by=user_id,
        language=payload.language,
    )

    return {
        "id": gen.id,
        "status": gen.status,
        "content_type": gen.content_type,
        "body_text": gen.body_text,
        "media_urls": result.get("media_urls", []),
        "model_used": gen.model_used,
        "tokens_used": 0,
        "generation_time_ms": gen.generation_time_ms or 0,
        "scores": {},
        "warnings": result.get("warnings", []),
        "platforms": [],
        "created_at": gen.created_at,
    }


def _handle_video_generation(
    payload: GenerateContentIn,
    tenant_id: str,
    user_id: str,
    start: float,
) -> dict[str, Any]:
    """Handle video generation request via unified payload."""
    result = generate_video(
        script=payload.brief,
        platform=payload.platforms[0] if payload.platforms else "youtube",
    )

    gen = ContentGeneration.objects.create(
        title=payload.title or "Video generation",
        prompt=payload.brief,
        content_type=ContentGeneration.ContentType.VIDEO,
        status=ContentGeneration.Status.PUBLISHED,
        body_text=result.get("script", payload.brief),
        model_used="video-pipeline",
        generation_time_ms=result["generation_time_ms"],
        tenant_id=tenant_id,
        created_by=user_id,
        language=payload.language,
    )

    return {
        "id": gen.id,
        "status": gen.status,
        "content_type": gen.content_type,
        "body_text": gen.body_text,
        "media_urls": [],
        "model_used": gen.model_used,
        "tokens_used": 0,
        "generation_time_ms": gen.generation_time_ms or 0,
        "scores": {},
        "warnings": [],
        "platforms": result.get("scenes", []),
        "created_at": gen.created_at,
    }


@router.post("/generate/text", response=GenerationResponseOut)
def generate_text_endpoint(request, payload: GenerateContentIn) -> dict[str, Any]:
    """Generate text content with full parameter control."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id() or "anonymous"
    return _handle_text_generation(payload, tenant_id, user_id, time.monotonic())


@router.post("/generate/image", response=GenerationResponseOut)
def generate_image_endpoint(request, payload: GenerateImageIn) -> dict[str, Any]:
    """Generate image content with full parameter control."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id() or "anonymous"

    result = generate_image(
        prompt=payload.prompt,
        style=payload.style,
        model=payload.model,
        aspect_ratio=payload.aspect_ratio,
        platform=payload.platform,
        brand_kit=None,
        color_palette=payload.color_palette,
        text_overlay=payload.text_overlay,
        variations=payload.variations,
        negative_prompt=payload.negative_prompt,
        quality=payload.quality,
        remove_background=payload.remove_background,
    )

    gen = ContentGeneration.objects.create(
        title=payload.title or "Image generation",
        prompt=payload.prompt,
        content_type=ContentGeneration.ContentType.IMAGE,
        status=ContentGeneration.Status.PUBLISHED,
        body_text=result.get("prompt_enhanced", ""),
        model_used=result["model_used"],
        generation_time_ms=result["generation_time_ms"],
        tenant_id=tenant_id,
        created_by=user_id,
    )

    return {
        "id": gen.id,
        "status": gen.status,
        "content_type": gen.content_type,
        "body_text": gen.body_text,
        "media_urls": [],
        "model_used": gen.model_used,
        "tokens_used": 0,
        "generation_time_ms": gen.generation_time_ms or 0,
        "scores": {},
        "warnings": result.get("warnings", []),
        "platforms": [],
        "created_at": gen.created_at,
    }


@router.post("/generate/video", response=GenerationResponseOut)
def generate_video_endpoint(request, payload: GenerateVideoIn) -> dict[str, Any]:
    """Generate video content from a script."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id() or "anonymous"

    result = generate_video(
        script=payload.script,
        platform=payload.platform,
        voice_id=payload.voice_id,
        music_genre=payload.music_genre,
        subtitle_language=payload.subtitle_language,
        style=payload.style,
        duration=payload.duration,
    )

    gen = ContentGeneration.objects.create(
        title=payload.title or "Video generation",
        prompt=payload.script,
        content_type=ContentGeneration.ContentType.VIDEO,
        status=ContentGeneration.Status.PUBLISHED,
        body_text=payload.script,
        model_used="video-pipeline",
        generation_time_ms=result["generation_time_ms"],
        tenant_id=tenant_id,
        created_by=user_id,
    )

    return {
        "id": gen.id,
        "status": gen.status,
        "content_type": gen.content_type,
        "body_text": gen.body_text,
        "media_urls": [],
        "model_used": gen.model_used,
        "tokens_used": 0,
        "generation_time_ms": gen.generation_time_ms or 0,
        "scores": {},
        "warnings": [],
        "platforms": result.get("scenes", []),
        "created_at": gen.created_at,
    }


@router.get("/generations/{generation_id}", response=GenerationResponseOut)
def get_generation(request, generation_id: UUID) -> dict[str, Any]:
    """Retrieve a content generation by ID."""
    tenant_id = get_tenant_id(request)
    gen = get_object_or_404(
        ContentGeneration,
        id=generation_id,
        tenant_id=tenant_id,
    )
    return {
        "id": gen.id,
        "status": gen.status,
        "content_type": gen.content_type,
        "body_text": gen.body_text,
        "media_urls": gen.media_urls,
        "model_used": gen.model_used,
        "tokens_used": gen.tokens_used or 0,
        "generation_time_ms": gen.generation_time_ms or 0,
        "scores": {
            "readability": float(gen.readability_score) if gen.readability_score else 0,
            "engagement_prediction": (
                float(gen.engagement_prediction) if gen.engagement_prediction else 0
            ),
            "brand_compliance": (
                float(gen.brand_compliance_score) if gen.brand_compliance_score else 0
            ),
            "seo_score": float(gen.seo_score) if gen.seo_score else 0,
        },
        "warnings": [],
        "platforms": [],
        "created_at": gen.created_at,
    }
