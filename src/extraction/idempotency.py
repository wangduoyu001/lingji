from __future__ import annotations

"""Canonical persistent identity helpers for extraction jobs.

This module is the single source of truth for extraction idempotency material.
It intentionally contains no queue state or worker behavior.
"""

import hashlib
import json
import os
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
_HASH_CHUNK_BYTES = 1024 * 1024


def _normalize(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, datetime):
        normalized = value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (set, frozenset)):
        normalized = [_normalize(item) for item in value]
        return sorted(normalized, key=lambda item: canonical_json_bytes(item))
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported idempotency value type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path | str, *, chunk_bytes: int = _HASH_CHUNK_BYTES) -> str:
    selected = Path(path).expanduser()
    if not selected.exists():
        raise FileNotFoundError(selected)
    if not selected.is_file():
        raise ValueError(f"Expected a file for idempotency hashing: {selected}")
    digest = hashlib.sha256()
    with selected.open("rb") as handle:
        for chunk in iter(lambda: handle.read(max(int(chunk_bytes), 1)), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_manifest(path: Path | str) -> list[dict[str, Any]]:
    root = Path(path).expanduser()
    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise ValueError(f"Expected a directory for manifest hashing: {root}")

    manifest: list[dict[str, Any]] = []
    for entry in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = entry.relative_to(root).as_posix()
        if entry.is_symlink():
            try:
                target = os.readlink(entry)
                target_hash = sha256_bytes(str(target).replace("\\", "/").encode("utf-8"))
            except OSError as exc:
                raise OSError(f"Unable to inspect symbolic link: {relative}") from exc
            manifest.append(
                {
                    "path": relative,
                    "kind": "symlink",
                    "target_sha256": target_hash,
                }
            )
            continue
        if not entry.is_file():
            continue
        stat = entry.stat()
        manifest.append(
            {
                "path": relative,
                "kind": "file",
                "size": int(stat.st_size),
                "sha256": sha256_file(entry),
            }
        )
    return manifest


def build_input_identity(input_path: Path | str | None) -> dict[str, Any]:
    if input_path is None or str(input_path).strip() == "":
        return {"kind": "payload"}
    selected = Path(input_path).expanduser()
    if not selected.exists():
        raise FileNotFoundError(selected)
    if selected.is_symlink():
        raise ValueError("Top-level symbolic-link inputs are not accepted for durable extraction identity")
    if selected.is_file():
        stat = selected.stat()
        return {
            "kind": "file",
            "size": int(stat.st_size),
            "content_sha256": sha256_file(selected),
        }
    if selected.is_dir():
        manifest = directory_manifest(selected)
        return {
            "kind": "directory",
            "entries": len(manifest),
            "manifest_sha256": sha256_bytes(canonical_json_bytes(manifest)),
        }
    raise ValueError(f"Unsupported extraction input type: {selected}")


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
        "source_type": str(source_type or "").strip().lower(),
        "adapter": {
            "name": str(adapter_name or "").strip(),
            "version": str(adapter_version or "").strip(),
        },
        "input_identity": dict(input_identity or {"kind": "payload"}),
        "payload": dict(payload or {}),
        "effective_options": dict(effective_options or {}),
    }
    return sha256_bytes(canonical_json_bytes(material))


def extraction_key_for_request(
    *,
    source_type: str,
    adapter_name: str,
    adapter_version: str,
    input_path: Path | str | None,
    payload: Mapping[str, Any] | None,
    effective_options: Mapping[str, Any] | None,
) -> str:
    return build_extraction_idempotency_key(
        source_type=source_type,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        input_identity=build_input_identity(input_path),
        payload=payload,
        effective_options=effective_options,
    )


def build_snapshot_idempotency_key(
    source_id: str, relative_path: str, sha256: str
) -> str:
    """Build the durable identity for one authorized source snapshot.

    Snapshot identity deliberately excludes absolute paths and timestamps so a
    repeated scan converges on the same extraction job after a restart.
    """

    relative = str(relative_path).replace("\\", "/").lstrip("/")
    material = {
        "schema_version": SCHEMA_VERSION,
        "kind": "automatic_memory_snapshot",
        "source_id": str(source_id),
        "relative_path": relative,
        "sha256": str(sha256).lower(),
    }
    return sha256_bytes(canonical_json_bytes(material))


__all__: Sequence[str] = (
    "SCHEMA_VERSION",
    "build_extraction_idempotency_key",
    "build_input_identity",
    "build_snapshot_idempotency_key",
    "canonical_json_bytes",
    "directory_manifest",
    "extraction_key_for_request",
    "sha256_bytes",
    "sha256_file",
)
