from __future__ import annotations

from typing import Any

from .connectors import AiMemoryConnectorService as ConnectorCore


class AiMemoryConnectorService(ConnectorCore):
    """Public connector service with secret-free preview responses.

    The connector core may build a complete copy payload internally, but the
    authenticated control API must not return it before the owner confirms the
    apply action. WorkBuddy receives the complete payload only from ``apply``.
    """

    def preview(self, connector_id: str) -> dict[str, Any]:
        payload = super().preview(connector_id)
        payload.pop("copy_payload", None)
        return payload
