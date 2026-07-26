from __future__ import annotations

from .models import ReviewCandidate, ReviewContext, RuleFinding

_DURABLE_TYPES = {"knowledge", "decision", "procedure", "preference", "project_fact"}
_DESTRUCTIVE_OPERATIONS = {"delete", "forget", "archive", "remove", "permission_change", "privacy_change"}
_UNVERIFIED_REPORT_STATES = {"", "failed", "unverified", "unknown", "cancelled", "partial"}


def hard_rule_findings(candidate: ReviewCandidate, context: ReviewContext) -> tuple[RuleFinding, ...]:
    findings: list[RuleFinding] = []

    if not candidate.memory_id or not candidate.title or not candidate.content:
        findings.append(_blocked("schema_invalid", "Candidate identity, title and content are required."))
    if candidate.memory_type in {"core", "core_memory"} or candidate.metadata.get("memory_tier") == "core":
        findings.append(_manual("core_memory_requires_owner", "Core Memory decisions always require owner review.", 100))
    if context.requested_operation.strip().lower() in _DESTRUCTIVE_OPERATIONS:
        findings.append(_manual("destructive_operation_requires_owner", "Deletion, forgetting and permission changes require owner review.", 100, reversible=False))
    if context.permission_or_privacy_change:
        findings.append(_manual("privacy_change_requires_owner", "Permission or privacy changes require owner review.", 100, reversible=False))
    if candidate.privacy == "restricted":
        findings.append(_manual("restricted_content_requires_owner", "Restricted content cannot be handled automatically.", 100))
    if context.target_project_id and candidate.project_ids and context.target_project_id not in candidate.project_ids:
        findings.append(_manual("cross_project_requires_owner", "Cross-project review or merge requires owner review.", 90))
    if context.has_conflict:
        findings.append(_manual("knowledge_conflict_requires_owner", "Conflicting knowledge requires owner review.", 90))
    if candidate.memory_type in _DURABLE_TYPES and not context.evidence_sufficient:
        findings.append(_manual("insufficient_evidence_requires_owner", "Durable knowledge lacks sufficient evidence.", 75))
    source = str(candidate.metadata.get("source_type") or candidate.metadata.get("source") or "").lower()
    report_status = str(context.development_report_status or candidate.metadata.get("status") or "").lower()
    if source in {"codex", "work_report", "development_report"} and report_status in _UNVERIFIED_REPORT_STATES:
        findings.append(_manual("unverified_work_report_requires_owner", "Failed or unverified development reports require owner review.", 90))
    if context.owner_authored or candidate.proposed_by in {"owner", "owner_manual"} or "source/owner-manual" in set(candidate.metadata.get("tags") or []):
        findings.append(_manual("owner_authored_requires_owner", "Owner-authored memory edits remain under explicit owner authority.", 100))
    return tuple(findings)


def _manual(code: str, message: str, risk_points: int, *, reversible: bool = True) -> RuleFinding:
    return RuleFinding(
        code=code,
        message=message,
        risk_points=risk_points,
        hard_manual=True,
        reversible=reversible,
    )


def _blocked(code: str, message: str) -> RuleFinding:
    return RuleFinding(
        code=code,
        message=message,
        risk_points=100,
        hard_manual=True,
        blocked=True,
        reversible=True,
    )
