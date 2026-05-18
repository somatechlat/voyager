"""License endpoints — CRUD, compliance, and alerts."""

from __future__ import annotations

import uuid

from ninja import Router

from apps.assets.models import Asset
from apps.assets.serializers import (
    AssetLicenseAlertOut,
    AssetLicenseComplianceOut,
    AssetLicenseIn,
    AssetLicenseOut,
    AssetLicenseUpdateIn,
)
from apps.assets.services.licensing import LicensingService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


@router.get("/assets/{asset_id}/licenses", response=list[AssetLicenseOut], tags=["Assets"])
def list_licenses(request, asset_id: uuid.UUID):
    """List all licenses for an asset."""
    return LicensingService.list_licenses(str(asset_id))


@router.post("/assets/{asset_id}/licenses", response=AssetLicenseOut, tags=["Assets"])
def create_license(request, asset_id: uuid.UUID, payload: AssetLicenseIn):
    """Create a license for an asset."""
    tenant_id = _get_tenant_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    return LicensingService.create_license(
        asset=asset,
        license_type=payload.license_type,
        holder=payload.holder,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        usage_rights=payload.usage_rights,
        restrictions=payload.restrictions,
        attribution_required=payload.attribution_required,
        attribution_text=payload.attribution_text,
    )


@router.get(
    "/assets/{asset_id}/licenses/compliance",
    response=AssetLicenseComplianceOut,
    tags=["Assets"],
)
def check_compliance(request, asset_id: uuid.UUID):
    """Check the compliance status of an asset's primary license."""
    licenses = LicensingService.list_licenses(str(asset_id))
    if not licenses:
        return {
            "status": "unlicensed",
            "score": 0,
            "grade": "F",
            "days_until_expiry": None,
            "warnings": [
                {"type": "unlicensed", "severity": "warning", "message": "No license configured"}
            ],
            "license": {
                "id": None,
                "type": None,
                "holder": "",
                "valid_from": None,
                "valid_until": None,
                "attribution_required": False,
            },
        }
    return LicensingService.check_compliance(licenses[0])


@router.put(
    "/assets/{asset_id}/licenses/{license_id}",
    response=AssetLicenseOut,
    tags=["Assets"],
)
def update_license(
    request,
    asset_id: uuid.UUID,
    license_id: uuid.UUID,
    payload: AssetLicenseUpdateIn,
):
    """Update a license."""
    result = LicensingService.update_license(
        license_id=str(license_id),
        license_type=payload.license_type,
        holder=payload.holder,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        usage_rights=payload.usage_rights,
        restrictions=payload.restrictions,
        attribution_required=payload.attribution_required,
        attribution_text=payload.attribution_text,
    )
    if not result:
        from ninja.errors import HttpError

        raise HttpError(404, "License not found")
    return result


@router.delete("/assets/{asset_id}/licenses/{license_id}", tags=["Assets"])
def delete_license(request, asset_id: uuid.UUID, license_id: uuid.UUID):
    """Delete a license."""
    success = LicensingService.delete_license(str(license_id))
    if not success:
        from ninja.errors import HttpError

        raise HttpError(404, "License not found")
    return {"success": True, "id": str(license_id)}


@router.get("/assets/licenses/alerts", response=AssetLicenseAlertOut, tags=["Assets"])
def license_alerts(request, within_days: int = 30):
    """Get expiring and expired license alerts for the tenant."""
    tenant_id = _get_tenant_id(request)
    expiring = LicensingService.find_expiring_licenses(tenant_id, within_days)
    expired = LicensingService.find_expired_licenses(tenant_id)
    return {
        "expiring": [
            {
                "license_id": str(lic.id),
                "asset_id": str(lic.asset_id),
                "asset_name": lic.asset.name,
                "license_type": lic.license_type,
                "holder": lic.holder,
                "valid_until": lic.valid_until.isoformat() if lic.valid_until else None,
            }
            for lic in expiring
        ],
        "expired": [
            {
                "license_id": str(lic.id),
                "asset_id": str(lic.asset_id),
                "asset_name": lic.asset.name,
                "license_type": lic.license_type,
                "holder": lic.holder,
                "valid_until": lic.valid_until.isoformat() if lic.valid_until else None,
            }
            for lic in expired
        ],
    }
