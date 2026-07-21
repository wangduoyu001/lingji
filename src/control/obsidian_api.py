from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field


class ObsidianValidateRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


def register_obsidian_routes(
    app: Any,
    control: Any,
    *,
    dependencies: list[Any],
    translate_error: Callable[[Exception], Exception],
) -> None:
    """Register authenticated Obsidian status and configuration validation."""

    @app.get("/api/obsidian/status", dependencies=dependencies)
    def obsidian_status() -> dict[str, Any]:
        return control.obsidian_status()

    @app.post("/api/obsidian/validate", dependencies=dependencies)
    def validate_obsidian(request: ObsidianValidateRequest) -> dict[str, Any]:
        try:
            return control.validate_obsidian_settings(request.values)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/obsidian/refresh", dependencies=dependencies)
    def refresh_obsidian() -> dict[str, Any]:
        return control.obsidian_status()
