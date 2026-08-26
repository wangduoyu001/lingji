from __future__ import annotations

import json
import logging
import math
import re
import stat
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..base import ExtractionAdapter
from ..errors import safe_extraction_error
from ..models import (
    ExtractedDocument,
    ExtractionBatch,
    ExtractionRequest,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)
from ..privacy import PrivacyClassifier
from .generic_ai_history import DetectionResult

logger = logging.getLogger("lingji.extraction.chatgpt")


@dataclass(frozen=True)
class _NormalizedConversation:
    conversation_id: str
    title: str
    current_node: str
    created_at: str
    updated_at: str
    messages: tuple[dict[str, Any], ...]
    models: tuple[str, ...]
    attachments: tuple[dict[str, Any], ...]
    branch_count: int


class ChatGPTExportAdapter(ExtractionAdapter):
    name = "chatgpt_export"
    version = "1.2.0"
    approved = True
    source_types = ("chatgpt", "chatgpt_export")

    DEFAULT_MAX_ZIP_TOTAL = 2 * 1024 * 1024 * 1024
    DEFAULT_MAX_MEMBER = 512 * 1024 * 1024
    DEFAULT_MAX_JSON_FILES = 500
    DEFAULT_MAX_CONVERSATIONS = 100_000
    DEFAULT_MAX_COMPRESSION_RATIO = 200

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        return source_type in self.source_types and input_path is not None and self.detect(input_path).supported

    def detect(self, path: Path) -> DetectionResult:
        if not path or path.is_dir() or path.is_symlink():
            return DetectionResult("chatgpt_export", None, False, "ChatGPT requires one official export ZIP or JSON file")
        if path.suffix.lower() not in {".zip", ".json"}:
            return DetectionResult("chatgpt_export", None, False, "ChatGPT official export must be ZIP or JSON")
        try:
            self._load_export(path, {})
        except (OSError, UnicodeError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            return DetectionResult("chatgpt_export", None, False, f"unsupported official ChatGPT export: {exc}")
        return DetectionResult("chatgpt_export", "chatgpt.export", True, "supported official ChatGPT export")

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        if not request.input_path:
            raise ValueError("ChatGPT export path is required")
        detection = self.detect(request.input_path)
        if not detection.supported:
            raise ValueError(detection.reason)
        conversations, source_files = self._load_export(request.input_path, request.options)
        projects = self._as_tuple(
            request.options.get("project_id") or request.options.get("project") or ()
        )
        agent_scope = self._as_tuple(request.options.get("agent_scope") or ())
        privacy_scan = bool(request.options.get("privacy_scan", True))
        sensitive_terms = request.options.get("sensitive_terms") or []
        classifier = PrivacyClassifier()
        documents: list[ExtractedDocument] = []
        structured_conversations: list[StructuredConversation] = []
        warnings: list[str] = []
        restricted = 0

        try:
            for conversation in conversations:
                normalized = self._normalize_conversation(conversation)
                document = self._document_from_normalized(
                    normalized, source_files, projects
                )
                privacy = "private"
                sensitivity_findings: tuple[str, ...] = ()
                if privacy_scan:
                    assessment = classifier.assess(document.body, sensitive_terms)
                    privacy = assessment.privacy
                    sensitivity_findings = tuple(assessment.kinds())
                    if assessment.restricted:
                        restricted += 1
                metadata = dict(document.metadata)
                metadata["privacy"] = privacy
                metadata["sensitivity_findings"] = list(sensitivity_findings)
                document = ExtractedDocument(
                    stable_id=document.stable_id,
                    title=document.title,
                    body=document.body,
                    source_type=document.source_type,
                    destination="private_source" if privacy == "restricted" else document.destination,
                    external_id=document.external_id,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                    metadata=metadata,
                )
                documents.append(document)
                structured_conversations.append(
                    self._structured_from_normalized(
                        normalized,
                        document_stable_id=document.stable_id,
                        source_files=source_files,
                        privacy=privacy,
                        projects=projects,
                        agent_scope=agent_scope,
                    )
                )
        except Exception as exc:
            logger.exception("ChatGPT export extraction failed; batch rejected")
            raise ValueError(
                safe_extraction_error(
                    exc,
                    message="ChatGPT conversation extraction failed; see local logs",
                )
            ) from exc

        source_external_id = str(
            request.options.get("source_external_id")
            or request.options.get("account_id")
            or request.options.get("profile_id")
            or "chatgpt:default"
        )
        source_display_name = str(
            request.options.get("source_display_name")
            or request.options.get("account_name")
            or "ChatGPT"
        )
        source_privacy = str(request.options.get("source_privacy") or "private")
        structured_source = StructuredSource(
            source_type="chatgpt",
            external_id=source_external_id,
            display_name=source_display_name,
            conversations=tuple(structured_conversations),
            privacy=source_privacy,
            projects=projects,
            agent_scope=agent_scope,
            metadata={"source_export_files": tuple(source_files)},
        )
        return ExtractionBatch(
            documents=tuple(documents),
            structured_sources=(structured_source,),
            summary={
                "conversations_found": len(conversations),
                "documents_created": len(documents),
                "restricted_documents": restricted,
                "failed_documents": len(warnings),
                "source_files": source_files,
            },
            warnings=tuple(warnings),
        )

    def _normalize_conversation(self, conversation: dict[str, Any]) -> _NormalizedConversation:
        conversation_id = str(
            conversation.get("id") or conversation.get("conversation_id") or ""
        ).strip()
        if not conversation_id:
            raise ValueError("conversation id is missing")
        title = str(conversation.get("title") or "未命名 ChatGPT 对话").strip()
        mapping = conversation.get("mapping") or {}
        if not isinstance(mapping, dict):
            mapping = {}
        current_node = str(conversation.get("current_node") or "")
        main_path = self._main_path(mapping, current_node)
        messages: list[dict[str, Any]] = []
        models: set[str] = set()
        attachments: list[dict[str, Any]] = []
        for position, (node_id, node) in enumerate(mapping.items()):
            if not isinstance(node, dict):
                continue
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            text = self._message_text(message.get("content"))
            if not text.strip():
                continue
            author = message.get("author") or {}
            role = str(author.get("role") or "unknown")
            name = str(author.get("name") or "")
            metadata = message.get("metadata") or {}
            if not isinstance(metadata, dict):
                raise ValueError("Official ChatGPT message metadata is invalid")
            model = str(
                metadata.get("model_slug")
                or metadata.get("default_model_slug")
                or metadata.get("model")
                or ""
            )
            if model:
                models.add(model)
            message_attachments = self._attachments(metadata)
            attachments.extend(message_attachments)
            messages.append(
                {
                    "node_id": str(node_id),
                    "message_id": str(message.get("id") or node_id),
                    "parent": str(node.get("parent") or ""),
                    "role": role,
                    "name": name,
                    "text": text,
                    "created_at": self._iso(message.get("create_time")),
                    "model": model,
                    "is_branch": bool(main_path and str(node_id) not in main_path),
                    "position": position,
                    "attachments": message_attachments,
                }
            )
        messages.sort(key=lambda item: (self._timestamp(item["created_at"]), item["position"]))
        return _NormalizedConversation(
            conversation_id=conversation_id,
            title=title,
            current_node=current_node,
            created_at=self._iso(conversation.get("create_time")),
            updated_at=self._iso(conversation.get("update_time")),
            messages=tuple(messages),
            models=tuple(sorted(models)),
            attachments=tuple(attachments),
            branch_count=sum(1 for message in messages if message["is_branch"]),
        )

    def _document_from_normalized(
        self,
        normalized: _NormalizedConversation,
        source_files: list[str],
        projects: tuple[str, ...],
    ) -> ExtractedDocument:
        stable_id = "LJ-CHATGPT-" + self._stable_token(normalized.conversation_id)
        return ExtractedDocument(
            stable_id=stable_id,
            title=normalized.title,
            body=self._render_conversation(
                normalized.title,
                normalized.conversation_id,
                list(normalized.messages),
                list(normalized.attachments),
            ),
            source_type="chatgpt",
            destination="source_archive",
            external_id=normalized.conversation_id,
            created_at=normalized.created_at,
            updated_at=normalized.updated_at,
            metadata={
                "conversation_id": normalized.conversation_id,
                "current_node": normalized.current_node,
                "message_count": len(normalized.messages),
                "message_ids": [message["message_id"] for message in normalized.messages],
                "branch_message_count": normalized.branch_count,
                "models": list(normalized.models),
                "attachments": list(normalized.attachments),
                "source_export_files": source_files,
                "project": list(projects),
                "tags": ["source/chatgpt", "topic/conversation"],
                "status": "active",
            },
        )

    @staticmethod
    def _structured_from_normalized(
        normalized: _NormalizedConversation,
        *,
        document_stable_id: str,
        source_files: list[str],
        privacy: str,
        projects: tuple[str, ...],
        agent_scope: tuple[str, ...],
    ) -> StructuredConversation:
        messages = tuple(
            StructuredMessage(
                external_id=message["message_id"],
                role=message["role"],
                author=message["name"],
                occurred_at=message["created_at"],
                sequence=sequence,
                content=message["text"],
                privacy=None,
                projects=(),
                agent_scope=(),
                metadata={
                    "node_id": message["node_id"],
                    "message_id": message["message_id"],
                    "parent": message["parent"],
                    "model": message["model"],
                    "is_branch": message["is_branch"],
                    "original_position": message["position"],
                    "attachments": tuple(message["attachments"]),
                },
            )
            for sequence, message in enumerate(normalized.messages)
        )
        participants = tuple(
            dict.fromkeys(
                message.author or message.role for message in messages if message.author or message.role
            )
        )
        return StructuredConversation(
            external_id=normalized.conversation_id,
            title=normalized.title,
            messages=messages,
            started_at=normalized.created_at,
            ended_at=normalized.updated_at,
            participants=participants,
            privacy=privacy,
            projects=projects,
            agent_scope=agent_scope,
            metadata={
                "current_node": normalized.current_node,
                "message_count": len(messages),
                "message_ids": tuple(message["message_id"] for message in normalized.messages),
                "branch_message_count": normalized.branch_count,
                "models": normalized.models,
                "source_export_files": tuple(source_files),
                "document_stable_id": document_stable_id,
            },
        )

    def _load_export(
        self, path: Path, options: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        loaded: list[dict[str, Any]] = []
        source_files: list[str] = []
        max_member = int(options.get("max_zip_member_bytes", self.DEFAULT_MAX_MEMBER))
        max_total = int(options.get("max_zip_uncompressed_bytes", self.DEFAULT_MAX_ZIP_TOTAL))
        max_members = int(
            options.get(
                "max_zip_members",
                options.get("max_zip_json_files", self.DEFAULT_MAX_JSON_FILES),
            )
        )
        max_conversations = int(options.get("max_conversations", self.DEFAULT_MAX_CONVERSATIONS))
        max_ratio = float(options.get("max_zip_compression_ratio", self.DEFAULT_MAX_COMPRESSION_RATIO))
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                if len(members) > max_members:
                    raise ValueError(
                        f"ChatGPT ZIP members exceed safety limit: {len(members)} > {max_members}"
                    )
                total_size = 0
                for member in members:
                    normalized_name = member.filename.replace("\\", "/")
                    member_path = Path(normalized_name)
                    if normalized_name.startswith("/") or normalized_name.split("/")[0].endswith(":") or ".." in normalized_name.split("/"):
                        raise ValueError("ChatGPT ZIP contains an unsafe member path")
                    mode = (member.external_attr >> 16) & 0o170000
                    if mode == stat.S_IFLNK:
                        raise ValueError("ChatGPT ZIP contains a symlink member")
                    if member_path.name.lower() == "conversations.json" and normalized_name != "conversations.json":
                        raise ValueError("Official ChatGPT ZIP rejects nested conversations.json")
                    if not member.is_dir():
                        if member.file_size > max_member:
                            raise ValueError(f"ZIP member too large: {member.filename}")
                        total_size += int(member.file_size)
                        if total_size > max_total:
                            raise ValueError("ChatGPT ZIP uncompressed size exceeds safety limit")
                        ratio = member.file_size / max(member.compress_size, 1)
                        if ratio > max_ratio:
                            raise ValueError(f"Suspicious ZIP compression ratio: {member.filename}")
                infos = sorted(
                    (
                        info
                        for info in members
                        if not info.is_dir()
                        and info.filename == "conversations.json"
                        and Path(info.filename).suffix.lower() == ".json"
                    ),
                    key=lambda item: item.filename,
                )
                if not infos:
                    raise ValueError("Official ChatGPT ZIP requires root conversations.json")
                if len(infos) != 1:
                    raise ValueError("Official ChatGPT ZIP must contain exactly one root conversations.json")
                for info in infos:
                    raw = self._read_zip_member(archive, info, max_member).decode("utf-8-sig")
                    loaded.extend(self._decode_conversation_payload(raw))
                    source_files.append(info.filename)
                    if len(loaded) > max_conversations:
                        raise ValueError(f"Too many conversations: {len(loaded)} > {max_conversations}")
        else:
            if path.stat().st_size > max_member:
                raise ValueError("ChatGPT JSON exceeds configured size limit")
            loaded.extend(self._decode_conversation_payload(path.read_text(encoding="utf-8-sig")))
            source_files.append(path.name)
        conversation_ids: set[str] = set()
        message_ids: set[str] = set()
        for conversation in loaded:
            conversation_id = str(conversation["id"])
            if conversation_id in conversation_ids:
                raise ValueError(f"Duplicate ChatGPT conversation ID: {conversation_id}")
            conversation_ids.add(conversation_id)
            for node in conversation["mapping"].values():
                message = node.get("message")
                if message is None:
                    continue
                message_id = str(message["id"])
                if message_id in message_ids:
                    raise ValueError(f"Duplicate ChatGPT message ID: {message_id}")
                message_ids.add(message_id)
        return loaded, source_files

    @staticmethod
    def _read_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, max_bytes: int) -> bytes:
        with archive.open(info, "r") as handle:
            data = handle.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"ZIP member exceeds read limit: {info.filename}")
        return data

    @staticmethod
    def _decode_conversation_payload(raw: str) -> list[dict[str, Any]]:
        data = json.loads(raw)
        if isinstance(data, list):
            if any(not isinstance(item, dict) for item in data):
                raise ValueError("ChatGPT conversations list contains a non-object")
            return [ChatGPTExportAdapter._validate_official_conversation(item) for item in data]
        if isinstance(data, dict):
            return [ChatGPTExportAdapter._validate_official_conversation(data)]
        raise ValueError("Unsupported ChatGPT export JSON structure")

    @staticmethod
    def _validate_official_conversation(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not value["id"].strip():
            raise ValueError("Official ChatGPT conversation id is missing")
        for field in ("title", "current_node"):
            if field in value and value[field] is not None and not isinstance(value[field], str):
                raise ValueError(f"Official ChatGPT conversation field {field} is invalid")
        if not isinstance(value.get("mapping"), dict):
            raise ValueError("Official ChatGPT conversation mapping is missing")
        for timestamp_field in ("create_time", "update_time"):
            if timestamp_field in value and value[timestamp_field] is not None:
                ChatGPTExportAdapter._validate_timestamp(value[timestamp_field], f"conversation {timestamp_field}")
        message_ids: set[str] = set()
        message_count = 0
        for node_id, node in value["mapping"].items():
            if not isinstance(node_id, str) or not isinstance(node, dict):
                raise ValueError("Official ChatGPT mapping is malformed")
            if "parent" in node and node["parent"] is not None and not isinstance(node["parent"], str):
                raise ValueError("Official ChatGPT mapping parent is invalid")
            if "message" not in node:
                raise ValueError("Official ChatGPT mapping node message is missing")
            message = node.get("message")
            if message is None:
                continue
            message_count += 1
            if not isinstance(message, dict):
                raise ValueError("Official ChatGPT message is malformed")
            message_id = message.get("id")
            if not isinstance(message_id, str) or not message_id.strip():
                raise ValueError("Official ChatGPT message id is missing")
            if message_id in message_ids:
                raise ValueError(f"Duplicate ChatGPT message ID: {message_id}")
            message_ids.add(message_id)
            author = message.get("author")
            role = author.get("role") if isinstance(author, dict) else None
            if role not in {"user", "assistant", "system", "tool"}:
                raise ValueError("Official ChatGPT message role is invalid")
            if "metadata" in message and message.get("metadata") is not None and not isinstance(message.get("metadata"), dict):
                raise ValueError("Official ChatGPT message metadata is invalid")
            if isinstance(message.get("metadata"), dict):
                ChatGPTExportAdapter._validate_metadata(message["metadata"])
            content = message.get("content")
            if not isinstance(content, dict):
                raise ValueError("Official ChatGPT message content is missing")
            ChatGPTExportAdapter._validate_content(content)
            if not ChatGPTExportAdapter._message_text(content).strip():
                raise ValueError("Official ChatGPT message content is empty")
            ChatGPTExportAdapter._validate_timestamp(message.get("create_time"), "message timestamp")
        if message_count == 0:
            raise ValueError("Official ChatGPT conversation contains no messages")
        return value

    @staticmethod
    def _validate_timestamp(value: Any, label: str) -> None:
        if isinstance(value, bool):
            raise ValueError(f"{label} is invalid")
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                raise ValueError(f"{label} is invalid")
            try:
                datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (ValueError, OSError, OverflowError) as exc:
                raise ValueError(f"{label} is invalid") from exc
            return
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is invalid")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{label} is invalid") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{label} must be timezone-aware")

    @staticmethod
    def _validate_content(content: Mapping[str, Any]) -> None:
        parts = content.get("parts")
        if parts is not None:
            if not isinstance(parts, list) or not parts:
                raise ValueError("Official ChatGPT message content parts are invalid")
            for part in parts:
                if isinstance(part, str):
                    if not part.strip():
                        raise ValueError("Official ChatGPT message content part is empty")
                    continue
                if not isinstance(part, dict):
                    raise ValueError("Official ChatGPT message content part is invalid")
                if any(isinstance(part.get(key), str) and part[key].strip() for key in ("text", "content", "result", "caption")):
                    continue
                if part.get("content_type") == "image_asset_pointer" and (part.get("asset_pointer") or part.get("pointer")):
                    continue
                raise ValueError("Official ChatGPT message content part is unsupported")
            return
        if any(isinstance(content.get(key), str) and content[key].strip() for key in ("text", "result", "content")):
            return
        raise ValueError("Official ChatGPT message content shape is unsupported")

    @staticmethod
    def _validate_metadata(metadata: Mapping[str, Any]) -> None:
        for key in ("model_slug", "default_model_slug", "model"):
            value = metadata.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"Official ChatGPT metadata field {key} is invalid")
        for key in ("attachments", "files"):
            raw = metadata.get(key)
            if raw is None:
                continue
            items = [raw] if isinstance(raw, dict) else raw if isinstance(raw, list) else None
            if items is None:
                raise ValueError(f"Official ChatGPT metadata field {key} is invalid")
            for item in items:
                if isinstance(item, str):
                    continue
                if not isinstance(item, dict):
                    raise ValueError(f"Official ChatGPT metadata field {key} contains an invalid item")
                for item_key in (
                    "id", "file_id", "asset_pointer", "pointer", "name", "file_name",
                    "filename", "mime_type",
                ):
                    value = item.get(item_key)
                    if value is not None and not isinstance(value, str):
                        raise ValueError(f"Official ChatGPT metadata attachment field {item_key} is invalid")
                size = item.get("size")
                if size is not None and not isinstance(size, (str, int, float)):
                    raise ValueError("Official ChatGPT metadata attachment size is invalid")

    def _render_conversation(
        self,
        title: str,
        conversation_id: str,
        messages: list[dict[str, Any]],
        attachments: list[dict[str, Any]],
    ) -> str:
        lines = [f"# {title}", "", f"> ChatGPT conversation ID: `{conversation_id}`", ""]
        for index, message in enumerate(messages, 1):
            role_label = {"user": "用户", "assistant": "ChatGPT", "system": "系统", "tool": "工具"}.get(message["role"], message["role"])
            suffix = " · 分支消息" if message["is_branch"] else ""
            model = f" · {message['model']}" if message["model"] else ""
            timestamp = f" · {message['created_at']}" if message["created_at"] else ""
            message_id = f" · message_id={message['message_id']}" if message["message_id"] else ""
            lines.extend([f"## {index}. {role_label}{timestamp}{model}{message_id}{suffix}", "", message["text"].rstrip(), ""])
            if message["attachments"]:
                lines.append("附件：")
                for item in message["attachments"]:
                    lines.append(f"- `{item.get('name') or item.get('id') or 'unknown'}`")
                lines.append("")
        if attachments:
            lines.extend(["## 对话附件索引", ""])
            seen = set()
            for item in attachments:
                key = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                lines.append("- " + ", ".join(f"{key}: {value}" for key, value in item.items() if value))
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _message_text(content: Any) -> str:
        if not isinstance(content, dict):
            return ""
        parts = content.get("parts")
        if isinstance(parts, list):
            rendered = [ChatGPTExportAdapter._flatten_part(part) for part in parts]
            return "\n\n".join(text for text in rendered if text)
        for key in ("text", "result", "content"):
            value = content.get(key)
            if isinstance(value, str):
                return value
        return ""

    @staticmethod
    def _flatten_part(part: Any) -> str:
        if isinstance(part, str):
            return part
        if isinstance(part, dict):
            for key in ("text", "content", "result", "caption"):
                value = part.get(key)
                if isinstance(value, str):
                    return value
            if part.get("content_type") == "image_asset_pointer":
                pointer = part.get("asset_pointer") or part.get("pointer")
                return f"[图片附件: {pointer}]" if pointer else "[图片附件]"
            return json.dumps(part, ensure_ascii=False, sort_keys=True)
        return "" if part is None else str(part)

    @staticmethod
    def _attachments(metadata: Any) -> list[dict[str, Any]]:
        if not isinstance(metadata, dict):
            return []
        candidates = []
        raw = metadata.get("attachments") or metadata.get("files") or []
        if isinstance(raw, dict):
            raw = [raw]
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    candidates.append({
                        "id": item.get("id") or item.get("file_id") or item.get("asset_pointer") or "",
                        "name": item.get("name") or item.get("file_name") or item.get("filename") or "",
                        "mime_type": item.get("mime_type") or "",
                        "size": item.get("size") or "",
                    })
                elif isinstance(item, str):
                    candidates.append({"id": item, "name": "", "mime_type": "", "size": ""})
        return candidates

    @staticmethod
    def _main_path(mapping: dict[str, Any], current_node: str) -> set[str]:
        result = set()
        node_id = current_node
        while node_id and node_id not in result:
            result.add(node_id)
            node = mapping.get(node_id)
            if not isinstance(node, dict):
                break
            node_id = str(node.get("parent") or "")
        return result

    @staticmethod
    def _iso(value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat(timespec="seconds")
            except (ValueError, OSError, OverflowError):
                return ""
        text = str(value)
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat(timespec="seconds")
        except ValueError:
            return text

    @staticmethod
    def _timestamp(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

    @staticmethod
    def _stable_token(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
        return cleaned[:80] or "UNKNOWN"

    @staticmethod
    def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
        result = []
        seen = set()
        for path in paths:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(path)
        return result

    @staticmethod
    def _as_tuple(value: Any) -> tuple[str, ...]:
        if value in (None, "", [], ()):
            return ()
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item) for item in value if str(item))
        return (str(value),)
