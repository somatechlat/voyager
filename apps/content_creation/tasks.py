"""Celery tasks for the Content Creation module.

Handles AI-assisted content generation, brand-voice enforcement,
and content pipeline orchestration asynchronously.  Tasks are routed
to the ``content`` queue via ``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from celery import shared_task

from apps.content_creation.models import ContentGeneration
from apps.content_creation.services.brand_enforcement import score_compliance
from apps.content_creation.services.generation import (
    generate_image,
    generate_text,
    generate_video,
)

logger = logging.getLogger(__name__)

# Maximum retries for transient failures
_MAX_RETRIES = 3
# Exponential backoff: 2^retry * base seconds
_RETRY_BACKOFF_BASE = 5


@shared_task(bind=True, max_retries=_MAX_RETRIES)
def generate_content_async(
    self,
    content_request: dict[str, Any],
    tenant_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Generate marketing content asynchronously via the AI pipeline.

    Persists a ContentGeneration record, calls the appropriate model,
    applies brand enforcement, and updates the record with results.

    :param content_request: Content specification with ``brief``,
        ``content_type``, ``tone``, ``platforms``, ``language``,
        ``seo_keywords``, ``variations``, ``brand_kit`` (optional).
    :param tenant_id: UUID of the tenant scope.
    :param user_id: UUID of the requesting user.
    :returns: Result dict with ``generation_id``, ``text``, ``scores``,
        ``warnings``, and ``status``.
    """
    start = time.monotonic()
    content_type = content_request.get("content_type", "text")
    brief = content_request.get("brief", "")

    logger.info(
        "Async generate: type=%s tenant=%s task=%s",
        content_type,
        tenant_id,
        self.request.id,
    )

    # Create the generation record
    gen = ContentGeneration.objects.create(
        title=content_request.get("title", f"{content_type} generation"),
        prompt=brief,
        content_type=content_type,
        status=ContentGeneration.Status.GENERATING,
        tenant_id=tenant_id,
        created_by=user_id,
        language=content_request.get("language", "en"),
        brand_kit_id=content_request.get("brand_kit_id"),
    )

    try:
        if content_type == "image":
            result = generate_image(
                prompt=brief,
                style=content_request.get("style", "photographic"),
                variations=content_request.get("variations", 1),
            )
            gen.body_text = result.get("prompt_enhanced", brief)
            gen.model_used = result.get("model_used", "dall-e-3")
            gen.generation_time_ms = result.get("generation_time_ms", 0)

        elif content_type == "video":
            result = generate_video(
                script=brief,
                platform=content_request.get("platforms", ["youtube"])[0],
                voice_id=content_request.get("voice_id", "default"),
            )
            gen.body_text = brief
            gen.model_used = "video-pipeline"
            gen.generation_time_ms = result.get("generation_time_ms", 0)

        else:
            result = generate_text(
                brief=brief,
                content_type=content_type,
                platforms=content_request.get("platforms", []),
                brand_kit=content_request.get("brand_kit"),
                tone=content_request.get("tone", "professional"),
                language=content_request.get("language", "en"),
                max_length=content_request.get("max_length"),
                seo_keywords=content_request.get("seo_keywords", []),
                include_cta=content_request.get("include_cta", True),
                variations=content_request.get("variations", 1),
            )
            gen.body_text = result["text"]
            gen.model_used = result["model_used"]
            gen.tokens_used = result["tokens_used"]
            gen.generation_time_ms = result["generation_time_ms"]
            gen.readability_score = result["scores"].get("readability")
            gen.engagement_prediction = result["scores"].get("engagement_prediction")
            gen.seo_score = result["scores"].get("seo_score")

            # Apply brand compliance if brand kit provided
            if content_request.get("brand_kit"):
                compliance = score_compliance(
                    text=result["text"],
                    image_url=None,
                    brand_kit=content_request["brand_kit"],
                )
                gen.brand_compliance_score = compliance.get("score")

        gen.status = ContentGeneration.Status.PUBLISHED
        gen.save()

        elapsed = int((time.monotonic() - start) * 1000)
        logger.info(
            "Async generation completed id=%s model=%s time_ms=%s",
            gen.id,
            gen.model_used,
            elapsed,
        )

        return {
            "status": "completed",
            "generation_id": str(gen.id),
            "content_type": gen.content_type,
            "model_used": gen.model_used,
            "generation_time_ms": elapsed,
        }

    except Exception as exc:
        gen.status = ContentGeneration.Status.FAILED
        gen.save()
        logger.error("Async generation failed id=%s: %s", gen.id, exc, exc_info=True)
        try:
            self.retry(
                countdown=_RETRY_BACKOFF_BASE * (2**self.request.retries),
                exc=exc,
            )
        except Exception:
            logger.warning("Generation retry exhausted for id=%s", gen.id)
        return {
            "status": "failed",
            "generation_id": str(gen.id),
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=_MAX_RETRIES)
def apply_brand_voice(
    self,
    content_id: str,
    brand_kit_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """Apply brand voice guidelines to generated content asynchronously.

    Loads the content and brand kit, runs compliance scoring, and
    updates the content record with the compliance score.

    :param content_id: UUID of the content to process.
    :param brand_kit_id: UUID of the brand kit.
    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with ``content_id``, ``brand_score``,
        ``violations``, and ``compliant``.
    """
    logger.info(
        "Applying brand voice: content=%s brand=%s tenant=%s",
        content_id,
        brand_kit_id,
        tenant_id,
    )

    try:
        gen = ContentGeneration.objects.get(id=content_id, tenant_id=tenant_id)
    except ContentGeneration.DoesNotExist:
        return {
            "status": "error",
            "content_id": content_id,
            "error": "Content generation not found",
        }

    # Local import to avoid circular deps at module level
    from apps.content_creation.models import BrandKit

    try:
        kit = BrandKit.objects.get(id=brand_kit_id, tenant_id=tenant_id)
        kit_data = {
            "voice": kit.voice,
            "forbidden_words": kit.forbidden_words,
            "required_phrases": kit.required_phrases,
            "competitor_list": kit.competitor_list,
            "tone_rules": kit.tone_rules,
            "min_readability": float(kit.min_readability),
            "min_compliance_score": kit.min_compliance_score,
        }
    except BrandKit.DoesNotExist:
        return {
            "status": "error",
            "content_id": content_id,
            "error": "Brand kit not found",
        }

    compliance = score_compliance(
        text=gen.body_text,
        image_url=None,
        brand_kit=kit_data,
    )

    gen.brand_compliance_score = compliance.get("score")
    gen.brand_kit_id = brand_kit_id
    gen.save(update_fields=["brand_compliance_score", "brand_kit_id", "updated_at"])

    return {
        "status": "completed",
        "content_id": content_id,
        "brand_score": compliance.get("score"),
        "grade": compliance.get("grade"),
        "compliant": compliance.get("compliant"),
        "violations": compliance.get("violations", []),
    }


@shared_task(bind=True, max_retries=2)
def score_content_compliance(
    self,
    content_id: str,
    brand_kit_data: dict[str, Any] | None,
    tenant_id: str,
) -> dict[str, Any]:
    """Score content compliance without persisting changes.

    Useful for previewing brand compliance before publishing.

    :param content_id: UUID of the content.
    :param brand_kit_data: Brand kit dict (avoids DB lookup).
    :param tenant_id: Tenant scope.
    :returns: Compliance result dict.
    """
    try:
        gen = ContentGeneration.objects.get(id=content_id, tenant_id=tenant_id)
    except ContentGeneration.DoesNotExist:
        return {"status": "error", "error": "Content not found"}

    compliance = score_compliance(
        text=gen.body_text,
        image_url=None,
        brand_kit=brand_kit_data,
    )
    return {
        "status": "completed",
        "content_id": content_id,
        **compliance,
    }
