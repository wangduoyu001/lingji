from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PrivacyFinding:
    kind: str
    severity: str
    count: int


@dataclass(frozen=True)
class PrivacyAssessment:
    privacy: str
    findings: tuple[PrivacyFinding, ...]

    @property
    def restricted(self) -> bool:
        return self.privacy == "restricted"

    def kinds(self) -> list[str]:
        return [item.kind for item in self.findings]


class PrivacyClassifier:
    """Conservative local-only detector used before normal Vault indexing.

    This is not a replacement for encryption or human review. It only prevents
    obviously sensitive material from entering the default searchable folders.
    """

    PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
        (
            "api_key",
            "high",
            re.compile(
                r"(?i)(?:sk-[A-Za-z0-9_-]{16,}|(?:api[_ -]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,})"
            ),
        ),
        (
            "private_key",
            "high",
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ),
        (
            "password",
            "high",
            re.compile(r"(?i)(?:password|passwd|密码)\s*[:=：]\s*\S{4,}"),
        ),
        (
            "cn_identity_number",
            "high",
            re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
        ),
        (
            "bank_card",
            "high",
            re.compile(r"(?<!\d)(?:\d[ -]?){15,19}(?!\d)"),
        ),
        (
            "phone_number",
            "medium",
            re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
        ),
        (
            "email",
            "medium",
            re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        ),
    )

    HIGH_RISK_KINDS = {"api_key", "private_key", "password", "cn_identity_number", "bank_card"}

    def assess(self, text: str, extra_sensitive_terms: Iterable[str] = ()) -> PrivacyAssessment:
        findings: list[PrivacyFinding] = []
        for kind, severity, pattern in self.PATTERNS:
            count = len(pattern.findall(text or ""))
            if count:
                findings.append(PrivacyFinding(kind=kind, severity=severity, count=count))
        for term in extra_sensitive_terms:
            normalized = str(term).strip()
            if normalized and normalized in (text or ""):
                findings.append(PrivacyFinding(kind="custom_sensitive_term", severity="high", count=1))
        privacy = "restricted" if any(item.kind in self.HIGH_RISK_KINDS or item.severity == "high" for item in findings) else "private"
        return PrivacyAssessment(privacy=privacy, findings=tuple(findings))

    def redact(self, text: str) -> str:
        result = text or ""
        for kind, _, pattern in self.PATTERNS:
            result = pattern.sub(f"[REDACTED:{kind}]", result)
        return result
