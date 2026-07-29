from __future__ import annotations

from typing import Any

from src.assistant_hub import AiAssistantDiscoveryService


def register_assistant_hub_routes(
    app: Any,
    settings: Any,
    *,
    dependencies: list[Any],
) -> None:
    workspace = str(getattr(settings, "workspace", "") or "")

    def discovery() -> AiAssistantDiscoveryService:
        return AiAssistantDiscoveryService(workspace=workspace)

    @app.get("/api/assistant-hub/status", dependencies=dependencies)
    def assistant_hub_status() -> dict[str, Any]:
        return discovery().scan()

    @app.post("/api/assistant-hub/scan", dependencies=dependencies)
    def assistant_hub_scan() -> dict[str, Any]:
        return discovery().scan()
