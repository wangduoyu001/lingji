from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

from src.gateway.profiles import AIProfileRegistry

from .read_model import SourceReadModel


@dataclass(frozen=True)
class ViewerContext:
    viewer_scope: str
    agent_id: str | None
    allowed_privacy: tuple[str, ...]
    owner: bool


class SourceQueryService:
    """Workspace-aware, permission-aware queries over the derived source index."""

    def __init__(
        self,
        read_model: SourceReadModel,
        *,
        workspace: str,
        vault_path: Path | str,
        raw_path: Path | str,
        profiles: AIProfileRegistry | None = None,
    ):
        self.read_model = read_model
        self.workspace = str(workspace or "production")
        self.vault_path = Path(vault_path).expanduser().resolve(strict=False)
        self.raw_path = Path(raw_path).expanduser().resolve(strict=False)
        self.profiles = profiles or AIProfileRegistry()

    def owner_viewer(self) -> ViewerContext:
        return ViewerContext(
            viewer_scope="owner",
            agent_id="lingji-local",
            allowed_privacy=("public", "private", "restricted"),
            owner=True,
        )

    def agent_viewer(self, agent_id: str) -> ViewerContext:
        profile = self.profiles.get(agent_id)
        return ViewerContext(
            viewer_scope="agent",
            agent_id=profile.agent_id,
            allowed_privacy=profile.allowed_privacy,
            owner=False,
        )

    def status(self, viewer: ViewerContext | None = None) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        return self._envelope(
            {
                "state": "healthy",
                "schema_version": self.read_model.schema_version(),
                **self.read_model.stats(),
            },
            selected,
        )

    def list_sources(
        self,
        *,
        viewer: ViewerContext | None = None,
        source_type: str | None = None,
        privacy: str | None = None,
        project: str | None = None,
        status: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        page = self.read_model.list_sources(
            source_type=source_type,
            privacy=self._privacy_filter(selected, privacy),
            project=project,
            status=status,
            q=q,
            agent_id=selected.agent_id,
            owner=selected.owner,
            limit=limit,
            offset=offset,
        )
        page["items"] = [self._safe_source(item) for item in page["items"]]
        return self._envelope(page, selected)

    def get_source(
        self, source_id: str, *, viewer: ViewerContext | None = None
    ) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        item = self.read_model.get_source(source_id)
        self._require_visible(item, selected, "source")
        return self._envelope({"item": self._safe_source(item or {})}, selected)

    def list_conversations(
        self,
        *,
        viewer: ViewerContext | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        privacy: str | None = None,
        project: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        page = self.read_model.list_conversations(
            source_id=source_id,
            source_type=source_type,
            privacy=self._privacy_filter(selected, privacy),
            project=project,
            from_time=from_time,
            to_time=to_time,
            q=q,
            agent_id=selected.agent_id,
            owner=selected.owner,
            limit=limit,
            offset=offset,
        )
        page["items"] = [self._safe_conversation(item) for item in page["items"]]
        return self._envelope(page, selected)

    def get_conversation(
        self, conversation_id: str, *, viewer: ViewerContext | None = None
    ) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        item = self.read_model.get_conversation(conversation_id)
        self._require_visible(item, selected, "conversation")
        return self._envelope({"item": self._safe_conversation(item or {})}, selected)

    def list_messages(
        self,
        *,
        viewer: ViewerContext | None = None,
        conversation_id: str | None = None,
        source_id: str | None = None,
        role: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        page = self.read_model.list_messages(
            conversation_id=conversation_id,
            source_id=source_id,
            role=role,
            privacy=selected.allowed_privacy,
            from_time=from_time,
            to_time=to_time,
            q=q,
            agent_id=selected.agent_id,
            owner=selected.owner,
            limit=limit,
            offset=offset,
        )
        page["items"] = [self._safe_message(item, include_content=False) for item in page["items"]]
        return self._envelope(page, selected)

    def get_message(
        self, message_id: str, *, viewer: ViewerContext | None = None
    ) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        item = self.read_model.get_message(message_id, include_content=True)
        self._require_visible(item, selected, "message")
        return self._envelope(
            {
                "item": self._safe_message(item or {}, include_content=True),
                "memory_links": self.read_model.message_links(message_id),
            },
            selected,
        )

    def memory_sources(
        self, memory_id: str, *, viewer: ViewerContext | None = None
    ) -> dict[str, Any]:
        selected = viewer or self.owner_viewer()
        links = []
        for link in self.read_model.memory_links(memory_id):
            message = self.read_model.get_message(str(link["message_id"]), include_content=False)
            if not self._is_visible(message, selected):
                continue
            links.append({**link, "content_preview": str(link.get("content_preview") or "")})
        return self._envelope({"memory_id": memory_id, "links": links}, selected)

    @staticmethod
    def _privacy_filter(viewer: ViewerContext, requested: str | None) -> tuple[str, ...]:
        if not requested:
            return viewer.allowed_privacy
        if requested not in viewer.allowed_privacy:
            return ("__denied__",)
        return (requested,)

    def _require_visible(
        self, item: dict[str, Any] | None, viewer: ViewerContext, entity: str
    ) -> None:
        if item is None:
            raise LookupError(f"{entity} not found")
        if not self._is_visible(item, viewer):
            raise PermissionError(f"{entity} is not visible to {viewer.agent_id or viewer.viewer_scope}")

    @staticmethod
    def _is_visible(item: dict[str, Any] | None, viewer: ViewerContext) -> bool:
        if not item or item.get("privacy") not in viewer.allowed_privacy:
            return False
        if viewer.owner:
            return True
        scopes = list(item.get("agent_scope") or [])
        return not scopes or "all" in scopes or viewer.agent_id in scopes

    def _safe_source(self, item: dict[str, Any]) -> dict[str, Any]:
        result = dict(item)
        result["raw_reference"] = self._safe_reference(result.get("raw_reference"))
        result["vault_reference"] = self._safe_reference(result.get("vault_reference"))
        result["metadata"] = self._safe_metadata(result.get("metadata") or {})
        return result

    def _safe_conversation(self, item: dict[str, Any]) -> dict[str, Any]:
        result = dict(item)
        result["metadata"] = self._safe_metadata(result.get("metadata") or {})
        return result

    def _safe_message(self, item: dict[str, Any], *, include_content: bool) -> dict[str, Any]:
        result = dict(item)
        result["raw_reference"] = self._safe_reference(result.get("raw_reference"))
        result["metadata"] = self._safe_metadata(result.get("metadata") or {})
        if not include_content:
            result.pop("content", None)
        return result

    def _safe_reference(self, value: Any) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        if text.startswith(("raw:", "vault:")):
            return text
        if text.startswith(("http://", "https://")):
            return text
        if "://" in text:
            return None
        path = Path(text).expanduser()
        if not path.is_absolute() and not PureWindowsPath(text).is_absolute():
            return path.as_posix()
        resolved = path.resolve(strict=False)
        for label, root in (("raw", self.raw_path), ("vault", self.vault_path)):
            try:
                return f"{label}:{resolved.relative_to(root).as_posix()}"
            except ValueError:
                continue
        return None

    def _safe_metadata(self, value: Any) -> Any:
        if isinstance(value, dict):
            output = {}
            for key, item in value.items():
                lowered = str(key).casefold()
                if any(token in lowered for token in ("token", "api_key", "apikey", "password", "cookie", "secret")):
                    continue
                if isinstance(item, str) and (
                    lowered.endswith(("path", "reference", "_ref"))
                    or Path(item).is_absolute()
                    or PureWindowsPath(item).is_absolute()
                ):
                    output[key] = self._safe_reference(item)
                else:
                    output[key] = self._safe_metadata(item)
            return output
        if isinstance(value, list):
            return [self._safe_metadata(item) for item in value]
        return value

    def _envelope(self, payload: dict[str, Any], viewer: ViewerContext) -> dict[str, Any]:
        return {
            "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "workspace": self.workspace,
            "viewer_scope": viewer.viewer_scope,
            "viewer_agent_id": viewer.agent_id,
            **payload,
        }
