"""Revision History endpoints.

GET  /api/v1/content/generations/{id}/revisions  — list revisions
POST /api/v1/content/generations/{id}/revisions  — create revision
GET  /api/v1/content/revisions/{id}              — get revision
POST /api/v1/content/revisions/{id}/rollback     — rollback to revision
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.content_creation.models import ContentGeneration, RevisionHistory
from apps.content_creation.serializers import CreateRevisionIn, RevisionOut
from apps.content_creation.services.revision import create_revision
from apps.core.middleware import get_tenant_id

logger = logging.getLogger(__name__)

router = Router(tags=["Revisions"])


@router.get("/generations/{generation_id}/revisions", response=list[RevisionOut])
def list_revisions(request, generation_id: UUID) -> list[RevisionHistory]:
    """List all revisions for a content generation."""
    tenant_id = get_tenant_id(request)
    # Verify the generation exists and belongs to the tenant
    get_object_or_404(ContentGeneration, id=generation_id, tenant_id=tenant_id)
    return list(
        RevisionHistory.objects.filter(content_generation_id=generation_id).order_by(
            "-version_number"
        )
    )


@router.post("/generations/{generation_id}/revisions", response=RevisionOut)
def create_revision_endpoint(
    request,
    generation_id: UUID,
    payload: CreateRevisionIn,
) -> RevisionHistory:
    """Create a new revision for a content generation.

    Computes a word-level diff against the previous version and stores
    the result along with the new body text.
    """
    tenant_id = get_tenant_id(request)
    gen = get_object_or_404(ContentGeneration, id=generation_id, tenant_id=tenant_id)

    # Get previous version
    prev_rev = (
        RevisionHistory.objects.filter(content_generation_id=generation_id)
        .order_by("-version_number")
        .first()
    )
    old_text = prev_rev.body_text if prev_rev else gen.body_text
    next_version = (prev_rev.version_number + 1) if prev_rev else 1

    result = create_revision(
        content_generation_id=str(generation_id),
        version_number=next_version,
        old_text=old_text,
        new_text=payload.body_text,
        changed_by=payload.changed_by,
        change_summary=payload.change_summary,
    )

    revision = RevisionHistory.objects.create(
        content_generation_id=generation_id,
        version_number=result["version_number"],
        diff_json=result["diff_json"],
        body_text=result["body_text"],
        changed_by=result["changed_by"],
        change_summary=result["change_summary"],
    )

    # Update the parent generation's body text
    gen.body_text = payload.body_text
    gen.save(update_fields=["body_text", "updated_at"])

    logger.info("Created revision v%s for generation=%s", result["version_number"], generation_id)
    return revision


@router.get("/revisions/{revision_id}", response=RevisionOut)
def get_revision(request, revision_id: UUID) -> RevisionHistory:
    """Retrieve a revision by ID."""
    return get_object_or_404(RevisionHistory, id=revision_id)


@router.post("/revisions/{revision_id}/rollback")
def rollback_endpoint(request, revision_id: UUID) -> dict[str, Any]:
    """Rollback a content generation to a specific revision.

    Restores the generation's body_text to the revision's body_text
    and creates a new revision entry recording the rollback.
    """
    tenant_id = get_tenant_id(request)
    revision = get_object_or_404(RevisionHistory, id=revision_id)
    gen = get_object_or_404(
        ContentGeneration,
        id=revision.content_generation_id,
        tenant_id=tenant_id,
    )

    old_text = gen.body_text
    new_text = revision.body_text

    # Create a rollback revision
    prev_rev = (
        RevisionHistory.objects.filter(content_generation_id=gen.id)
        .order_by("-version_number")
        .first()
    )
    next_version = (prev_rev.version_number + 1) if prev_rev else 1

    rollback_rev = create_revision(
        content_generation_id=str(gen.id),
        version_number=next_version,
        old_text=old_text,
        new_text=new_text,
        changed_by="system",
        change_summary=f"Rollback to v{revision.version_number}",
    )

    RevisionHistory.objects.create(
        content_generation_id=gen.id,
        version_number=rollback_rev["version_number"],
        diff_json=rollback_rev["diff_json"],
        body_text=rollback_rev["body_text"],
        changed_by=rollback_rev["changed_by"],
        change_summary=rollback_rev["change_summary"],
    )

    gen.body_text = new_text
    gen.save(update_fields=["body_text", "updated_at"])

    logger.info("Rolled back generation=%s to revision v%s", gen.id, revision.version_number)
    return {
        "rolled_back": True,
        "generation_id": str(gen.id),
        "to_version": revision.version_number,
        "new_version": next_version,
        "body_text_preview": new_text[:200],
    }
