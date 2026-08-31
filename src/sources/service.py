from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path, PureWindowsPath
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

if TYPE_CHECKING:
    from src.gateway.profiles import AIProfileRegistry

from .read_model import SourceReadModel

_SENSITIVE_QUERY_KEYS = {
    "token",
    "access_token",
    "api_key",
    "apikey",
    "key",
    "secret",
    "signature",
    "sig",
    "credential",
    "authorization",
    "session",
    "cookie",
}
_SENSITIVE_REFERENCE_TOKENS = (
    "token",
    "credential",
    "authorization",
    "auth_metadata",
    "password",
    "cookie",
    "secret",
    "api_key",
    "apikey",
    "session",
    "signature",
)
_SENSITIVE_DISPLAY_TOKENS = frozenset(_SENSITIVE_REFERENCE_TOKENS) | frozenset(
    _SENSITIVE_QUERY_KEYS
)
_OWNER_DISPLAY_SENSITIVE_PATTERN = re.compile(
    r"(?<![a-z0-9_])(?:"
    + "|".join(re.escape(token) for token in sorted(_SENSITIVE_DISPLAY_TOKENS, key=len, reverse=True))
    + r")(?:\s*)(?:=|:)\s*",
    re.IGNORECASE,
)
_OWNER_SOURCE_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_OWNER_SOURCE_TYPES = frozenset(
    {
        "chatgpt",
        "chatgpt_export",
        "claude_desktop",
        "codex",
        "codex_history",
        "codex_report",
        "codex_rollout",
        "codex_session",
        "codex_transcript",
        "generic_ai_history",
        "history_inbox",
        "obsidian",
    }
)


@dataclass(frozen=True)
class ViewerContext:
    viewer_scope: str
    agent_id: str | None
    allowed_privacy: tuple[str, ...]
    owner: bool


@dataclass(frozen=True)
class EvidencePage:
    """A bounded, serializable page of linked source evidence."""

    as_of: str
    memory_id: str
    items: tuple[dict[str, Any], ...]
    pagination: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of,
            "memory_id": self.memory_id,
            "items": list(self.items),
            "pagination": dict(self.pagination),
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


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
        if profiles is None:
            from src.gateway.profiles import AIProfileRegistry

            profiles = AIProfileRegistry()
        self.profiles = profiles

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
        page["items"] = [
            self._safe_message(item, include_content=False) for item in page["items"]
        ]
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

    def memory_evidence(
        self,
        memory_id: str,
        *,
        viewer: ViewerContext | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        """Return visible linked messages with content for ContextPack only.

        The read model remains the sole source of structured evidence.  This
        method deliberately reuses the same viewer privacy/agent checks as the
        ordinary source APIs and applies the requested project scope to the
        message's inherited project list before exposing its body.
        """
        selected = viewer or self.owner_viewer()
        items: list[dict[str, Any]] = []
        for link in self.read_model.memory_links(memory_id):
            message_id = str(link.get("message_id") or "")
            message = self.read_model.get_message(message_id, include_content=True)
            if not self._is_visible(message, selected) or not self._matches_project(message, project):
                continue
            if not message:
                continue
            source = self.read_model.get_source(str(message.get("source_id") or "")) or {}
            conversation = self.read_model.get_conversation(str(message.get("conversation_id") or "")) or {}
            items.append(
                {
                    **link,
                    "source_id": message.get("source_id"),
                    "conversation_id": message.get("conversation_id"),
                    "message_id": message.get("message_id"),
                    "role": message.get("role"),
                    "occurred_at": message.get("occurred_at"),
                    "content": message.get("content") or "",
                    "content_hash": message.get("content_hash") or "",
                    "privacy": message.get("privacy"),
                    "project": message.get("projects") or [],
                    "agent_scope": message.get("agent_scope") or [],
                    "source_display_name": source.get("display_name"),
                    "conversation_title": conversation.get("title"),
                }
            )
        items.sort(
            key=lambda item: (
                str(item.get("occurred_at") or ""),
                str(item.get("source_id") or ""),
                str(item.get("conversation_id") or ""),
                str(item.get("message_id") or ""),
            )
        )
        return self._envelope({"memory_id": memory_id, "items": items}, selected)

    def list_memory_evidence_page(
        self,
        memory_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        include_content: bool = True,
        viewer: ViewerContext | None = None,
    ) -> EvidencePage:
        """Return a bounded page of visible linked messages.

        Link metadata is filtered and sorted before any message body is read.
        This keeps pagination deterministic while ensuring that a request can
        never cause an unbounded body read or bypass source authority.
        """
        selected = viewer or self.owner_viewer()
        selected_limit = int(limit)
        selected_offset = int(offset)
        if selected_limit < 1 or selected_limit > 50:
            raise ValueError("limit must be between 1 and 50")
        if selected_offset < 0:
            raise ValueError("offset must be greater than or equal to zero")

        visible: list[dict[str, Any]] = []
        for link in self.read_model.memory_links(str(memory_id)):
            message_id = str(link.get("message_id") or "").strip()
            if not message_id:
                continue
            message = self.read_model.get_message(message_id, include_content=False)
            if not self._is_visible(message, selected) or message is None:
                continue
            source = self.read_model.get_source(str(message.get("source_id") or ""))
            if not self._is_authoritative_source(source, selected):
                continue
            conversation = self.read_model.get_conversation(
                str(message.get("conversation_id") or "")
            )
            if not self._is_visible(conversation, selected):
                continue
            visible.append(
                {
                    "link": link,
                    "message": message,
                    "source": source,
                    "conversation": conversation,
                }
            )

        visible.sort(key=self._evidence_sort_key)
        page_rows = visible[selected_offset : selected_offset + selected_limit]
        items: list[dict[str, Any]] = []
        remaining_content = 24_000
        for row in page_rows:
            message = row["message"]
            link = row["link"]
            source = row["source"] or {}
            conversation = row["conversation"] or {}
            content = ""
            truncated = False
            if include_content:
                full_message = self.read_model.get_message(
                    str(message["message_id"]), include_content=True
                ) or {}
                content = str(full_message.get("content") or "")
                allowed = min(4_000, remaining_content)
                if len(content) > allowed:
                    content = content[:allowed]
                    truncated = True
                remaining_content -= len(content)
            excerpt_source = str(message.get("content_preview") or "")
            excerpt = " ".join(excerpt_source.split())[:240]
            item: dict[str, Any] = {
                "source_id": message.get("source_id"),
                "source_label": self._safe_owner_display_text(source.get("display_name")),
                "source_type": self._safe_owner_source_type(source.get("source_type")),
                "conversation_id": message.get("conversation_id"),
                "conversation_title": self._safe_owner_display_text(conversation.get("title")),
                "message_id": message.get("message_id"),
                "role": message.get("role"),
                "sequence": message.get("sequence"),
                "occurred_at": message.get("occurred_at"),
                "excerpt": excerpt,
                "content_hash": message.get("content_hash") or "",
                "raw_reference": self._safe_evidence_reference(
                    message.get("raw_reference") or source.get("raw_reference")
                )
                or "",
                "truncated": truncated,
            }
            if include_content:
                item["content"] = content
            items.append(item)

        as_of = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return EvidencePage(
            as_of=as_of,
            memory_id=str(memory_id),
            items=tuple(items),
            pagination={
                "limit": selected_limit,
                "offset": selected_offset,
                "total": len(visible),
                "has_more": selected_offset + len(items) < len(visible),
            },
        )

    @staticmethod
    def _is_authoritative_source(
        source: dict[str, Any] | None, viewer: ViewerContext
    ) -> bool:
        if not SourceQueryService._is_visible(source, viewer):
            return False
        # Source lifecycle is query-time authority. Only active records may
        # expose message bodies; revoked/expired/unavailable states fail closed.
        return str(source.get("status") or "").strip().casefold() == "active"

    @classmethod
    def _evidence_sort_key(cls, row: dict[str, Any]) -> tuple[Any, ...]:
        message = row["message"]
        occurred_at = cls._utc_datetime(message.get("occurred_at"))
        source_id = str(message.get("source_id") or "")
        conversation_id = str(message.get("conversation_id") or "")
        message_id = str(message.get("message_id") or "")
        try:
            sequence = int(message.get("sequence") or 0)
        except (TypeError, ValueError):
            sequence = 0
        if occurred_at is None:
            return (1, 0.0, sequence, source_id, conversation_id, message_id)
        return (0, occurred_at.timestamp(), sequence, source_id, conversation_id, message_id)

    @staticmethod
    def _utc_datetime(value: Any) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

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

    @staticmethod
    def _matches_project(item: dict[str, Any] | None, project: str | None) -> bool:
        if not project:
            return True
        projects = item.get("projects") if item else []
        if isinstance(projects, str):
            projects = [projects]
        return str(project).casefold() in {
            str(value).casefold() for value in (projects or [])
        }

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
        if text.casefold().startswith(("http://", "https://")):
            return self._safe_http_url(text)
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

    def _safe_evidence_reference(self, value: Any) -> str | None:
        """Allow only canonical, relative references for owner evidence."""
        text = str(value or "").strip()
        if not text:
            return None
        lowered = text.casefold()
        if any(token in lowered for token in _SENSITIVE_REFERENCE_TOKENS):
            return None
        safe = self._safe_reference(text)
        if not safe:
            return None
        safe_lowered = safe.casefold()
        if safe_lowered.startswith(("http://", "https://")):
            return safe
        if not safe_lowered.startswith(("raw:", "vault:")):
            return None
        _prefix, relative = safe.split(":", 1)
        relative = unquote(relative)
        relative_lowered = relative.casefold()
        if (
            relative.startswith(("{", "["))
            or relative.endswith(("}", "]"))
            or any(token in relative_lowered for token in _SENSITIVE_REFERENCE_TOKENS)
        ):
            return None
        windows_path = PureWindowsPath(relative)
        if (
            not relative
            or relative.startswith(("/", "\\"))
            or "\\" in relative
            or windows_path.is_absolute()
            or bool(windows_path.drive)
            or Path(relative).is_absolute()
            or any(part in {"", ".", ".."} for part in relative.split("/"))
        ):
            return None
        return safe

    @staticmethod
    def _safe_owner_display_text(value: Any) -> str | None:
        """Return short, owner-readable labels without paths or secret-like text."""
        text = str(value or "")
        for _ in range(3):
            decoded = unquote(text)
            if decoded == text:
                break
            text = decoded
        if any(ord(character) < 32 or ord(character) == 127 for character in text):
            return None
        text = " ".join(text.split())
        if not text or len(text) > 160 or _OWNER_DISPLAY_SENSITIVE_PATTERN.search(text):
            return None
        if text.startswith(("/", "\\", "~")):
            return None
        windows_path = PureWindowsPath(text)
        if windows_path.is_absolute() or bool(windows_path.drive):
            return None
        try:
            parsed = urlsplit(text)
        except (TypeError, ValueError):
            return None
        if parsed.scheme or "://" in text:
            return None
        if any(part == ".." for part in text.replace("\\", "/").split("/")):
            return None
        try:
            parsed_json = json.loads(text)
        except (TypeError, ValueError):
            parsed_json = None
        if isinstance(parsed_json, (dict, list)):
            return None
        return text

    @staticmethod
    def _safe_owner_source_type(value: Any) -> str | None:
        text = str(value or "").strip().casefold()
        return text if _OWNER_SOURCE_TYPE_PATTERN.fullmatch(text) and text in _OWNER_SOURCE_TYPES else None

    @staticmethod
    def _safe_http_url(value: str) -> str | None:
        try:
            parsed = urlsplit(value)
            if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
                return None
            host = parsed.hostname
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            port = f":{parsed.port}" if parsed.port is not None else ""
            safe_query = [
                (key, item)
                for key, item in parse_qsl(parsed.query, keep_blank_values=True)
                if key.casefold() not in _SENSITIVE_QUERY_KEYS
            ]
            return urlunsplit(
                (
                    parsed.scheme.casefold(),
                    f"{host}{port}",
                    parsed.path,
                    urlencode(safe_query, doseq=True),
                    "",
                )
            )
        except (TypeError, ValueError):
            return None

    def _safe_metadata(self, value: Any) -> Any:
        if isinstance(value, dict):
            output = {}
            for key, item in value.items():
                lowered = str(key).casefold()
                if any(
                    token in lowered
                    for token in ("token", "api_key", "apikey", "password", "cookie", "secret")
                ):
                    continue
                if isinstance(item, str) and (
                    item.casefold().startswith(("http://", "https://"))
                    or lowered.endswith(("path", "reference", "_ref"))
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
