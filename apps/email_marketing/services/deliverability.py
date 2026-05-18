"""Deliverability monitoring service.

Handles bounce classification, reputation scoring,
authentication checking, and recommendation generation.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Bounce classification
# ---------------------------------------------------------------------------

HARD_BOUNCE_CODES: dict[str, str] = {
    "5.1.1": "Mailbox not found",
    "5.1.2": "Domain not found",
    "5.1.6": "Mailbox has moved",
    "5.2.1": "Mailbox disabled",
    "5.2.2": "Mailbox full",
    "5.4.1": "No answer from host",
    "5.5.0": "General bounce",
    "5.7.1": "Delivery not authorized",
    "550": "Mailbox not found",
    "551": "User not local",
    "552": "Mailbox full",
    "553": "Invalid address",
    "554": "Transaction failed",
}

SOFT_BOUNCE_CODES: dict[str, str] = {
    "4.2.1": "Mailbox busy",
    "4.3.2": "System not accepting network messages",
    "4.4.1": "No answer from host",
    "4.4.2": "Bad connection",
    "4.4.7": "Message expired",
    "4.7.1": "Too many messages",
    "421": "Service unavailable",
    "450": "Mailbox busy",
    "451": "Processing error",
    "452": "Insufficient storage",
    "422": "Mailbox full (temporary)",
}


def classify_bounce(
    bounce_code: str,
    retry_count: int = 0,
) -> dict[str, Any]:
    """Classify a bounce by SMTP code.

    Determines if the bounce is hard (permanent), soft (temporary),
    or unknown, and recommends the appropriate action.

    Args:
        bounce_code: SMTP bounce code string.
        retry_count: Number of prior retry attempts.

    Returns:
        Classification dict with type, reason, and action.
    """
    clean_code = bounce_code.strip()
    if clean_code in HARD_BOUNCE_CODES:
        return {
            "type": "hard",
            "reason": HARD_BOUNCE_CODES[clean_code],
            "action": "suppress_email",
            "resubscribe_allowed": False,
            "retry_after": None,
        }
    if clean_code in SOFT_BOUNCE_CODES:
        reason = SOFT_BOUNCE_CODES[clean_code]
        if retry_count >= 3:
            return {
                "type": "soft_permanent",
                "reason": reason,
                "action": "suppress_email",
                "resubscribe_allowed": True,
                "retry_after": None,
            }
        backoff_seconds = (2**retry_count) * 3600
        return {
            "type": "soft_temporary",
            "reason": reason,
            "action": "retry",
            "resubscribe_allowed": True,
            "retry_after": backoff_seconds,
        }
    if clean_code.startswith("5"):
        return {
            "type": "hard",
            "reason": f"Permanent failure ({clean_code})",
            "action": "suppress_email",
            "resubscribe_allowed": False,
            "retry_after": None,
        }
    if clean_code.startswith("4"):
        return {
            "type": "soft_temporary",
            "reason": f"Temporary failure ({clean_code})",
            "action": "retry",
            "resubscribe_allowed": True,
            "retry_after": (2**retry_count) * 3600,
        }
    return {
        "type": "unknown",
        "reason": f"Unknown bounce code: {clean_code}",
        "action": "log_only",
        "resubscribe_allowed": True,
        "retry_after": None,
    }


# ---------------------------------------------------------------------------
# Reputation scoring
# ---------------------------------------------------------------------------


def calculate_reputation_score(metrics: dict[str, float]) -> dict[str, Any]:
    """Calculate sender reputation score from email metrics.

    Uses a weighted scoring system across 6 factors:
    bounce rate, spam complaints, opens, clicks, unsubscribes, and blacklist.

    Args:
        metrics: Dict with bounce_rate, spam_rate, open_rate,
            click_rate, unsubscribe_rate, blacklisted.

    Returns:
        Dict with overall score, grade, factor breakdown, and recommendations.
    """
    bounce_rate = metrics.get("bounce_rate", 0.0)
    spam_rate = metrics.get("spam_rate", 0.0)
    open_rate = metrics.get("open_rate", 0.0)
    click_rate = metrics.get("click_rate", 0.0)
    unsubscribe_rate = metrics.get("unsubscribe_rate", 0.0)
    blacklisted = metrics.get("blacklisted", False)

    bounce_score = 100.0 if bounce_rate < 0.02 else 70.0 if bounce_rate < 0.05 else 30.0
    spam_score = 100.0 if spam_rate < 0.001 else 60.0 if spam_rate < 0.003 else 20.0
    open_score = 100.0 if open_rate > 0.25 else 70.0 if open_rate > 0.15 else 40.0
    click_score = 100.0 if click_rate > 0.03 else 70.0 if click_rate > 0.015 else 40.0
    unsub_score = 100.0 if unsubscribe_rate < 0.002 else 70.0 if unsubscribe_rate < 0.005 else 30.0
    bl_score = 0.0 if blacklisted else 100.0

    factors = {
        "bounce_rate": {"value": bounce_rate, "weight": 0.20, "score": bounce_score},
        "spam_complaint_rate": {"value": spam_rate, "weight": 0.25, "score": spam_score},
        "open_rate": {"value": open_rate, "weight": 0.20, "score": open_score},
        "click_rate": {"value": click_rate, "weight": 0.15, "score": click_score},
        "unsubscribe_rate": {"value": unsubscribe_rate, "weight": 0.10, "score": unsub_score},
        "blacklist_status": {"value": blacklisted, "weight": 0.10, "score": bl_score},
    }
    overall = round(
        sum(f["score"] * f["weight"] for f in factors.values()),
        2,
    )
    grade = (
        "A"
        if overall >= 90
        else "B" if overall >= 75 else "C" if overall >= 60 else "D" if overall >= 40 else "F"
    )
    recommendations = generate_recommendations(factors)
    return {
        "score": overall,
        "grade": grade,
        "factors": factors,
        "recommendations": recommendations,
    }


def generate_recommendations(factors: dict[str, Any]) -> list[str]:
    """Generate actionable recommendations from reputation factors.

    Args:
        factors: Dict of factor name -> {value, weight, score}.

    Returns:
        List of recommendation strings.
    """
    recs: list[str] = []
    if factors["bounce_rate"]["score"] < 70:
        recs.append("Clean your email list: remove invalid addresses and implement double opt-in.")
    if factors["spam_complaint_rate"]["score"] < 70:
        recs.append(
            "Review email content and frequency: ensure clear unsubscribe and relevant content."
        )
    if factors["open_rate"]["score"] < 70:
        recs.append("Improve subject lines: test personalization and urgency to boost open rates.")
    if factors["click_rate"]["score"] < 70:
        recs.append("Optimize CTAs: use clear single-CTA design and A/B test button placement.")
    if factors["unsubscribe_rate"]["score"] < 70:
        recs.append("Reduce unsubscribe rate: segment audience better and reduce send frequency.")
    if factors["blacklist_status"]["score"] == 0:
        recs.append("Address blacklist issue: contact blacklist operators and fix authentication.")
    if not recs:
        recs.append("Maintain current practices: continue monitoring deliverability metrics.")
    return recs


# ---------------------------------------------------------------------------
# Authentication checking
# ---------------------------------------------------------------------------


def check_authentication(domain: str) -> dict[str, Any]:
    """Check email authentication records for a domain.

    Performs DNS lookups for SPF, DKIM, DMARC, and BIMI records.
    In production, this calls actual DNS queries; here it returns
    the structure with a flag indicating real checks are needed.

    Args:
        domain: The sending domain to check.

    Returns:
        Dict with authentication results for each mechanism.
    """

    spf_record = _dns_txt_lookup(domain)
    dkim_record = _dns_txt_lookup(f"default._domainkey.{domain}")
    dmarc_record = _dns_txt_lookup(f"_dmarc.{domain}")
    bimi_record = _dns_txt_lookup(f"default._bimi.{domain}")
    return {
        "domain": domain,
        "spf": {
            "configured": "v=spf1" in spf_record,
            "valid": _validate_spf(spf_record),
            "record": spf_record,
            "includes": _extract_spf_includes(spf_record),
        },
        "dkim": {
            "configured": bool(dkim_record),
            "valid": "v=DKIM1" in dkim_record,
            "record": dkim_record,
            "selector": "default",
        },
        "dmarc": {
            "configured": "v=DMARC1" in dmarc_record,
            "policy": _extract_dmarc_policy(dmarc_record),
            "record": dmarc_record,
            "rua": _extract_dmarc_tag(dmarc_record, "rua"),
            "ruf": _extract_dmarc_tag(dmarc_record, "ruf"),
        },
        "bimi": {
            "configured": "v=BIMI1" in bimi_record,
            "record": bimi_record,
            "logo_url": _extract_bimi_logo(bimi_record),
        },
    }


def _dns_txt_lookup(fqdn: str) -> str:
    """Perform a DNS TXT lookup.

    Args:
        fqdn: Fully qualified domain name.

    Returns:
        TXT record string or empty string on failure.
    """
    try:
        import dns.resolver

        answers = dns.resolver.resolve(fqdn, "TXT")
        return "".join(str(rdata) for rdata in answers)
    except Exception:
        return ""


def _validate_spf(record: str) -> bool:
    """Validate an SPF record."""
    if not record or "v=spf1" not in record:
        return False
    return record.count("all") > 0


def _extract_spf_includes(record: str) -> list[str]:
    """Extract include mechanisms from SPF record."""
    if not record:
        return []
    return re.findall(r"include:([^\s]+)", record)


def _extract_dmarc_policy(record: str) -> str:
    """Extract DMARC policy."""
    match = re.search(r"p=([^;\s]+)", record)
    return match.group(1) if match else "none"


def _extract_dmarc_tag(record: str, tag: str) -> str:
    """Extract a DMARC tag value."""
    pattern = rf"{tag}=([^;\s]+)"
    match = re.search(pattern, record)
    return match.group(1) if match else ""


def _extract_bimi_logo(record: str) -> str:
    """Extract BIMI logo URL."""
    match = re.search(r"l=([^;\s]+)", record)
    return match.group(1) if match else ""


import re  # noqa: E402, F811
