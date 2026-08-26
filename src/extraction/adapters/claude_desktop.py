"""Claude Desktop boundary.

Claude Desktop's opaque application storage is intentionally not an extraction
input.  Until an explicit official export contract exists this adapter only
reports capability and never opens an application path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from src.automatic_memory.models import AuthorizationScope

from ..base import ExtractionAdapter
from ..models import ExtractionBatch, ExtractionRequest
from .generic_ai_history import CapabilityStatus


class ClaudeDesktopAdapter(ExtractionAdapter):
    name = "claude_desktop"
    version = "1.0.0"
    approved = True
    source_types = ("claude_desktop",)

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        del input_path, payload
        return False if source_type in self.source_types else False

    def capability(self, scope: AuthorizationScope) -> CapabilityStatus:
        if "claude_desktop" not in scope.source_kinds or not scope.owner_confirmed:
            return CapabilityStatus(
                "claude_desktop",
                "consent_required",
                "owner confirmation for Claude Desktop is required",
            )
        return CapabilityStatus(
            "claude_desktop",
            "unsupported",
            "Claude Desktop has no approved official export schema; opaque storage is not read",
        )

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        del request
        raise PermissionError(
            "Claude Desktop extraction is unsupported until an official export schema is approved"
        )


__all__ = ["ClaudeDesktopAdapter"]
