from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from enum import Enum
from typing import Any, Callable, Mapping

from .models import ReviewCandidate


POLICY_VERSION = "memory-promotion-1"
_AUTO_THRESHOLD = 0.90
_HIGH_RISK = {
    "core", "core_memory", "identity", "credentials", "credential", "secret",
    "secrets", "permission", "permissions", "medical", "legal", "financial",
    "security", "destructive", "irreversible", "privacy", "restricted",
}


class PromotionStatus(str, Enum):
    ACTIVE = "active"
    PENDING_OWNER_REVIEW = "pending_owner_review"
    REJECTED = "rejected"
    ERROR = "error"


class AutoMemoryPromotionService:
    """Safe boundary between extracted evidence and derived current memory.

    The service owns policy evaluation and append-only audit events.  It does
    not write Obsidian, Core Memory, or formal project knowledge.  A supplied
    projection writer (normally ``MemoryDatabase.upsert_derived_projection``)
    is the only mutable derived-index seam.
    """

    def __init__(
        self,
        *,
        state_db: Any,
        memory_db: Any | None = None,
        projection_writer: Callable[..., Any] | None = None,
        evidence_store: Any | None = None,
        policy_version: str = POLICY_VERSION,
    ):
        self.state_db = state_db
        self.memory_db = memory_db
        self.projection_writer = projection_writer
        self.evidence_store = evidence_store
        self.policy_version = str(policy_version or POLICY_VERSION)

    def evaluate(self, candidate: ReviewCandidate | Mapping[str, Any]) -> dict[str, Any]:
        selected = self._normalize(candidate)
        existing = self._existing_decision(selected)
        if existing:
            recovered_prior = self._existing_recovery(selected.memory_id, str(existing.get("decision_id") or ""))
            if recovered_prior is not None:
                return recovered_prior
            if existing.get("status") != PromotionStatus.ERROR.value:
                return existing
            # A failed derived-index write may be retried after the provider
            # recovers.  Reuse the immutable decision ID and append only the
            # recovery outcome; do not create a duplicate decision audit.
            try:
                self._write_projection(selected, str(existing.get("decision_id") or ""))
            except Exception:
                return existing
            recovered = dict(existing)
            recovered.update({
                "status": PromotionStatus.ACTIVE.value,
                "reason_codes": ["projection_recovered"],
                "error": "",
            })
            self._append("memory_projection_activated", selected.memory_id, recovered)
            self._append("memory_promotion_recovered", selected.memory_id, recovered)
            return recovered

        self._record_candidate(selected)
        reasons = self._policy_reasons(selected)
        status = PromotionStatus.ACTIVE if not reasons else PromotionStatus.PENDING_OWNER_REVIEW
        decision_id = self._decision_id(selected, status.value, self.policy_version)
        result = self._result(
            selected,
            decision_id,
            status,
            reasons or ["auto_activation_eligible"],
            mutation=False,
        )
        if status is PromotionStatus.ACTIVE:
            try:
                self._write_projection(selected, decision_id)
            except Exception as exc:
                result = self._result(
                    selected,
                    decision_id,
                    PromotionStatus.ERROR,
                    ["projection_persist_failed"],
                    mutation=False,
                    error=f"{type(exc).__name__}: {exc}"[:500],
                )
                self._append("memory_promotion_projection_error", selected.memory_id, result)
                self._append("memory_promotion_decision", selected.memory_id, result)
                return result
            self._append("memory_projection_activated", selected.memory_id, result)
        self._append("memory_promotion_decision", selected.memory_id, result)
        return result

    # Explicit aliases make the boundary readable at call sites that use the
    # vocabulary of candidates rather than review decisions.
    promote = evaluate
    submit = evaluate

    def approve(
        self,
        candidate_id: str,
        *,
        expected_content_hash: str,
        owner_confirmed: bool,
    ) -> dict[str, Any]:
        if not owner_confirmed:
            raise PermissionError("owner confirmation is required")
        candidate = self.candidate(candidate_id)
        if candidate is None:
            raise LookupError(f"Unknown memory candidate: {candidate_id}")
        expected = str(expected_content_hash or "")
        if expected != str(candidate.get("content_hash") or ""):
            raise ValueError("candidate content hash is stale")
        if self._existing_owner_result(
            "memory_promotion_owner_rejected",
            str(candidate_id),
            self._decision_id(self._normalize(candidate), "owner_rejected", self.policy_version),
        ) is not None:
            raise ValueError("rejected candidate cannot be approved")
        if candidate.get("status") == PromotionStatus.REJECTED.value:
            raise ValueError("rejected candidate cannot be approved")
        selected = self._normalize(candidate)
        decision_id = self._decision_id(selected, "owner_approved", self.policy_version)
        prior = self._existing_owner_result("memory_promotion_owner_approved", selected.memory_id, decision_id)
        if prior is not None:
            return prior
        result = self._result(selected, decision_id, PromotionStatus.ACTIVE, [], mutation=False)
        try:
            self._write_projection(selected, decision_id)
        except Exception as exc:
            result = self._result(
                selected, decision_id, PromotionStatus.ERROR, ["projection_persist_failed"],
                mutation=False, error=f"{type(exc).__name__}: {exc}"[:500],
            )
            self._append("memory_promotion_projection_error", selected.memory_id, result)
            return result
        self._append("memory_promotion_owner_approved", selected.memory_id, result)
        self._append("memory_projection_activated", selected.memory_id, result)
        return result

    def reject(
        self,
        candidate_id: str,
        *,
        expected_content_hash: str,
        owner_confirmed: bool,
        reason: str,
    ) -> dict[str, Any]:
        if not owner_confirmed:
            raise PermissionError("owner confirmation is required")
        candidate = self.candidate(candidate_id)
        if candidate is None:
            raise LookupError(f"Unknown memory candidate: {candidate_id}")
        if str(expected_content_hash or "") != str(candidate.get("content_hash") or ""):
            raise ValueError("candidate content hash is stale")
        note = str(reason or "").strip()
        if not note:
            raise ValueError("rejection reason is required")
        selected = self._normalize(candidate)
        decision_id = self._decision_id(selected, "owner_rejected", self.policy_version)
        prior = self._existing_owner_result("memory_promotion_owner_rejected", selected.memory_id, decision_id)
        if prior is not None:
            return prior
        result = self._result(
            selected,
            decision_id,
            PromotionStatus.REJECTED,
            ["owner_rejected"],
            mutation=False,
        )
        result["owner_reason"] = note[:2000]
        self._append("memory_promotion_owner_rejected", selected.memory_id, result)
        return result

    def candidate(self, candidate_id: str) -> dict[str, Any] | None:
        wanted = str(candidate_id or "")
        for row in self.state_db.recent_events(limit=100000):
            if row.get("event_type") != "memory_candidate_recorded":
                continue
            if str(row.get("entity_id") or "") != wanted:
                continue
            return self._payload(row)
        return None

    def candidates(self, *, limit: int = 100) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in self.state_db.recent_events(limit=100000):
            if row.get("event_type") != "memory_candidate_recorded":
                continue
            item = self._payload(row)
            candidate_id = str(item.get("candidate_id") or "")
            if candidate_id and candidate_id not in seen:
                output.append(item)
                seen.add(candidate_id)
            if len(output) >= max(int(limit), 1):
                break
        return output

    def _normalize(self, value: ReviewCandidate | Mapping[str, Any]) -> ReviewCandidate:
        selected = value if isinstance(value, ReviewCandidate) else ReviewCandidate.from_mapping(value)
        content_hash = self._authentic_content_hash(selected)
        if selected.content_hash and selected.content_hash != content_hash:
            raise ValueError("content hash does not match normalized candidate content")
        candidate_id = selected.memory_id or f"LJ-CAND-{content_hash[:20].upper()}"
        metadata = dict(selected.metadata)
        if selected.memory_id != candidate_id or selected.content_hash != content_hash:
            from dataclasses import replace
            selected = replace(selected, memory_id=candidate_id, content_hash=content_hash, metadata=metadata)
        return selected

    def _policy_reasons(self, candidate: ReviewCandidate) -> list[str]:
        reasons: list[str] = []
        if not candidate.memory_id or not candidate.title or not candidate.content:
            reasons.append("schema_invalid")
        confidence = candidate.confidence
        numeric_confidence = (
            float(confidence)
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
            else None
        )
        if numeric_confidence is None or not math.isfinite(numeric_confidence) or numeric_confidence < _AUTO_THRESHOLD:
            reasons.append("confidence_below_threshold")
        if not self._has_authoritative_evidence(candidate):
            reasons.append("direct_user_or_authoritative_source_required")
        refs = self._evidence_refs(candidate)
        if not refs:
            reasons.append("evidence_required")
        elif not any(self._evidence_verifiable(ref) for ref in refs):
            reasons.append("evidence_reference_unverifiable")
        metadata = dict(candidate.metadata)
        if self._truthy(metadata.get("has_conflict")) or self._truthy(metadata.get("conflict")):
            reasons.append("unresolved_conflict")
        if any(self._truthy(metadata.get(key)) for key in ("duplicate_ambiguity", "duplicate_ambiguous")):
            reasons.append("duplicate_ambiguity")
        flags = {str(item).strip().lower() for item in candidate.risk_flags}
        raw_flags = metadata.get("risk_flags") or ()
        if isinstance(raw_flags, str):
            raw_flags = (raw_flags,)
        flags.update(str(item).strip().lower() for item in raw_flags if str(item).strip())
        if candidate.memory_type.lower() in {"core", "core_memory"} or str(metadata.get("memory_tier") or "").lower() == "core":
            reasons.append("core_memory_requires_owner")
        if candidate.privacy.lower() in {"restricted", "sensitive", "secret"}:
            reasons.append("restricted_requires_owner")
        for flag in sorted(flags & _HIGH_RISK):
            reasons.append(f"{flag}_requires_owner")
        memory_type = candidate.memory_type.lower()
        if memory_type in _HIGH_RISK and memory_type not in {"core", "core_memory"}:
            reasons.append(f"{memory_type}_requires_owner")
        return list(dict.fromkeys(reasons))

    @staticmethod
    def _has_authoritative_evidence(candidate: ReviewCandidate) -> bool:
        metadata = dict(candidate.metadata)
        if any(AutoMemoryPromotionService._truthy(metadata.get(key)) for key in ("direct_user_evidence", "user_authored", "owner_confirmed_evidence")):
            return True
        authority = candidate.authority.lower()
        source = candidate.source_kind.lower()
        if authority in {"direct_user", "user", "owner", "owner_manual", "user_explicit"}:
            return True
        return (
            authority in {"project_authority", "authoritative_project", "current_project"}
            and source in {"current_project_document", "project_authority", "authoritative_project", "code", "test"}
            and ("current_authoritative" not in metadata or AutoMemoryPromotionService._truthy(metadata.get("current_authoritative")))
        )

    @staticmethod
    def _evidence_refs(candidate: ReviewCandidate) -> tuple[str, ...]:
        return tuple(str(item).strip() for item in candidate.source_refs if str(item).strip())

    def _evidence_verifiable(self, reference: str) -> bool:
        """Resolve evidence through existing state/source read models only."""
        wanted = str(reference).strip()
        if not wanted:
            return False
        allowed_event_types = {
            "evidence_recorded", "source_ingested", "raw_snapshot_created",
            "extraction_completed", "source_snapshot_committed", "message_recorded",
        }
        for row in self.state_db.recent_events(limit=100000):
            if str(row.get("event_type") or "") not in allowed_event_types:
                continue
            if str(row.get("entity_id") or "") == wanted:
                return True
            payload = self._payload(row)
            if self._contains_reference(payload, wanted):
                return True
        store = self.evidence_store
        if store is not None:
            for method_name in ("get_source", "get_conversation", "get_message"):
                method = getattr(store, method_name, None)
                if callable(method):
                    try:
                        if method(wanted) is not None:
                            return True
                    except Exception:
                        continue
        return False

    @classmethod
    def _contains_reference(cls, value: Any, wanted: str) -> bool:
        if isinstance(value, Mapping):
            return any(cls._contains_reference(item, wanted) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(cls._contains_reference(item, wanted) for item in value)
        return str(value).strip() == wanted

    @staticmethod
    def _authentic_content_hash(candidate: ReviewCandidate) -> str:
        material = {
            "title": str(candidate.title or "").strip(),
            "content": str(candidate.content or "").strip(),
            "structured": dict(candidate.structured_content),
        }
        return hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _record_candidate(self, candidate: ReviewCandidate) -> None:
        payload = self._candidate_payload(candidate)
        for row in self.state_db.recent_events(limit=100000):
            if row.get("event_type") != "memory_candidate_recorded":
                continue
            prior = self._payload(row)
            if (
                prior.get("candidate_id") == candidate.memory_id
                and prior.get("content_hash") == candidate.content_hash
                and prior.get("extractor_version") == candidate.extractor_version
            ):
                return
        self._append("memory_candidate_recorded", candidate.memory_id, payload)

    def _existing_decision(self, candidate: ReviewCandidate) -> dict[str, Any] | None:
        for row in self.state_db.recent_events(limit=100000):
            if row.get("event_type") != "memory_promotion_decision":
                continue
            item = self._payload(row)
            if (
                item.get("candidate_id") == candidate.memory_id
                and item.get("content_hash") == candidate.content_hash
                and item.get("extractor_version") == candidate.extractor_version
                and item.get("policy_version") == self.policy_version
            ):
                return item
        return None

    def _existing_owner_result(self, event_type: str, candidate_id: str, decision_id: str) -> dict[str, Any] | None:
        for row in self.state_db.recent_events(limit=100000):
            if row.get("event_type") != event_type:
                continue
            item = self._payload(row)
            if str(item.get("candidate_id") or "") == str(candidate_id) and item.get("decision_id") == decision_id:
                return item
        return None

    def _existing_recovery(self, candidate_id: str, decision_id: str) -> dict[str, Any] | None:
        return self._existing_owner_result("memory_promotion_recovered", candidate_id, decision_id)

    def rebuild_derived_projections(self) -> dict[str, int]:
        """Replay active promotion events into the rebuildable memory index."""
        latest: dict[str, dict[str, Any]] = {}
        rejected: set[str] = set()
        active_events = {
            "memory_promotion_decision", "memory_promotion_owner_approved",
            "memory_promotion_recovered", "memory_projection_activated",
        }
        # StateDatabase returns newest first; replay oldest to newest so a
        # newer extractor/policy decision or explicit rejection wins.
        for row in reversed(self.state_db.recent_events(limit=100000)):
            event_type = str(row.get("event_type") or "")
            payload = self._payload(row)
            candidate_id = str(payload.get("candidate_id") or row.get("entity_id") or "")
            if not candidate_id:
                continue
            if event_type == "memory_promotion_owner_rejected":
                rejected.add(candidate_id)
                latest.pop(candidate_id, None)
            elif event_type in active_events and payload.get("status") == PromotionStatus.ACTIVE.value:
                rejected.discard(candidate_id)
                latest[candidate_id] = payload
        outcomes = latest
        rebuilt = 0
        failed = 0
        for candidate_id, payload in outcomes.items():
            if candidate_id in rejected:
                continue
            decision_id = str(payload.get("decision_id") or "")
            if not decision_id:
                continue
            if self._projection_exists(candidate_id, decision_id, str(payload.get("content_hash") or "")):
                continue
            try:
                self._write_projection(self._normalize(payload), decision_id)
            except Exception:
                failed += 1
                continue
            rebuilt += 1
        return {"rebuilt": rebuilt, "failed": failed, "skipped": len(outcomes) - rebuilt - failed}

    def _projection_exists(self, candidate_id: str, decision_id: str, content_hash: str) -> bool:
        database = self.memory_db
        fetch = getattr(database, "fetch_memory", None) if database is not None else None
        if not callable(fetch):
            return False
        try:
            item = fetch(candidate_id, include_chunks=False)
        except TypeError:
            item = fetch(candidate_id)
        except Exception:
            return False
        if not isinstance(item, Mapping):
            return False
        relationships = item.get("relationships") or {}
        return (
            item.get("memory_tier") == "derived"
            and str(item.get("content_hash") or "") == content_hash
            and str(relationships.get("decision_id") or "") == decision_id
        )

    def _write_projection(self, candidate: ReviewCandidate, decision_id: str) -> Any:
        writer = self.projection_writer
        if writer is None and self.memory_db is not None:
            writer = self.memory_db.upsert_derived_projection
        if writer is None:
            raise RuntimeError("derived projection writer is unavailable")
        refs = list(self._evidence_refs(candidate))
        kwargs = {
            "memory_id": candidate.memory_id,
            "title": candidate.title,
            "content": candidate.content,
            "content_hash": candidate.content_hash,
            "evidence_refs": refs,
            "confidence": candidate.confidence,
            "authority": candidate.authority,
            "source_kind": candidate.source_kind,
            "policy_version": self.policy_version,
            "decision_id": decision_id,
            "candidate_metadata": dict(candidate.metadata),
        }
        try:
            result = writer(**kwargs)
        except TypeError:
            result = writer(kwargs)
        if isinstance(result, Mapping):
            state = str(result.get("status") or "").strip().lower()
            if state in {"error", "failed", "degraded", "pending", "rebuild_required"}:
                raise RuntimeError(str(result.get("error") or result.get("message") or state))
        return result

    def _result(
        self,
        candidate: ReviewCandidate,
        decision_id: str,
        status: PromotionStatus,
        reasons: list[str],
        *,
        mutation: bool,
        error: str = "",
    ) -> dict[str, Any]:
        result = {
            **self._candidate_payload(candidate),
            "decision_id": decision_id,
            "status": status.value,
            "reason_codes": list(reasons),
            "policy_version": self.policy_version,
            "mutation_performed": bool(mutation),
            "evidence_refs": list(self._evidence_refs(candidate)),
            "error": error,
        }
        return result

    @staticmethod
    def _candidate_payload(candidate: ReviewCandidate) -> dict[str, Any]:
        payload = asdict(candidate)
        payload["project_ids"] = list(candidate.project_ids)
        payload["source_refs"] = list(candidate.source_refs)
        payload["risk_flags"] = list(candidate.risk_flags)
        payload["structured_content"] = dict(candidate.structured_content)
        payload["candidate_id"] = candidate.memory_id
        payload["evidence_refs"] = list(candidate.source_refs)
        return payload

    def _decision_id(self, candidate: ReviewCandidate, status: str, policy_version: str) -> str:
        material = {
            "candidate_id": candidate.memory_id,
            "content_hash": candidate.content_hash,
            "extractor_version": candidate.extractor_version,
            "policy_version": policy_version,
            "status": status,
        }
        token = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
        return f"LJ-PROM-{token.upper()}"

    def _append(self, event_type: str, entity_id: str, payload: Mapping[str, Any]) -> None:
        self.state_db.append_event(event_type, "memory_candidate", entity_id, dict(payload))

    @staticmethod
    def _payload(row: Mapping[str, Any]) -> dict[str, Any]:
        raw = row.get("payload_json")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return dict(row.get("payload") or {}) if isinstance(row.get("payload"), Mapping) else {}

    @staticmethod
    def _truthy(value: Any) -> bool:
        return value is True or str(value or "").strip().lower() in {"1", "true", "yes", "on"}
# Shorter names are useful for callers that treat this as a policy boundary.
AutomaticMemoryPromotionService = AutoMemoryPromotionService
