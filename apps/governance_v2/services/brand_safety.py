"""Brand safety scanning service.

Provides content scanning for profanity, sensitive topics,
competitor mentions, medical claims, financial promises,
and required disclaimers.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Built-in profanity word list — English (can be extended via BrandSafetyRule.conditions)
_PROFANITY_WORDS: list[str] = [
    "damn",
    "hell",
    "crap",
    "stupid",
    "idiot",
    "moron",
    "loser",
    "trash",
    "garbage",
    "suck",
    "jerk",
    "fool",
]

# Sensitive topic keywords mapped to topic names
_SENSITIVE_TOPIC_PATTERNS: dict[str, list[str]] = {
    "politics": [
        "election",
        "democrat",
        "republican",
        "senator",
        "congressman",
        "president",
        "vote",
        "political",
        "party",
        "campaign",
        "liberal",
        "conservative",
        "parliament",
        "government",
    ],
    "religion": [
        "christianity",
        "islam",
        "judaism",
        "hinduism",
        "buddhism",
        "atheist",
        "religious",
        "faith",
        "church",
        "mosque",
        "temple",
        "prayer",
        "worship",
        "god",
        "allah",
    ],
    "violence": [
        "kill",
        "murder",
        "attack",
        "war",
        "battle",
        "fight",
        "weapon",
        "gun",
        "bomb",
        "terrorist",
        "assault",
        "violent",
        "bloodshed",
        "conflict",
        "combat",
    ],
    "tragedy": [
        "disaster",
        "accident",
        "casualty",
        "death toll",
        "fatal",
        "tragedy",
        "catastrophe",
        "devastating",
        "horrific",
    ],
    "adult_content": [
        "porn",
        "sexual",
        "nude",
        "explicit",
        "xxx",
        "adult content",
        "nsfw",
    ],
    "drugs": [
        "cocaine",
        "heroin",
        "marijuana",
        "drug abuse",
        "substance abuse",
        "narcotic",
        "methamphetamine",
    ],
    "gambling": [
        "casino",
        "betting",
        "gamble",
        "poker",
        "slot machine",
        "wager",
        "lottery",
        "sports betting",
        "gambling",
    ],
}

# Common competitor name patterns (placeholder; real ones come from BrandSafetyRule)
_DEFAULT_COMPETITOR_PATTERNS: list[str] = []

# Medical claim keywords for FDA compliance
_MEDICAL_CLAIM_PATTERNS: list[str] = [
    "cures",
    "prevents",
    "treats all",
    "guaranteed to cure",
    "eliminates",
    "100% effective",
    "miracle cure",
    "no side effects",
    "clinical proven",
    "fda approved",
]

# Financial promise keywords for FINRA compliance
_FINANCIAL_PROMISE_PATTERNS: list[str] = [
    "guaranteed returns",
    "risk-free investment",
    "double your money",
    "no risk",
    "promise profit",
    "guaranteed income",
    "get rich quick",
    "sure thing",
    "can't lose",
]


class BrandSafetyService:
    """Service for scanning content against brand safety rules.

    Performs real-time text scanning for profanity, sensitive topics,
    competitor mentions, medical claims, financial promises, and
    missing required disclaimers. Returns a structured result with
    violations and recommended actions.
    """

    @staticmethod
    def scan_content(
        content: str,
        tenant_id: str,
        industry: str = "general",
        content_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Scan content for brand safety violations.

        Args:
            content: The text content to scan.
            tenant_id: Tenant identifier for rule scoping.
            industry: Industry context (healthcare, finance, etc.).
            content_type: Type of content (text, image, video).
            metadata: Additional context for scanning.

        Returns:
            Dict with ``passed``, ``action``, ``violations``,
            and ``scan_timestamp`` keys.
        """
        violations: list[dict[str, Any]] = []
        content_lower = content.lower()

        # 1. Profanity detection
        profanity_result = BrandSafetyService._detect_profanity(content_lower)
        if profanity_result["detected"]:
            violations.append(
                {
                    "type": "profanity",
                    "severity": "critical",
                    "message": f"Profanity detected: {', '.join(profanity_result['words'])}",
                    "details": {"words": profanity_result["words"]},
                }
            )

        # 2. Sensitive topic detection
        sensitive_topics = BrandSafetyService._detect_sensitive_topics(content_lower)
        for topic_name, confidence in sensitive_topics:
            violations.append(
                {
                    "type": "sensitive_topic",
                    "severity": "high",
                    "message": f"Sensitive topic detected: {topic_name}",
                    "details": {"topic": topic_name, "confidence": confidence},
                }
            )

        # 3. Competitor mention detection
        competitors = BrandSafetyService._detect_competitors(
            content_lower,
            tenant_id,
            metadata or {},
        )
        for competitor in competitors:
            violations.append(
                {
                    "type": "competitor_mention",
                    "severity": "medium",
                    "message": f"Competitor mentioned: {competitor}",
                    "details": {"competitor": competitor},
                }
            )

        # 4. Regulatory compliance checks by industry
        if industry == "healthcare":
            medical_claims = BrandSafetyService._detect_medical_claims(content_lower)
            if medical_claims:
                violations.append(
                    {
                        "type": "medical_claim",
                        "severity": "critical",
                        "message": f"Unverified medical claims: {', '.join(medical_claims)}",
                        "details": {"claims": medical_claims},
                    }
                )

        if industry == "finance":
            financial_promises = BrandSafetyService._detect_financial_promises(
                content_lower,
            )
            if financial_promises:
                violations.append(
                    {
                        "type": "financial_promise",
                        "severity": "critical",
                        "message": (
                            f"Financial promises detected: " f"{', '.join(financial_promises)}"
                        ),
                        "details": {"promises": financial_promises},
                    }
                )

        # 5. Required disclaimer check
        missing_disclaimers = BrandSafetyService._check_disclaimers(
            content_lower,
            tenant_id,
            metadata or {},
        )
        for disclaimer in missing_disclaimers:
            violations.append(
                {
                    "type": "missing_disclaimer",
                    "severity": "high",
                    "message": f"Missing required disclaimer: {disclaimer}",
                    "details": {"disclaimer": disclaimer},
                }
            )

        # Determine overall action
        has_critical = any(v["severity"] == "critical" for v in violations)
        has_high = any(v["severity"] == "high" for v in violations)

        if has_critical:
            overall_action = "block"
        elif has_high:
            overall_action = "require_approval"
        else:
            overall_action = "pass"

        return {
            "passed": overall_action == "pass",
            "action": overall_action,
            "violations": violations,
            "scan_timestamp": datetime.now(UTC),
        }

    @staticmethod
    def _detect_profanity(content_lower: str) -> dict[str, Any]:
        """Detect profanity words in the content.

        Args:
            content_lower: Lowercase content text.

        Returns:
            Dict with ``detected`` (bool) and ``words`` (list).
        """
        found: list[str] = []
        for word in _PROFANITY_WORDS:
            pattern = r"\b" + re.escape(word) + r"\b"
            if re.search(pattern, content_lower):
                found.append(word)
        return {"detected": len(found) > 0, "words": found}

    @staticmethod
    def _detect_sensitive_topics(content_lower: str) -> list[tuple[str, float]]:
        """Detect sensitive topics in the content.

        Args:
            content_lower: Lowercase content text.

        Returns:
            List of (topic_name, confidence_score) tuples.
        """
        found: list[tuple[str, float]] = []
        for topic, keywords in _SENSITIVE_TOPIC_PATTERNS.items():
            match_count = sum(1 for kw in keywords if kw.lower() in content_lower)
            if match_count > 0:
                confidence = min(1.0, match_count / max(len(keywords) * 0.1, 1.0))
                found.append((topic, round(confidence, 2)))
        return found

    @staticmethod
    def _detect_competitors(
        content_lower: str,
        tenant_id: str,
        metadata: dict[str, Any],
    ) -> list[str]:
        """Detect competitor mentions in the content.

        Args:
            content_lower: Lowercase content text.
            tenant_id: Tenant identifier.
            metadata: May contain 'competitor_list' override.

        Returns:
            List of competitor names found in the content.
        """
        competitor_list: list[str] = metadata.get(
            "competitor_list",
            _DEFAULT_COMPETITOR_PATTERNS,
        )
        found: list[str] = []
        for competitor in competitor_list:
            if competitor.lower() in content_lower:
                found.append(competitor)
        return found

    @staticmethod
    def _detect_medical_claims(content_lower: str) -> list[str]:
        """Detect unverified medical claims for FDA compliance.

        Args:
            content_lower: Lowercase content text.

        Returns:
            List of medical claim phrases found.
        """
        return [phrase for phrase in _MEDICAL_CLAIM_PATTERNS if phrase.lower() in content_lower]

    @staticmethod
    def _detect_financial_promises(content_lower: str) -> list[str]:
        """Detect financial promises for FINRA compliance.

        Args:
            content_lower: Lowercase content text.

        Returns:
            List of financial promise phrases found.
        """
        return [phrase for phrase in _FINANCIAL_PROMISE_PATTERNS if phrase.lower() in content_lower]

    @staticmethod
    def _check_disclaimers(
        content_lower: str,
        tenant_id: str,
        metadata: dict[str, Any],
    ) -> list[str]:
        """Check for missing required disclaimers.

        Args:
            content_lower: Lowercase content text.
            tenant_id: Tenant identifier.
            metadata: May contain 'required_disclaimers' list.

        Returns:
            List of missing disclaimer texts.
        """
        required: list[str] = metadata.get("required_disclaimers", [])
        missing: list[str] = []
        for disclaimer in required:
            if disclaimer.lower() not in content_lower:
                missing.append(disclaimer)
        return missing
