"""Isolated scale-fixture and readiness helpers.

The actual 100k run remains opt-in and is never performed while functional
quality is unavailable.  This module deliberately has no product imports.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .quality_evidence import EvidenceState, QualityEvidenceReadiness
from src.extraction.adapters.generic_ai_history import HISTORY_SCHEMA, HISTORY_VERSION


def readiness_from_envelope(path: Path) -> QualityEvidenceReadiness:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        raw = payload.get("quality_evidence_readiness")
        if not isinstance(raw, Mapping):
            raise ValueError
        values: dict[str, EvidenceState] = {}
        fields = QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",)
        for field in fields:
            value = raw.get(field)
            if isinstance(value, EvidenceState):
                values[field] = value
            elif isinstance(value, str):
                values[field] = EvidenceState(value.removeprefix("EvidenceState.").lower())
            else:
                raise ValueError
        result = QualityEvidenceReadiness(**values)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("BLOCKED_4R2_REQUIRED") from exc
    if not result.functional_ready:
        raise ValueError("BLOCKED_4R2_REQUIRED")
    return result


def generate_history_fixture(path: Path, *, count: int = 100_000, seed: int = 41041) -> dict[str, Any]:
    """Generate and measure a deterministic fixture; small counts are test-only."""
    if type(count) is not int or count <= 0:
        raise ValueError("scale fixture count must be a positive integer")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    ids: set[str] = set()
    hashes: set[str] = set()
    rows = 0
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        header = {"schema": HISTORY_SCHEMA, "schema_version": HISTORY_VERSION, "type": "header", "seed": seed}
        conversation = {"type": "conversation", "conversation_id": "scale-conversation", "title": "Scale benchmark"}
        for value in (header, conversation):
            encoded = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
            digest.update(encoded)
            stream.write(encoded.decode("utf-8"))
        for index in range(count):
            message_id = f"scale-message-{index:06d}"
            content = f"Deterministic scale message {index:06d} seed {seed}."
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            row = {
                "type": "message", "conversation_id": "scale-conversation",
                "message_id": message_id, "role": "user" if index % 2 == 0 else "assistant",
                "content": content, "content_hash": content_hash,
                "timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat().replace("+00:00", "Z"),
            }
            encoded = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
            digest.update(encoded)
            stream.write(encoded.decode("utf-8"))
            rows += 1; ids.add(message_id); hashes.add(content_hash)
    if rows != count or len(ids) != count or len(hashes) != count:
        raise ValueError("scale fixture identity validation failed during generation")
    return {"seed": seed, "messages": count, "message_rows": rows,
            "unique_message_ids": len(ids), "unique_content_hashes": len(hashes),
            "fixture_sha256": digest.hexdigest(), "content_hash": digest.hexdigest(),
            "path": str(path)}


def validate_history_fixture(path: Path, *, expected_count: int, expected_seed: int) -> dict[str, Any]:
    digest = hashlib.sha256(); ids: set[str] = set(); hashes: set[str] = set(); rows = 0
    with Path(path).open("rb") as stream:
        for raw in stream:
            digest.update(raw); value = json.loads(raw.decode("utf-8"))
            if value.get("type") != "message":
                continue
            rows += 1; message_id = value.get("message_id"); content = value.get("content")
            content_hash = value.get("content_hash")
            if not isinstance(message_id, str) or not message_id or not isinstance(content, str) or not content:
                raise ValueError("scale fixture contains invalid identity/content")
            if content_hash != hashlib.sha256(content.encode("utf-8")).hexdigest():
                raise ValueError("scale fixture content hash mismatch")
            ids.add(message_id); hashes.add(content_hash)
    if rows != expected_count or len(ids) != expected_count or len(hashes) != expected_count:
        raise ValueError("scale fixture persisted identity counts do not match")
    return {"message_rows": rows, "unique_message_ids": len(ids),
            "unique_content_hashes": len(hashes), "fixture_sha256": digest.hexdigest(),
            "seed": expected_seed}


__all__ = ["readiness_from_envelope", "generate_history_fixture", "validate_history_fixture"]
