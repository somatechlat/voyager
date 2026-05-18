"""Expense tracking service.

Handles receipt OCR, expense categorization, approval workflow,
and billable markup calculation.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from apps.billing.models.expense import Expense

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "travel": ["airline", "hotel", "flight", "taxi", "uber", "rental car", "parking"],
    "meals": ["restaurant", "cafe", "coffee", "lunch", "dinner", "catering"],
    "software": ["saas", "subscription", "license", "software", "app"],
    "advertising": ["ad", "ads", "facebook", "google ads", "linkedin", "promotion"],
    "supplies": ["office", "stationery", "printer", "supplies"],
    "professional_services": ["legal", "accounting", "consulting", "lawyer"],
}


def parse_amount(text: str) -> Decimal | None:
    """Extract amount from OCR text.

    Args:
        text: Raw OCR text from receipt.

    Returns:
        Extracted amount or None.
    """
    pattern = r"(?:total|amount|sum)\s*[:$]?\s*([0-9,]+\.\d{2})"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return Decimal(match.group(1).replace(",", ""))
    # Fallback: find largest dollar amount in text
    amounts = re.findall(r"\$?([0-9,]+\.\d{2})", text)
    if amounts:
        return Decimal(max(amounts, key=lambda x: Decimal(x.replace(",", ""))).replace(",", ""))
    return None


def parse_date(text: str) -> str | None:
    """Extract date from OCR text.

    Args:
        text: Raw OCR text from receipt.

    Returns:
        ISO date string or None.
    """
    patterns = [
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            return match.group(1)
    return None


def parse_vendor(text: str) -> str:
    """Extract vendor name from OCR text.

    Args:
        text: Raw OCR text from receipt.

    Returns:
        Vendor name or empty string.
    """
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return lines[0] if lines else ""


def parse_currency(text: str) -> str:
    """Detect currency from OCR text.

    Args:
        text: Raw OCR text from receipt.

    Returns:
        ISO 4217 currency code (default USD).
    """
    if "EUR" in text or "€" in text:
        return "EUR"
    if "GBP" in text or "£" in text:
        return "GBP"
    if "CAD" in text or "C$" in text:
        return "CAD"
    return "USD"


def categorize_expense(vendor: str, description: str) -> str:
    """Auto-categorize expense from vendor and description.

    Args:
        vendor: Vendor name.
        description: Expense description.

    Returns:
        Category string matching Expense.Category choices.
    """
    combined = f"{vendor} {description}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return category
    return "other"


def process_receipt_ocr(ocr_text: str) -> dict[str, Any]:
    """Process OCR text from a receipt into structured data.

    Args:
        ocr_text: Raw OCR text extracted from receipt image.

    Returns:
        Dict with extracted vendor, date, total, currency, category,
        and confidence score.
    """
    vendor = parse_vendor(ocr_text)
    extracted_date = parse_date(ocr_text)
    total = parse_amount(ocr_text)
    currency = parse_currency(ocr_text)
    category = categorize_expense(vendor, ocr_text)
    confidence = Decimal("0.75") if total else Decimal("0.4")
    return {
        "vendor": vendor,
        "date": extracted_date,
        "total": str(total) if total else None,
        "currency": currency,
        "category": category,
        "confidence": str(confidence),
    }


def apply_ocr_to_expense(expense: Expense, ocr_result: dict[str, Any]) -> None:
    """Apply OCR results to an expense record.

    Args:
        expense: The expense to update.
        ocr_result: OCR extraction result dict.
    """
    expense.receipt_ocr_data = ocr_result
    expense.ocr_confidence = Decimal(str(ocr_result.get("confidence", "0")))
    if ocr_result.get("vendor") and not expense.vendor:
        expense.vendor = ocr_result["vendor"]
    if ocr_result.get("category"):
        expense.category = ocr_result["category"]
    if ocr_result.get("total") and not expense.amount:
        expense.amount = Decimal(ocr_result["total"])
    if ocr_result.get("currency"):
        expense.currency = ocr_result["currency"]
    expense.save(
        update_fields=[
            "receipt_ocr_data",
            "ocr_confidence",
            "vendor",
            "category",
            "amount",
            "currency",
            "updated_at",
        ]
    )


def approve_expense(expense: Expense, approver_id: str, notes: str = "") -> dict[str, Any]:
    """Approve an expense.

    Args:
        expense: The expense to approve.
        approver_id: User ID of approver.
        notes: Optional approval notes.

    Returns:
        Dict with approval result.
    """
    expense.status = Expense.Status.APPROVED
    expense.approver_id = approver_id
    expense.approved_at = datetime.now()
    expense.metadata["approval_notes"] = notes
    expense.save(
        update_fields=[
            "status",
            "approver_id",
            "approved_at",
            "metadata",
            "updated_at",
        ]
    )
    return {
        "expense_id": expense.pk,
        "status": expense.status,
        "approved_by": approver_id,
        "approved_at": expense.approved_at.isoformat() if expense.approved_at else None,
    }


def reject_expense(expense: Expense, approver_id: str, reason: str) -> dict[str, Any]:
    """Reject an expense.

    Args:
        expense: The expense to reject.
        approver_id: User ID of rejector.
        reason: Rejection reason.

    Returns:
        Dict with rejection result.
    """
    expense.status = Expense.Status.REJECTED
    expense.approver_id = approver_id
    expense.rejection_reason = reason
    expense.save(update_fields=["status", "approver_id", "rejection_reason", "updated_at"])
    return {
        "expense_id": expense.pk,
        "status": expense.status,
        "rejected_by": approver_id,
        "reason": reason,
    }


def calculate_billable_amount(expense: Expense) -> Decimal:
    """Calculate the billable amount including markup.

    Args:
        expense: The expense.

    Returns:
        Billable amount.
    """
    if not expense.is_billable:
        return Decimal("0")
    return Decimal(
        str(round(expense.amount * (Decimal("1") + expense.markup_pct / Decimal("100")), 2))
    )
