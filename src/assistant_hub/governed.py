from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .connectors import AiMemoryConnectorService as ConnectorCore
from .connectors import Runner


class _ExplicitEnvironment(dict[str, str]):
    """Keep an explicitly supplied empty environment distinct from ``None``.

    The connector core preserves legacy behaviour by inheriting ``os.environ``
    when no environment is supplied.  A caller that deliberately passes an
    empty mapping must remain isolated from machine-level variables such as
    ``CODEX_HOME``.  Making the temporary mapping truthy lets the core copy it
    without falling back to the process environment.
    """

    def __bool__(self) -> bool:
        return True


class AiMemoryConnectorService(ConnectorCore):
    """Public owner-governed connector service.

    Besides removing secret-bearing preview fields, this public boundary keeps
    explicit test and acceptance environments isolated from the owner's real
    Codex and Claude configuration.
    """

    def __init__(
        self,
        *,
        storage_path: Path | str,
        home: Path | str | None = None,
        env: Mapping[str, str] | None = None,
        runner: Runner | None = None,
        timeout_seconds: float = 12.0,
    ) -> None:
        isolated_env = None if env is None else _ExplicitEnvironment(env)
        super().__init__(
            storage_path=storage_path,
            home=home,
            env=isolated_env,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )

    def preview(self, connector_id: str) -> dict[str, Any]:
        payload = super().preview(connector_id)
        payload.pop("copy_payload", None)
        return payload
