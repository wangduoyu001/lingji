from __future__ import annotations

"""Canonical persistent identity helpers for extraction jobs.

This module is the single source of truth for extraction idempotency material.
It intentionally contains no queue state or worker behavior.
"""

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = 1


def _normalize(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, set | frozenset):
        return sorted(_normalize(item) for item in value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_extraction_idempotency_key(
    *,
    source_type: str,
    adapter_name: str,
    adapter_version: str,
    input_identity: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    effective_options: Mapping[str, Any] | None = None,
) -> str:
    material = {
        "schema_version": SCHEMA_VERSION,
        "source_type": source_type,
        "adapter": {
            "name": adapter_name,
            "version": adapter_version,
        },
        "input_identity": input_identity or {},
        "payload": payload or {},
        "effective_options": effective_options or {},
    }
    return sha256_bytes(canonical_json_bytes(material))
