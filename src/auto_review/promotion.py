from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from enum import Enum
from typing import Any, Callable, Mapping
from pathlib import Path

from .models import (
    BatchLinkResult, PromotionEvidence, PromotionProjectionState, ProvenanceRef,
    ResolvedProvenance, ReviewCandidate,
)


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
        self._last_promotion_evidence: dict[str, Any] = {}
        self._operation_owner = f"promotion:{id(self)}"
        self._provenance_errors: list[str] = []

    def evaluate(self, candidate: ReviewCandidate | Mapping[str, Any]) -> dict[str, Any]:
        # Evidence belongs to one promote/evaluate invocation only.  Never let
        # a later pending/rejected/error result inherit a prior candidate's
        # projection/link provenance.
        self._last_promotion_evidence = {}
        selected = self._normalize(candidate)
        provenance = self._normalize_provenance(selected)
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
            decision_id = str(existing.get("decision_id") or "")
            if not self._claim_lease(decision_id):
                return existing
            start_recorded = self.state_db.get_event(f"promotion:{decision_id}:memory_promotion_preparing") is not None if hasattr(self.state_db, "get_event") else False
            try:
                if not start_recorded:
                    self._record_promotion_event("memory_promotion_preparing", selected, decision_id, provenance)
                    start_recorded = True
                self._write_projection(selected, str(existing.get("decision_id") or ""))
            except Exception:
                if start_recorded:
                    terminal_type = self._terminal_type_for_evidence()
                    try:
                        self._record_terminal(selected, decision_id, terminal_type, provenance)
                    except Exception:
                        pass
                self._release_lease(decision_id)
                return existing
            recovered = dict(existing)
            recovered.update({
                "status": PromotionStatus.ACTIVE.value,
                "reason_codes": ["projection_recovered"],
                "error": "",
            })
            recovered["promotion_evidence"] = dict(self._last_promotion_evidence)
            self._record_terminal(selected, decision_id, "memory_projection_activated", provenance)
            self._append("memory_promotion_recovered", selected.memory_id, recovered)
            self._release_lease(decision_id)
            return recovered

        self._record_candidate(selected)
        reasons = self._policy_reasons(selected)
        reasons.extend(code for code in self._provenance_errors if code not in reasons)
        if not provenance.linkable_messages:
            reasons.append("structured_message_provenance_required")
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
            if not self._claim_lease(decision_id):
                result = self._result(selected, decision_id, PromotionStatus.ERROR, ["promotion_lease_conflict"], mutation=False)
                self._append("memory_promotion_decision", selected.memory_id, result)
                return result
            try:
                self._record_promotion_event("memory_promotion_preparing", selected, decision_id, provenance)
            except Exception:
                self._release_lease(decision_id)
                result = self._result(selected, decision_id, PromotionStatus.ERROR, ["promotion_start_event_failed"], mutation=False)
                self._append("memory_promotion_decision", selected.memory_id, result)
                return result
            try:
                self._write_projection(selected, decision_id)
            except Exception:
                if not self._last_promotion_evidence and self.projection_writer is None:
                    self._last_promotion_evidence = {"candidate_id": selected.memory_id, "decision_id": decision_id, "memory_id": selected.memory_id, "state": PromotionProjectionState.REPAIR_REQUIRED.value, "error_codes": ["promotion_persist_failed"]}
                result = self._result(
                    selected,
                    decision_id,
                    PromotionStatus.ERROR,
                    ["projection_persist_failed"],
                    mutation=False,
                    error="",
                )
                if self.projection_writer is None:
                    terminal_type = self._terminal_type_for_evidence()
                    self._record_terminal(selected, decision_id, terminal_type, provenance)
                self._append("memory_promotion_decision", selected.memory_id, result)
                return result
            result["promotion_evidence"] = dict(self._last_promotion_evidence)
            self._record_terminal(selected, decision_id, "memory_projection_activated", provenance)
            self._release_lease(decision_id)
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
        self._last_promotion_evidence = {}
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
        provenance = self._normalize_provenance(selected)
        decision_id = self._decision_id(selected, "owner_approved", self.policy_version)
        prior = self._existing_owner_result("memory_promotion_owner_approved", selected.memory_id, decision_id)
        if prior is not None:
            return prior
        if not provenance.linkable_messages:
            result = self._result(selected, decision_id, PromotionStatus.PENDING_OWNER_REVIEW, ["structured_message_provenance_required"], mutation=False)
            self._append("memory_promotion_owner_approved", selected.memory_id, result)
            return result
        result = self._result(selected, decision_id, PromotionStatus.ACTIVE, [], mutation=False)
        if not self._claim_lease(decision_id):
            return self._result(selected, decision_id, PromotionStatus.ERROR, ["promotion_lease_conflict"], mutation=False)
        start_recorded = False
        try:
            self._record_promotion_event("memory_promotion_preparing", selected, decision_id, provenance)
            start_recorded = True
            self._write_projection(selected, decision_id)
        except Exception:
            if not self._last_promotion_evidence:
                self._last_promotion_evidence = {
                    "candidate_id": selected.memory_id,
                    "decision_id": decision_id,
                    "decision": "error",
                    "resulting_lifecycle": PromotionStatus.ERROR.value,
                    "memory_id": selected.memory_id,
                    "resolved_message_primary_ids": [],
                    "created_link_ids": [],
                    "reused_link_ids": [],
                    "rollback": "not_needed",
                }
            result = self._result(
                selected, decision_id, PromotionStatus.ERROR, ["projection_persist_failed"],
                mutation=False, error="",
            )
            if start_recorded:
                terminal_type = self._terminal_type_for_evidence()
                self._record_terminal(selected, decision_id, terminal_type, provenance)
            self._append("memory_promotion_projection_error", selected.memory_id, result)
            self._release_lease(decision_id)
            return result
        result["promotion_evidence"] = dict(self._last_promotion_evidence)
        self._record_terminal(selected, decision_id, "memory_projection_activated", provenance)
        self._append("memory_promotion_owner_approved", selected.memory_id, result)
        self._release_lease(decision_id)
        return result

    def reject(
        self,
        candidate_id: str,
        *,
        expected_content_hash: str,
        owner_confirmed: bool,
        reason: str,
    ) -> dict[str, Any]:
        self._last_promotion_evidence = {}
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
        from dataclasses import replace
        normalized_refs: list[ProvenanceRef] = []
        malformed_refs = list(selected.provenance_errors)
        resolver = getattr(self.evidence_store, "resolve_exact_message_ref", None) if self.evidence_store is not None else None
        for item in selected.source_refs:
            if isinstance(item, ProvenanceRef):
                normalized_refs.append(item)
                continue
            if isinstance(item, Mapping):
                # ReviewCandidate.from_mapping normally handles these.  Keep
                # direct construction fail-closed rather than stringifying a
                # malformed typed reference into context evidence.
                kind = item.get("kind")
                value_text = item.get("value")
                content_hash = item.get("content_hash")
                if (
                    isinstance(kind, str)
                    and kind in {"message", "event", "source", "conversation", "evidence"}
                    and isinstance(value_text, str)
                    and value_text.strip()
                    and (content_hash is None or (isinstance(content_hash, str) and content_hash.strip()))
                ):
                    normalized_refs.append(ProvenanceRef(kind, value_text, content_hash))
                else:
                    malformed_refs.append("provenance_typed_invalid")
                    continue
                continue
            if not str(item).strip():
                continue
            if not isinstance(item, str):
                malformed_refs.append("provenance_typed_invalid")
                continue
            raw = str(item).strip()
            if callable(resolver):
                try:
                    resolved = resolver(raw)
                    normalized_refs.append(ProvenanceRef("message", raw, resolved.content_hash))
                    continue
                except Exception:
                    pass
            normalized_refs.append(ProvenanceRef("evidence", raw))
        normalized_refs = tuple(normalized_refs)
        if normalized_refs != selected.source_refs or tuple(dict.fromkeys(malformed_refs)) != selected.provenance_errors:
            selected = replace(selected, source_refs=normalized_refs, provenance_errors=tuple(dict.fromkeys(malformed_refs)))
        content_hash = self._authentic_content_hash(selected)
        if selected.content_hash and selected.content_hash != content_hash:
            raise ValueError("content hash does not match normalized candidate content")
        candidate_id = selected.memory_id or f"LJ-CAND-{content_hash[:20].upper()}"
        metadata = dict(selected.metadata)
        if selected.memory_id != candidate_id or selected.content_hash != content_hash:
            selected = replace(selected, memory_id=candidate_id, content_hash=content_hash, metadata=metadata)
        return selected

    def _normalize_provenance(self, candidate: ReviewCandidate) -> ResolvedProvenance:
        self._provenance_errors = list(candidate.provenance_errors)
        store = self.evidence_store
        resolved = []
        context = []
        seen_messages: set[str] = set()
        seen_message_inputs: set[str] = set()
        seen_context: set[tuple[str, str, str | None]] = set()
        for raw in candidate.source_refs:
            if isinstance(raw, ProvenanceRef):
                ref = raw
            elif isinstance(raw, Mapping):
                try:
                    kind = raw.get("kind")
                    value = raw.get("value")
                    content_hash = raw.get("content_hash")
                    if not isinstance(kind, str) or not isinstance(value, str) or not value.strip() or (content_hash is not None and not isinstance(content_hash, str)):
                        raise ValueError("invalid typed provenance")
                    ref = ProvenanceRef(kind, value, content_hash)
                except ValueError:
                    self._provenance_errors.append("provenance_typed_invalid")
                    continue
            else:
                ref = ProvenanceRef("message", str(raw).strip())
            if ref.kind == "message":
                if ref.value in seen_message_inputs:
                    self._provenance_errors.append("provenance_duplicate_message")
                    continue
                seen_message_inputs.add(ref.value)
                resolver = getattr(store, "resolve_exact_message_ref", None) if store is not None else None
                if not callable(resolver):
                    context.append(ProvenanceRef("evidence", ref.value, ref.content_hash))
                    continue
                try:
                    item = resolver(ref.value, content_hash=ref.content_hash)
                except Exception as exc:
                    message = str(exc)
                    if "ambiguous" in message:
                        self._provenance_errors.append("provenance_ambiguous_message")
                    elif "mismatch" in message:
                        self._provenance_errors.append("provenance_content_hash_mismatch")
                    else:
                        self._provenance_errors.append("provenance_unknown_message")
                    continue
                if item.message_id in seen_messages:
                    self._provenance_errors.append("provenance_duplicate_message")
                    continue
                seen_messages.add(item.message_id)
                resolved.append(item)
            elif ref.kind == "event":
                event = self.state_db.get_event(ref.value) if hasattr(self.state_db, "get_event") else None
                payload = self._payload(event or {})
                identity = payload.get("message") if isinstance(payload.get("message"), Mapping) else payload
                message_id = identity.get("message_id") if isinstance(identity, Mapping) else None
                message_hash = identity.get("content_hash") if isinstance(identity, Mapping) else None
                if message_id and message_hash and store is not None:
                    try:
                        item = store.resolve_exact_message_ref(str(message_id), content_hash=str(message_hash))
                    except Exception:
                        self._provenance_errors.append("provenance_event_invalid")
                        continue
                    if item.message_id not in seen_messages:
                        seen_messages.add(item.message_id)
                        resolved.append(item)
                    else:
                        self._provenance_errors.append("provenance_duplicate_message")
                else:
                    self._provenance_errors.append("provenance_event_invalid")
                    continue
            else:
                key = (ref.kind, ref.value, ref.content_hash)
                if key not in seen_context:
                    seen_context.add(key)
                    context.append(ref)
        return ResolvedProvenance(tuple(resolved), tuple(context))

    def _claim_lease(self, decision_id: str) -> bool:
        claim = getattr(self.state_db, "claim_promotion_lease", None)
        return bool(claim(decision_id, self._operation_owner)) if callable(claim) else True

    def _release_lease(self, decision_id: str) -> None:
        release = getattr(self.state_db, "release_promotion_lease", None)
        if callable(release):
            release(decision_id, self._operation_owner)

    def _record_promotion_event(self, event_type: str, candidate: ReviewCandidate, decision_id: str, provenance: ResolvedProvenance) -> str | None:
        recorder = getattr(self.state_db, "record_promotion_event_once", None)
        if not callable(recorder):
            return None
        payload = {
            "candidate_id": candidate.memory_id, "decision_id": decision_id, "memory_id": candidate.memory_id,
            "content_hash": candidate.content_hash, "policy_version": self.policy_version,
            "state": PromotionProjectionState.PREPARING.value if event_type.endswith("preparing") else PromotionProjectionState.VISIBLE_ACTIVE.value,
            "messages": [{"message_id": ref.message_id, "content_hash": ref.content_hash, "external_key": {"source_external_id": ref.external_key.source_external_id, "conversation_external_id": ref.external_key.conversation_external_id, "message_external_id": ref.external_key.message_external_id}} for ref in sorted(provenance.linkable_messages, key=lambda x: x.message_id)],
        }
        return recorder(decision_id, event_type, candidate.memory_id, payload)

    def _record_terminal(self, candidate: ReviewCandidate, decision_id: str, event_type: str, provenance: ResolvedProvenance) -> str | None:
        recorder = getattr(self.state_db, "record_promotion_event_once", None)
        if not callable(recorder):
            return None
        state = {"memory_projection_activated": "active", "memory_projection_rolled_back": "rolled_back", "memory_projection_repair_required": "repair_required"}[event_type]
        return recorder(decision_id, event_type, candidate.memory_id, {"candidate_id": candidate.memory_id, "decision_id": decision_id, "memory_id": candidate.memory_id, "content_hash": candidate.content_hash, "policy_version": self.policy_version, "state": state, "messages": [{"message_id": ref.message_id, "content_hash": ref.content_hash, "external_key": {"source_external_id": ref.external_key.source_external_id, "conversation_external_id": ref.external_key.conversation_external_id, "message_external_id": ref.external_key.message_external_id}} for ref in sorted(provenance.linkable_messages, key=lambda x: x.message_id)]})

    def _terminal_type_for_evidence(self) -> str:
        state = self._last_promotion_evidence.get("state")
        if state == PromotionProjectionState.VISIBLE_ACTIVE.value:
            return "memory_projection_activated"
        if state == PromotionProjectionState.ROLLED_BACK.value:
            return "memory_projection_rolled_back"
        return "memory_projection_repair_required"

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
        elif not any(self._evidence_verifiable(ref, candidate) for ref in refs):
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
        return tuple(
            (item.value if isinstance(item, ProvenanceRef) else str(item).strip())
            for item in candidate.source_refs
            if (item.value if isinstance(item, ProvenanceRef) else str(item).strip())
        )

    def _message_primary_refs(self, candidate: ReviewCandidate) -> tuple[str, ...]:
        """Only exact SourceReadModel message primary IDs may receive links."""
        store = self.evidence_store
        resolver = getattr(store, "resolve_message_refs", None) if store is not None else None
        if callable(resolver):
            try:
                return tuple(str(item) for item in resolver(self._evidence_refs(candidate)))
            except Exception:
                return ()
        getter = getattr(store, "get_message", None) if store is not None else None
        if not callable(getter):
            return ()
        resolved: list[str] = []
        for reference in self._evidence_refs(candidate):
            try:
                row = getter(reference, include_content=False)
            except Exception:
                row = None
            if row is not None and str(row.get("message_id") or "") == reference:
                resolved.append(reference)
        return tuple(dict.fromkeys(resolved))

    def _evidence_verifiable(self, reference: str, candidate: ReviewCandidate) -> bool:
        """Resolve evidence through existing state/source read models only."""
        wanted = str(reference).strip()
        if not wanted:
            return False
        # Typed event references are verifiable by their durable event identity;
        # they must not be mistaken for a message primary key merely because
        # the public evidence_refs projection contains their value.
        for item in candidate.source_refs:
            if isinstance(item, ProvenanceRef) and item.kind == "event" and item.value == wanted:
                getter = getattr(self.state_db, "get_event", None)
                return callable(getter) and getter(wanted) is not None
        metadata = dict(candidate.metadata)
        candidate_owned = {
            str(candidate.memory_id).strip(),
            str(candidate.content_hash).strip(),
            str(metadata.get("candidate_id") or "").strip(),
            str(metadata.get("decision_id") or "").strip(),
            str(metadata.get("promotion_id") or "").strip(),
        }
        candidate_owned.discard("")
        if wanted in candidate_owned:
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
            resolver = getattr(store, "resolve_message_refs", None)
            if callable(resolver):
                try:
                    resolver((wanted,))
                    return True
                except Exception:
                    return False
            for method_name in ("get_source", "get_conversation", "get_message"):
                method = getattr(store, method_name, None)
                if callable(method):
                    try:
                        try:
                            found = method(wanted)
                        except TypeError:
                            # SourceReadModel.get_message requires an explicit
                            # content flag; provenance verification only needs
                            # identity and must not read message bodies.
                            found = method(wanted, include_content=False)
                        if found is not None:
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

    def reconcile_incomplete_projections(self) -> tuple[PromotionEvidence, ...]:
        """Repair durable promotion sagas after a process interruption."""
        output: list[PromotionEvidence] = []
        starts = [row for row in self.state_db.recent_events(limit=100000) if row.get("event_type") == "memory_promotion_preparing"]
        for row in starts:
            payload = self._payload(row)
            decision_id = str(payload.get("decision_id") or "")
            memory_id = str(payload.get("memory_id") or row.get("entity_id") or "")
            if not decision_id or not memory_id or not self._claim_lease(decision_id):
                continue
            refs: list[Any] = []
            for item in payload.get("messages") or ():
                if not isinstance(item, Mapping) or not item.get("message_id"):
                    continue
                try:
                    resolved = self.evidence_store.resolve_exact_message_ref(str(item["message_id"]), content_hash=str(item.get("content_hash") or ""))
                    external = item.get("external_key")
                    if isinstance(external, Mapping):
                        expected_external = (
                            str(external.get("source_external_id") or ""),
                            str(external.get("conversation_external_id") or ""),
                            str(external.get("message_external_id") or ""),
                        )
                        actual_external = (
                            resolved.external_key.source_external_id,
                            resolved.external_key.conversation_external_id,
                            resolved.external_key.message_external_id,
                        )
                        if expected_external != actual_external:
                            continue
                    refs.append(resolved)
                except Exception:
                    continue
            document = self.memory_db.fetch_memory(memory_id, include_chunks=False) if self.memory_db is not None else None
            terminal = {str(self._payload(item).get("state") or "") for item in self.state_db.recent_events(limit=100000) if item.get("event_type") in {"memory_projection_activated", "memory_projection_rolled_back", "memory_projection_repair_required"} and str(self._payload(item).get("decision_id") or "") == decision_id}
            candidate_stub = ReviewCandidate(memory_id=memory_id, title="", content="", content_hash=str(payload.get("content_hash") or ""))
            if "repair_required" in terminal:
                output.append(PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.REPAIR_REQUIRED, tuple(refs), ( ), False, error_codes=("repair_required",)))
                self._release_lease(decision_id)
                continue
            try:
                if document is None:
                    event_id = self._record_terminal(candidate_stub, decision_id, "memory_projection_rolled_back", ResolvedProvenance(tuple(refs), ()))
                    evidence = PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.ROLLED_BACK, tuple(refs), terminal_event_id=event_id, rollback_verified=True)
                elif document.get("status") == "active":
                    sound = bool(refs) and bool(self.evidence_store) and self.evidence_store.verify_message_memory_links(tuple(refs), memory_id, decision_id=decision_id)
                    if not sound:
                        self.memory_db.mark_repair_required(memory_id, decision_id=decision_id)
                        if "active" in terminal:
                            raise RuntimeError("promotion_repair_terminal_conflict")
                        event_id = self._record_terminal(candidate_stub, decision_id, "memory_projection_repair_required", ResolvedProvenance(tuple(refs), ()))
                        evidence = PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.REPAIR_REQUIRED, tuple(refs), terminal_event_id=event_id, error_codes=("promotion_provenance_incomplete",))
                    elif "active" not in terminal:
                        event_id = self._record_terminal(candidate_stub, decision_id, "memory_projection_activated", ResolvedProvenance(tuple(refs), ()))
                        evidence = PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.VISIBLE_ACTIVE, tuple(refs), terminal_event_id=event_id)
                    else:
                        evidence = PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.VISIBLE_ACTIVE, tuple(refs))
                elif document.get("status") == "preparing" and refs and self.evidence_store.verify_message_memory_links(tuple(refs), memory_id, decision_id=decision_id):
                    self.memory_db.activate_derived_projection(memory_id, decision_id=decision_id, required_messages=tuple(refs))
                    event_id = self._record_terminal(candidate_stub, decision_id, "memory_projection_activated", ResolvedProvenance(tuple(refs), ()))
                    evidence = PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.VISIBLE_ACTIVE, tuple(refs), terminal_event_id=event_id)
                elif document.get("status") == "preparing":
                    self.evidence_store.unlink_message_memory_batch(tuple(refs), memory_id, decision_id=decision_id)
                    cleaned = self.memory_db.remove_preparing_projection(memory_id, decision_id=decision_id)
                    if not cleaned:
                        raise RuntimeError("promotion_cleanup_unverified")
                    event_id = self._record_terminal(candidate_stub, decision_id, "memory_projection_rolled_back", ResolvedProvenance(tuple(refs), ()))
                    evidence = PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.ROLLED_BACK, tuple(refs), terminal_event_id=event_id, rollback_verified=True)
                else:
                    raise RuntimeError("promotion_state_unreconciled")
            except Exception as exc:
                terminal_event_id = None
                error_codes = ["promotion_repair_required"]
                try:
                    terminal_event_id = self._record_terminal(candidate_stub, decision_id, "memory_projection_repair_required", ResolvedProvenance(tuple(refs), ()))
                except Exception:
                    error_codes.extend(("promotion_repair_terminal_conflict", "reconcile_unreconciled"))
                evidence = PromotionEvidence(memory_id, decision_id, memory_id, PromotionProjectionState.REPAIR_REQUIRED, tuple(refs), terminal_event_id=terminal_event_id, error_codes=tuple(error_codes))
            output.append(evidence)
            self._release_lease(decision_id)
        return tuple(output)

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
        # The only production path is prepare -> one transactional source-link
        # batch -> activation.  A custom writer remains a compatibility seam
        # for OFF/SHADOW tests and cannot claim provenance visibility.
        provenance = self._normalize_provenance(candidate)
        writer = self.projection_writer
        if writer is None and self.memory_db is not None:
            writer = getattr(self.memory_db, "prepare_derived_projection", None)
        if writer is None:
            raise RuntimeError("derived projection writer is unavailable")
        if not provenance.linkable_messages:
            raise RuntimeError("structured_message_provenance_required")
        if self.memory_db is not None and self.evidence_store is not None:
            if Path(getattr(self.memory_db, "path", "")).resolve() != Path(getattr(self.evidence_store, "path", "")).resolve():
                raise RuntimeError("promotion_database_path_mismatch")
        kwargs = {
            "memory_id": candidate.memory_id,
            "title": candidate.title,
            "content": candidate.content,
            "content_hash": candidate.content_hash,
            "evidence_refs": list(provenance.context_only_refs) + [ProvenanceRef("message", item.message_id, item.content_hash) for item in provenance.linkable_messages],
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
        if self.evidence_store is None:
            self._last_promotion_evidence = {"candidate_id": candidate.memory_id, "decision_id": decision_id, "memory_id": candidate.memory_id, "state": PromotionProjectionState.VISIBLE_ACTIVE.value, "resolved_message_primary_ids": [x.message_id for x in provenance.linkable_messages]}
            return result
        if self.projection_writer is not None:
            self._last_promotion_evidence = {"candidate_id": candidate.memory_id, "decision_id": decision_id, "memory_id": candidate.memory_id, "state": PromotionProjectionState.VISIBLE_ACTIVE.value, "resolved_message_primary_ids": [x.message_id for x in provenance.linkable_messages], "created_link_ids": [], "reused_link_ids": [], "rollback_verified": False, "error_codes": []}
            return result
        linker = getattr(self.evidence_store, "link_message_memory_batch", None)
        activator = getattr(self.memory_db, "activate_derived_projection", None)
        if not callable(linker) or not callable(activator):
            raise RuntimeError("promotion_atomic_interfaces_unavailable")
        batch = None
        try:
            batch = linker(provenance.linkable_messages, candidate.memory_id, decision_id=decision_id, confidence=candidate.confidence)
            if not self.evidence_store.verify_message_memory_links(provenance.linkable_messages, candidate.memory_id, decision_id=decision_id):
                raise RuntimeError("promotion_provenance_verification_failed")
            activator(candidate.memory_id, decision_id=decision_id, required_messages=provenance.linkable_messages)
        except Exception as exc:
            # A provider may commit activation and then lose the process
            # before returning. Preserve the durable active projection so
            # reconciliation can append the missing terminal event.
            try:
                current = self.memory_db.fetch_memory(candidate.memory_id, include_chunks=False)
                if isinstance(current, Mapping) and current.get("status") == PromotionProjectionState.VISIBLE_ACTIVE.value and self.evidence_store.verify_message_memory_links(provenance.linkable_messages, candidate.memory_id, decision_id=decision_id):
                    self._last_promotion_evidence = {
                        "candidate_id": candidate.memory_id, "decision_id": decision_id, "memory_id": candidate.memory_id,
                        "state": PromotionProjectionState.VISIBLE_ACTIVE.value,
                        "resolved_message_primary_ids": [x.message_id for x in provenance.linkable_messages],
                        "created_link_ids": [x.message_id for x in (batch.created_messages if batch else ())],
                        "reused_link_ids": [x.message_id for x in (batch.reused_messages if batch else ())],
                        "rollback_verified": False, "error_codes": ["promotion_terminal_event_pending"],
                    }
                    raise
            except Exception:
                if self._last_promotion_evidence.get("state") == PromotionProjectionState.VISIBLE_ACTIVE.value:
                    raise
            removed = ()
            try:
                removed = self.evidence_store.unlink_message_memory_batch(provenance.linkable_messages, candidate.memory_id, decision_id=decision_id)
                cleaned = bool(self.memory_db.remove_preparing_projection(candidate.memory_id, decision_id=decision_id))
                verified = self.memory_db.fetch_memory(candidate.memory_id, include_chunks=False) is None
            except Exception:
                cleaned, verified = False, False
            state = PromotionProjectionState.ROLLED_BACK if cleaned and verified else PromotionProjectionState.REPAIR_REQUIRED
            self._last_promotion_evidence = {"candidate_id": candidate.memory_id, "decision_id": decision_id, "memory_id": candidate.memory_id, "state": state.value, "removed_link_ids": [x.message_id for x in removed], "rollback_verified": bool(cleaned and verified), "error_codes": ["promotion_persist_failed"]}
            raise
        self._last_promotion_evidence = {
            "candidate_id": candidate.memory_id, "decision_id": decision_id, "memory_id": candidate.memory_id,
            "state": PromotionProjectionState.VISIBLE_ACTIVE.value,
            "resolved_message_primary_ids": [x.message_id for x in provenance.linkable_messages],
            "created_link_ids": [x.message_id for x in batch.created_messages],
            "reused_link_ids": [x.message_id for x in batch.reused_messages],
            "rollback_verified": False, "error_codes": [],
        }
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
        if self._last_promotion_evidence:
            result["promotion_evidence"] = dict(self._last_promotion_evidence)
        return result

    @staticmethod
    def _candidate_payload(candidate: ReviewCandidate) -> dict[str, Any]:
        payload = asdict(candidate)
        payload["project_ids"] = list(candidate.project_ids)
        payload["source_refs"] = [
            item.to_dict() if isinstance(item, ProvenanceRef) else item
            for item in candidate.source_refs
        ]
        payload["risk_flags"] = list(candidate.risk_flags)
        payload["structured_content"] = dict(candidate.structured_content)
        payload["candidate_id"] = candidate.memory_id
        payload["evidence_refs"] = list(payload["source_refs"])
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
        safe_recorder = getattr(self.state_db, "append_promotion_event", None)
        if callable(safe_recorder):
            safe_recorder(event_type, entity_id, dict(payload))
            return
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
