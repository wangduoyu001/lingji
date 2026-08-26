from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalMessageKey:
    source_external_id: str
    conversation_external_id: str
    message_external_id: str


@dataclass(frozen=True)
class ResolvedMessageRef:
    message_id: str
    external_key: ExternalMessageKey
    content_hash: str
