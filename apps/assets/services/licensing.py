"""Licensing service for asset usage-rights tracking.

Handles license CRUD, expiration checking, compliance validation,
and alert generation for assets with time-limited usage rights.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from apps.assets.models import Asset, AssetLicense

logger = logging.getLogger(__name__)


class LicensingService:
    """Service for asset license management and compliance."""

    @staticmethod
    def list_licenses(asset_id: str) -> list[AssetLicense]:
        """List all licenses attached to an asset.

        Args:
            asset_id: UUID of the parent asset.

        Returns:
            List of license records.
        """
        return list(AssetLicense.objects.filter(asset_id=asset_id))

    @staticmethod
    def get_license(license_id: str) -> AssetLicense | None:
        """Fetch a single license by ID.

        Args:
            license_id: UUID of the license.

        Returns:
            The license or ``None``.
        """
        try:
            return AssetLicense.objects.get(id=license_id)
        except AssetLicense.DoesNotExist:
            return None

    @staticmethod
    def create_license(
        asset: Asset,
        license_type: str,
        holder: str = "",
        valid_from: date | None = None,
        valid_until: date | None = None,
        usage_rights: dict[str, Any] | None = None,
        restrictions: dict[str, Any] | None = None,
        attribution_required: bool = False,
        attribution_text: str = "",
    ) -> AssetLicense:
        """Create a new license for an asset.

        Args:
            asset: The asset being licensed.
            license_type: One of AssetLicense.LicenseType values.
            holder: Name of the license holder.
            valid_from: Start date of validity.
            valid_until: End date of validity (None = perpetual).
            usage_rights: JSON dict of permitted uses.
            restrictions: JSON dict of usage restrictions.
            attribution_required: Whether attribution is mandatory.
            attribution_text: Required attribution string.

        Returns:
            The newly created license.
        """
        license_obj = AssetLicense.objects.create(
            asset=asset,
            license_type=license_type,
            holder=holder,
            valid_from=valid_from,
            valid_until=valid_until,
            usage_rights=usage_rights or {},
            restrictions=restrictions or {},
            attribution_required=attribution_required,
            attribution_text=attribution_text,
        )
        return license_obj

    @staticmethod
    def update_license(
        license_id: str,
        license_type: str | None = None,
        holder: str | None = None,
        valid_from: date | None = None,
        valid_until: date | None = None,
        usage_rights: dict[str, Any] | None = None,
        restrictions: dict[str, Any] | None = None,
        attribution_required: bool | None = None,
        attribution_text: str | None = None,
    ) -> AssetLicense | None:
        """Update fields on an existing license.

        Args:
            license_id: UUID of the license.
            license_type: New license type.
            holder: New holder name.
            valid_from: New start date.
            valid_until: New end date.
            usage_rights: New usage rights dict.
            restrictions: New restrictions dict.
            attribution_required: New attribution flag.
            attribution_text: New attribution text.

        Returns:
            The updated license or ``None``.
        """
        lic = LicensingService.get_license(license_id)
        if not lic:
            return None
        if license_type is not None:
            lic.license_type = license_type
        if holder is not None:
            lic.holder = holder
        if valid_from is not None:
            lic.valid_from = valid_from
        if valid_until is not None:
            lic.valid_until = valid_until
        if usage_rights is not None:
            lic.usage_rights = usage_rights
        if restrictions is not None:
            lic.restrictions = restrictions
        if attribution_required is not None:
            lic.attribution_required = attribution_required
        if attribution_text is not None:
            lic.attribution_text = attribution_text
        lic.save()
        return lic

    @staticmethod
    def delete_license(license_id: str) -> bool:
        """Delete a license.

        Args:
            license_id: UUID of the license.

        Returns:
            ``True`` if deleted, ``False`` if not found.
        """
        lic = LicensingService.get_license(license_id)
        if not lic:
            return False
        lic.delete()
        return True

    @staticmethod
    def check_compliance(license: AssetLicense) -> dict[str, Any]:
        """Evaluate a license's current compliance status.

        Checks expiration date and produces warnings if the license
        has expired or is expiring soon.

        Args:
            license: The license to evaluate.

        Returns:
            Dict with ``status``, ``grade``, ``warnings``,
            ``days_until_expiry``, and ``license`` summary.
        """
        warnings: list[dict[str, Any]] = []
        today = date.today()
        days_until_expiry = None

        if license.valid_until:
            delta = (license.valid_until - today).days
            days_until_expiry = delta
            if delta < 0:
                warnings.append(
                    {
                        "type": "expired",
                        "severity": "critical",
                        "message": f"License expired {abs(delta)} days ago",
                    }
                )
            elif delta < 30:
                warnings.append(
                    {
                        "type": "expiring_soon",
                        "severity": "warning",
                        "message": f"License expires in {delta} days",
                    }
                )

        score = 100 - len([w for w in warnings if w["severity"] == "critical"]) * 50
        score -= len([w for w in warnings if w["severity"] == "warning"]) * 10
        score = max(0, score)

        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        else:
            grade = "F"

        status = "violation" if any(w["severity"] == "critical" for w in warnings) else "compliant"

        return {
            "status": status,
            "score": score,
            "grade": grade,
            "days_until_expiry": days_until_expiry,
            "warnings": warnings,
            "license": {
                "id": str(license.id),
                "type": license.license_type,
                "holder": license.holder,
                "valid_from": license.valid_from.isoformat() if license.valid_from else None,
                "valid_until": license.valid_until.isoformat() if license.valid_until else None,
                "attribution_required": license.attribution_required,
            },
        }

    @staticmethod
    def check_asset_compliance(asset: Asset) -> dict[str, Any]:
        """Evaluate all licenses on an asset and aggregate compliance.

        Args:
            asset: The asset to check.

        Returns:
            Aggregated compliance report with overall status.
        """
        licenses = LicensingService.list_licenses(str(asset.id))
        if not licenses:
            return {
                "status": "unlicensed",
                "message": "No usage rights configured",
                "licenses": [],
            }

        results = [LicensingService.check_compliance(lic) for lic in licenses]
        critical = any(r["status"] == "violation" for r in results)
        status = "violation" if critical else "compliant"

        return {
            "status": status,
            "asset_id": str(asset.id),
            "asset_name": asset.name,
            "licenses": results,
        }

    @staticmethod
    def find_expiring_licenses(
        tenant_id: str,
        within_days: int = 30,
    ) -> list[AssetLicense]:
        """Find licenses expiring within a given window.

        Args:
            tenant_id: Tenant scope identifier.
            within_days: Number of days to look ahead.

        Returns:
            List of licenses with expiry within the window.
        """
        cutoff = date.today() + timedelta(days=within_days)
        return list(
            AssetLicense.objects.filter(
                asset__tenant_id=tenant_id,
                valid_until__lte=cutoff,
                valid_until__gte=date.today(),
            ).select_related("asset")
        )

    @staticmethod
    def find_expired_licenses(tenant_id: str) -> list[AssetLicense]:
        """Find licenses that have already expired.

        Args:
            tenant_id: Tenant scope identifier.

        Returns:
            List of expired licenses.
        """
        return list(
            AssetLicense.objects.filter(
                asset__tenant_id=tenant_id,
                valid_until__lt=date.today(),
            ).select_related("asset")
        )
