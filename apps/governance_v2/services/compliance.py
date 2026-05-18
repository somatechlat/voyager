"""Compliance checking service.

Validates content against industry-specific regulatory rules
for FDA (healthcare), FINRA (finance), FTC (advertising),
and COPPA (children's content).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.governance_v2.models import ComplianceRule

logger = logging.getLogger(__name__)

# Built-in rule text templates keyed by (industry, regulation)
_BUILTIN_RULES: list[dict[str, Any]] = [
    {
        "industry": "healthcare",
        "regulation": "FDA 21 CFR 202",
        "name": "No Misleading Medical Claims",
        "description": "Content must not make unverified therapeutic claims.",
        "check_type": "keyword_scan",
        "check_config": {
            "forbidden_phrases": [
                "cures all",
                "prevents all",
                "100% effective",
                "no side effects",
                "guaranteed cure",
            ]
        },
        "severity": "critical",
        "legal_reference": "21 CFR 202.1(e)(6)(i)",
        "remediation": "Remove or substantiate medical claims with FDA-approved labeling.",
    },
    {
        "industry": "healthcare",
        "regulation": "FDA 21 CFR 202",
        "name": "Fair Balance Required",
        "description": "Must present both benefits and risks of treatments.",
        "check_type": "balance_check",
        "check_config": {"min_risk_mentions": 1},
        "severity": "high",
        "legal_reference": "21 CFR 202.1(e)(5)",
        "remediation": "Add risk/side-effect information to balance benefit claims.",
    },
    {
        "industry": "finance",
        "regulation": "FINRA 2210",
        "name": "Fair Dealing",
        "description": "Communications must be fair, balanced, and not misleading.",
        "check_type": "keyword_scan",
        "check_config": {
            "forbidden_phrases": [
                "guaranteed returns",
                "risk-free",
                "no risk",
                "double your money",
                "get rich quick",
            ]
        },
        "severity": "critical",
        "legal_reference": "FINRA Rule 2210(d)(1)(A)",
        "remediation": "Remove promises of guaranteed returns; add risk disclosures.",
    },
    {
        "industry": "finance",
        "regulation": "FINRA 2210",
        "name": "Risk Disclosure",
        "description": "Investment content must include risk disclosure statements.",
        "check_type": "required_phrase",
        "check_config": {
            "required_phrases": [
                "past performance is not indicative",
                "investment involves risk",
            ]
        },
        "severity": "high",
        "legal_reference": "FINRA Rule 2210(d)(1)(D)",
        "remediation": "Add standard risk disclosure statement to content.",
    },
    {
        "industry": "advertising",
        "regulation": "FTC Act Section 5",
        "name": "Truthful Claims",
        "description": "Advertising claims must be truthful and substantiated.",
        "check_type": "keyword_scan",
        "check_config": {
            "forbidden_phrases": [
                "guaranteed results",
                "miracle",
                "instant results",
                "works for everyone",
                "never fails",
            ]
        },
        "severity": "high",
        "legal_reference": "15 U.S.C. Section 45(a)(1)",
        "remediation": "Substantiate claims with evidence or remove superlative language.",
    },
    {
        "industry": "advertising",
        "regulation": "FTC Act Section 5",
        "name": "Clear Disclosures",
        "description": "Material connections must be clearly disclosed.",
        "check_type": "required_phrase",
        "check_config": {
            "required_phrases": [
                "#ad",
                "#sponsored",
                "paid partnership",
            ]
        },
        "severity": "high",
        "legal_reference": "16 CFR 255.5",
        "remediation": "Add clear disclosure of material connection or sponsorship.",
    },
    {
        "industry": "children",
        "regulation": "COPPA",
        "name": "Parental Consent",
        "description": "Must not collect personal data from children under 13 without consent.",
        "check_type": "keyword_scan",
        "check_config": {
            "forbidden_phrases": [
                "for kids",
                "ages 5-12",
                "children welcome",
            ]
        },
        "severity": "critical",
        "legal_reference": "15 U.S.C. Section 6501",
        "remediation": "Add parental consent flow or remove child-targeted language.",
    },
    {
        "industry": "children",
        "regulation": "COPPA",
        "name": "No Behavioral Targeting",
        "description": "Behavioral advertising to children under 13 is prohibited.",
        "check_type": "keyword_scan",
        "check_config": {
            "forbidden_phrases": [
                "personalized ads",
                "targeted to your child",
                "based on your child's interests",
            ]
        },
        "severity": "critical",
        "legal_reference": "15 U.S.C. Section 6503",
        "remediation": "Disable behavioral targeting for users under 13.",
    },
]


class ComplianceService:
    """Service for validating content against compliance rules.

    Loads active compliance rules from the database and built-in
    templates, then executes checks against content to produce a
    structured compliance report.
    """

    @staticmethod
    def validate_compliance(
        content: str,
        tenant_id: str,
        industry: str,
        regulations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Validate content against compliance rules.

        Args:
            content: The text content to validate.
            tenant_id: Tenant identifier for rule scoping.
            industry: Industry sector (healthcare, finance, etc.).
            regulations: Optional list of regulation codes to check.
                         If empty, all rules for the industry are checked.

        Returns:
            Dict with ``content_id``, ``industry``, ``regulations``,
            ``overall_compliant``, ``violations``, and ``checked_at``.
        """
        violations: list[dict[str, Any]] = []
        content_lower = content.lower()

        # Load active database rules for the tenant and industry
        db_rules = ComplianceRule.objects.filter(
            tenant_id=tenant_id,
            industry=industry,
            enabled=True,
        )
        if regulations:
            db_rules = db_rules.filter(regulation__in=regulations)

        for rule in db_rules:
            result = ComplianceService._execute_rule(rule, content_lower)
            if not result["passed"]:
                violations.append(
                    {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "regulation": rule.regulation,
                        "passed": False,
                        "severity": rule.severity,
                        "description": rule.description,
                        "violation": result["violation"],
                        "remediation": rule.remediation,
                    }
                )

        # Also run built-in rules as fallback
        for built_in in _BUILTIN_RULES:
            if built_in["industry"] != industry:
                continue
            if regulations and built_in["regulation"] not in regulations:
                continue
            result = ComplianceService._execute_builtin_rule(
                built_in,
                content_lower,
            )
            if not result["passed"]:
                # Deduplicate: skip if a DB rule already caught this
                existing = [v for v in violations if v["rule_name"] == built_in["name"]]
                if not existing:
                    violations.append(
                        {
                            "rule_id": 0,
                            "rule_name": built_in["name"],
                            "regulation": built_in["regulation"],
                            "passed": False,
                            "severity": built_in["severity"],
                            "description": built_in["description"],
                            "violation": result["violation"],
                            "remediation": built_in["remediation"],
                        }
                    )

        return {
            "content_id": "",
            "industry": industry,
            "regulations": regulations or [],
            "overall_compliant": len(violations) == 0,
            "violations": violations,
            "checked_at": datetime.now(UTC),
        }

    @staticmethod
    def seed_builtin_rules(tenant_id: str) -> int:
        """Create built-in compliance rules for a tenant.

        Args:
            tenant_id: Target tenant identifier.

        Returns:
            Number of rules created.
        """
        created = 0
        for rule_data in _BUILTIN_RULES:
            _, was_created = ComplianceRule.objects.get_or_create(
                tenant_id=tenant_id,
                industry=rule_data["industry"],
                regulation=rule_data["regulation"],
                name=rule_data["name"],
                defaults={
                    "description": rule_data["description"],
                    "check_type": rule_data["check_type"],
                    "check_config": rule_data["check_config"],
                    "severity": rule_data["severity"],
                    "legal_reference": rule_data["legal_reference"],
                    "remediation": rule_data["remediation"],
                    "enabled": True,
                },
            )
            if was_created:
                created += 1
        return created

    @staticmethod
    def _execute_rule(
        rule: ComplianceRule,
        content_lower: str,
    ) -> dict[str, Any]:
        """Execute a single compliance rule against content.

        Args:
            rule: ComplianceRule instance to execute.
            content_lower: Lowercase content text.

        Returns:
            Dict with ``passed`` (bool) and ``violation`` (str).
        """
        check_type = rule.check_type or "keyword_scan"
        config = rule.check_config or {}

        if check_type == "keyword_scan":
            forbidden = config.get("forbidden_phrases", [])
            found = [p for p in forbidden if p.lower() in content_lower]
            if found:
                return {
                    "passed": False,
                    "violation": f"Forbidden phrases found: {', '.join(found)}",
                }

        elif check_type == "required_phrase":
            required = config.get("required_phrases", [])
            missing = [p for p in required if p.lower() not in content_lower]
            if missing:
                return {
                    "passed": False,
                    "violation": f"Required phrases missing: {', '.join(missing)}",
                }

        elif check_type == "balance_check":
            min_mentions = config.get("min_risk_mentions", 1)
            risk_keywords = ["risk", "side effect", "warning", "caution"]
            risk_count = sum(1 for kw in risk_keywords if kw in content_lower)
            if risk_count < min_mentions:
                return {
                    "passed": False,
                    "violation": (
                        f"Insufficient risk disclosure " f"({risk_count} < {min_mentions} required)"
                    ),
                }

        return {"passed": True, "violation": ""}

    @staticmethod
    def _execute_builtin_rule(
        rule_data: dict[str, Any],
        content_lower: str,
    ) -> dict[str, Any]:
        """Execute a built-in compliance rule against content.

        Args:
            rule_data: Dict with rule configuration.
            content_lower: Lowercase content text.

        Returns:
            Dict with ``passed`` (bool) and ``violation`` (str).
        """
        check_type = rule_data.get("check_type", "keyword_scan")
        config = rule_data.get("check_config", {})

        if check_type == "keyword_scan":
            forbidden = config.get("forbidden_phrases", [])
            found = [p for p in forbidden if p.lower() in content_lower]
            if found:
                return {
                    "passed": False,
                    "violation": f"Forbidden phrases found: {', '.join(found)}",
                }

        elif check_type == "required_phrase":
            required = config.get("required_phrases", [])
            missing = [p for p in required if p.lower() not in content_lower]
            if missing:
                return {
                    "passed": False,
                    "violation": f"Required phrases missing: {', '.join(missing)}",
                }

        elif check_type == "balance_check":
            min_mentions = config.get("min_risk_mentions", 1)
            risk_keywords = ["risk", "side effect", "warning", "caution"]
            risk_count = sum(1 for kw in risk_keywords if kw in content_lower)
            if risk_count < min_mentions:
                return {
                    "passed": False,
                    "violation": (
                        f"Insufficient risk disclosure " f"({risk_count} < {min_mentions} required)"
                    ),
                }

        return {"passed": True, "violation": ""}
