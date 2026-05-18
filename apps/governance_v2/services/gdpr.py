"""GDPR compliance service.

Manages consent recording, consent withdrawal, DSR processing,
and data inventory tracking for GDPR and CCPA compliance.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.governance_v2.models import DSRRequest, GDPRConsent

logger = logging.getLogger(__name__)

# Default data inventory categories per tenant
_DEFAULT_DATA_INVENTORY: list[dict[str, Any]] = [
    {
        "category": "user_account",
        "data_types": ["email", "name", "password_hash", "avatar"],
        "purpose": "Account management",
        "legal_basis": "contract",
        "retention": "account_lifetime_plus_90_days",
        "third_party_sharing": False,
    },
    {
        "category": "social_media_data",
        "data_types": ["posts", "comments", "analytics", "followers"],
        "purpose": "Marketing services",
        "legal_basis": "contract",
        "retention": "2_years",
        "third_party_sharing": ["analytics_providers"],
    },
    {
        "category": "behavioral_data",
        "data_types": ["page_views", "click_events", "session_recordings"],
        "purpose": "Service improvement",
        "legal_basis": "legitimate_interest",
        "retention": "1_year",
        "third_party_sharing": ["analytics_providers"],
    },
    {
        "category": "billing_data",
        "data_types": ["credit_card_token", "billing_address", "invoice_history"],
        "purpose": "Payment processing",
        "legal_basis": "contract",
        "retention": "7_years",
        "third_party_sharing": ["stripe"],
    },
]


class GDPRService:
    """Service for GDPR consent and DSR management.

    Records consent, processes data subject requests (access,
    erasure, portability), and maintains a data inventory.
    """

    @staticmethod
    def record_consent(
        user_id: str,
        tenant_id: str,
        consent_type: str,
        granted: bool,
        source: str = "user_settings",
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> dict[str, Any]:
        """Record or update a user's consent for a specific purpose.

        Args:
            user_id: UUID string of the consenting user.
            tenant_id: Tenant identifier.
            consent_type: Category of consent (analytics, marketing, etc.).
            granted: Whether consent was given (True) or withdrawn (False).
            source: Origin of the consent record.
            ip_address: IP address at time of consent.
            user_agent: Browser user agent string.

        Returns:
            Dict with the recorded consent details.
        """
        consent = GDPRConsent.objects.create(
            user_id=user_id,
            tenant_id=tenant_id,
            consent_type=consent_type,
            granted=granted,
            source=source,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not granted:
            logger.info(
                "Consent withdrawn: user=%s tenant=%s type=%s",
                user_id,
                tenant_id,
                consent_type,
            )

        return {
            "id": consent.id,
            "user_id": consent.user_id,
            "tenant_id": consent.tenant_id,
            "consent_type": consent.consent_type,
            "granted": consent.granted,
            "source": consent.source,
            "ip_address": consent.ip_address,
            "user_agent": consent.user_agent,
            "created_at": consent.created_at,
        }

    @staticmethod
    def get_consent_status(
        user_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Get the current consent status for a user.

        Returns the most recent consent record for each consent type.

        Args:
            user_id: UUID string of the user.
            tenant_id: Tenant identifier.

        Returns:
            List of the latest consent record dicts per type.
        """
        consent_types = [c[0] for c in GDPRConsent.ConsentType.choices]
        results: list[dict[str, Any]] = []
        for ct in consent_types:
            latest = (
                GDPRConsent.objects.filter(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    consent_type=ct,
                )
                .order_by("-created_at")
                .first()
            )
            if latest:
                results.append(
                    {
                        "id": latest.id,
                        "user_id": latest.user_id,
                        "tenant_id": latest.tenant_id,
                        "consent_type": latest.consent_type,
                        "granted": latest.granted,
                        "source": latest.source,
                        "ip_address": latest.ip_address,
                        "user_agent": latest.user_agent,
                        "created_at": latest.created_at,
                    }
                )
        return results

    @staticmethod
    def has_consent(
        user_id: str,
        tenant_id: str,
        consent_type: str,
    ) -> bool:
        """Check whether a user has granted a specific consent.

        Args:
            user_id: UUID string of the user.
            tenant_id: Tenant identifier.
            consent_type: Category of consent to check.

        Returns:
            True if the latest consent record shows granted=True.
        """
        latest = (
            GDPRConsent.objects.filter(
                user_id=user_id,
                tenant_id=tenant_id,
                consent_type=consent_type,
            )
            .order_by("-created_at")
            .first()
        )
        if latest:
            return latest.granted
        return False

    @staticmethod
    def submit_dsr(
        tenant_id: str,
        email: str,
        request_type: str,
        user_id: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Submit a new data subject request.

        Args:
            tenant_id: Tenant identifier.
            email: Email address of the data subject.
            request_type: Type of request (access, erasure, portability).
            user_id: Optional UUID string of the data subject.
            notes: Internal notes for processing.

        Returns:
            Dict with the created DSR details.
        """
        # GDPR: 30-day deadline; CCPA: 45-day deadline
        deadline_days = 30
        deadline = datetime.now(UTC) + timedelta(days=deadline_days)

        dsr = DSRRequest.objects.create(
            tenant_id=tenant_id,
            user_id=user_id,
            email=email,
            request_type=request_type,
            status=DSRRequest.Status.RECEIVED,
            deadline=deadline,
            notes=notes,
        )

        logger.info(
            "DSR submitted: id=%s type=%s email=%s tenant=%s",
            dsr.id,
            request_type,
            email,
            tenant_id,
        )

        return {
            "id": dsr.id,
            "tenant_id": dsr.tenant_id,
            "user_id": dsr.user_id,
            "email": dsr.email,
            "request_type": dsr.request_type,
            "status": dsr.status,
            "deadline": dsr.deadline,
            "completed_at": dsr.completed_at,
            "verified_at": dsr.verified_at,
            "processed_by": dsr.processed_by,
            "notes": dsr.notes,
            "created_at": dsr.created_at,
            "updated_at": dsr.updated_at,
        }

    @staticmethod
    def process_dsr(
        dsr_id: int,
        processor_id: str,
        action: str = "complete",
        notes: str = "",
    ) -> dict[str, Any]:
        """Process a data subject request.

        Args:
            dsr_id: ID of the DSR to process.
            processor_id: User ID of the person processing the request.
            action: Processing action (complete, reject, hold, verify).
            notes: Additional processing notes.

        Returns:
            Dict with the updated DSR details.
        """
        try:
            dsr = DSRRequest.objects.get(id=dsr_id)
        except DSRRequest.DoesNotExist:
            return {"error": f"DSR with id={dsr_id} not found"}

        now = datetime.now(UTC)
        update_fields: dict[str, Any] = {
            "processed_by": processor_id,
            "updated_at": now,
        }

        if action == "complete":
            update_fields["status"] = DSRRequest.Status.COMPLETED
            update_fields["completed_at"] = now
        elif action == "reject":
            update_fields["status"] = DSRRequest.Status.REJECTED
            update_fields["completed_at"] = now
        elif action == "hold":
            update_fields["status"] = DSRRequest.Status.ON_HOLD
        elif action == "verify":
            update_fields["status"] = DSRRequest.Status.IN_PROGRESS
            update_fields["verified_at"] = now
        elif action == "progress":
            update_fields["status"] = DSRRequest.Status.IN_PROGRESS

        if notes:
            existing_notes = dsr.notes or ""
            update_fields["notes"] = f"{existing_notes}\n[{now.isoformat()}] {notes}".strip()

        for field, value in update_fields.items():
            setattr(dsr, field, value)
        dsr.save(update_fields=list(update_fields.keys()))

        logger.info(
            "DSR processed: id=%s action=%s processor=%s",
            dsr_id,
            action,
            processor_id,
        )

        return {
            "id": dsr.id,
            "tenant_id": dsr.tenant_id,
            "user_id": dsr.user_id,
            "email": dsr.email,
            "request_type": dsr.request_type,
            "status": dsr.status,
            "deadline": dsr.deadline,
            "completed_at": dsr.completed_at,
            "verified_at": dsr.verified_at,
            "processed_by": dsr.processed_by,
            "notes": dsr.notes,
            "created_at": dsr.created_at,
            "updated_at": dsr.updated_at,
        }

    @staticmethod
    def get_data_inventory(
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Return the data inventory for a tenant.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of data category dicts.
        """
        # In a full implementation, this would load per-tenant config.
        # For now, return the default inventory.
        return [{**entry, "tenant_id": tenant_id} for entry in _DEFAULT_DATA_INVENTORY]

    @staticmethod
    def get_pending_dsr_deadlines(
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Get DSRs approaching their deadline (within 48 hours).

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of DSR dicts with upcoming deadlines.
        """
        now = datetime.now(UTC)
        warning_threshold = now + timedelta(hours=48)
        dsrs = DSRRequest.objects.filter(
            tenant_id=tenant_id,
            status__in=[
                DSRRequest.Status.RECEIVED,
                DSRRequest.Status.PENDING_VERIFICATION,
                DSRRequest.Status.IN_PROGRESS,
            ],
            deadline__lte=warning_threshold,
        ).order_by("deadline")

        return [
            {
                "id": d.id,
                "email": d.email,
                "request_type": d.request_type,
                "status": d.status,
                "deadline": d.deadline,
                "hours_remaining": round(
                    (d.deadline - now).total_seconds() / 3600,
                    1,
                ),
            }
            for d in dsrs
        ]

    @staticmethod
    def get_expired_dsrs(
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Get DSRs that have exceeded their deadline.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of expired DSR dicts.
        """
        now = datetime.now(UTC)
        dsrs = DSRRequest.objects.filter(
            tenant_id=tenant_id,
            status__in=[
                DSRRequest.Status.RECEIVED,
                DSRRequest.Status.PENDING_VERIFICATION,
                DSRRequest.Status.IN_PROGRESS,
                DSRRequest.Status.ON_HOLD,
            ],
            deadline__lt=now,
        ).order_by("deadline")

        return [
            {
                "id": d.id,
                "email": d.email,
                "request_type": d.request_type,
                "status": d.status,
                "deadline": d.deadline,
                "hours_overdue": round(
                    (now - d.deadline).total_seconds() / 3600,
                    1,
                ),
            }
            for d in dsrs
        ]
